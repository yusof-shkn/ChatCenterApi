# tests/test_rate_limiting.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.db.postgres import init_postgres, close_postgres
from app.models.postgres_models import User
from app.db.redis import redis_client

# Configure test settings
settings.RATE_LIMIT = 3  # Lower limit for testing
settings.RATE_LIMIT_WINDOW = 60  # 1 minute window


@pytest.fixture(scope="module")
def test_client():
    # Initialize dependencies
    init_postgres()

    with TestClient(app) as client:
        yield client

    # Cleanup
    close_postgres()


@pytest.fixture(autouse=True)
async def clear_state():
    # Clean Redis before each test
    redis_client.flushdb()

    # Clean PostgreSQL data
    await User.all().delete()
    yield


@pytest.fixture
async def test_user():
    # Create a test user for authenticated tests
    user = await User.create(
        username="testuser",
        email="test@example.com",
        password_hash="testing123",
    )
    return user


def test_registration_rate_limit(test_client: TestClient):
    for i in range(settings.RATE_LIMIT + 1):  # Test beyond limit
        response = test_client.post(
            "/auth/register",
            json={
                "username": f"user{i}",
                "email": f"user{i}@test.com",
                "password": "ValidPass123!",
            },
        )
        if i < settings.RATE_LIMIT:
            assert response.status_code in [
                200,
                400,
            ], f"Unexpected status code: {response.status_code}"
        else:
            assert response.status_code == 429, "Rate limit not enforced"

    # Test rate limit exceeded
    response = test_client.post(
        "/auth/register",
        json={
            "username": "blockeduser",
            "email": "blocked@test.com",
            "password": "ValidPass123!",
        },
    )
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]


def test_authenticated_endpoint_limit(test_client, test_user):
    # Login to get token
    login_response = test_client.post(
        "/auth/login", data={"username": "testuser", "password": "testpassword"}
    )
    token = login_response.json()["access_token"]

    # Test authenticated endpoint
    for _ in range(settings.RATE_LIMIT):
        response = test_client.post(
            "/message/send",
            json={"text": "test message"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    # Test rate limit exceeded
    response = test_client.post(
        "/message/send",
        json={"text": "blocked message"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 429
