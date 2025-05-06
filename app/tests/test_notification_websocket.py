# app/tests/test_notification_websocket.py
from fastapi.testclient import TestClient
from app.main import app  # Import your FastAPI app here
import pytest

client = TestClient(app)


def test_websocket_notifications():
    # Step 1: Open a WebSocket connection to the /ws/notifications endpoint
    with client.websocket_connect("/ws/notifications") as websocket:
        # Step 2: Send a "Test message" to the WebSocket
        websocket.send_text("Test message")

        # Step 3: Receive the message from WebSocket
        try:
            response = websocket.receive_text()
            assert response == "Echo: Test message"  # Adjust this based on your server's logic
        except Exception as e:
            pytest.fail(f"WebSocket response failed: {e}")

    # Step 4: Now create a personal notification and check if it is sent to the correct WebSocket
    user_id = 1  # Specify a user ID for testing personal notifications
    notification_message = "Personal notification for user 1"

    # Send a POST request to create a new notification
    notification_data = {
        "user_id": user_id,
        "message": notification_message
    }

    response = client.post("/notifications", json=notification_data)
    print(response)
    assert response.status_code == 200
    notification = response.json()
    assert notification["user_id"] == user_id
    assert notification["message"] == notification_message

    # Step 5: Now open a new WebSocket connection to verify the personal notification
    with client.websocket_connect("/ws/notifications") as websocket:
        # Wait for the notification to be sent to the connected WebSocket
        personal_message = websocket.receive_text()
        assert personal_message == f"New Notification for User {user_id}: {notification_message}"
