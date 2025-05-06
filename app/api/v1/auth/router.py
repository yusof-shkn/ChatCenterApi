from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
import logging
from uuid import UUID

from .schemas import UserCreate, UserResponse, TokenResponse, LogoutResponse
from .dependencies import get_auth_service, get_user_service, oauth2_scheme
from app.models.postgres_models import User
from .services import AuthService, UserService
from .utils import authenticate_user
from app.dependencies import get_current_user
from app.utils.cache import cache_response
from app.core.config import settings
from fastapi_limiter.depends import RateLimiter

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)


def format_user_response(user: User) -> UserResponse:
    """Helper to format user responses consistently"""
    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        created_at=user.created_at,
    )


@router.post(
    "/register",
    response_model=UserResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Register a new user"""
    try:
        logger.info(f"Registration attempt for username: {user_data.username}")
        user = await auth_service.register_user(user_data)
        logger.info(f"User registered successfully: {user.id}")
        return format_user_response(user)

    except HTTPException as he:
        logger.warning(f"Registration failed for {user_data.username}: {he.detail}")
        raise
    except Exception as e:
        logger.error(
            {
                "Registration error": user_data.username,
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "User registration failed"},
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return access token"""
    try:
        logger.debug(f"Login attempt for user: {form_data.username}")
        user = await authenticate_user(form_data.username, form_data.password)

        if not user:
            logger.warning(f"Failed login attempt for: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Invalid credentials"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"Generating token for user: {user.id}")
        token = await auth_service.create_session(user.id, user.username)
        return TokenResponse(access_token=token, token_type="bearer")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Login error",
            extra={
                "username": form_data.username,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Authentication failed"},
        )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
async def logout(
    auth_service: AuthService = Depends(get_auth_service),
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
):
    """Invalidate user session"""
    try:
        logger.info(f"Logout initiated for user: {current_user.id}")
        response = await auth_service.logout_user(token)
        logger.debug(f"Session invalidated for user: {current_user.id}")
        return response

    except HTTPException as he:
        logger.warning(f"Logout failed: {he.detail}")
        raise
    except Exception as e:
        logger.error(
            "Logout error",
            extra={
                "user_id": current_user.id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Logout failed"},
        )


@router.get(
    "/users/me",
    response_model=UserResponse,
    dependencies=[Depends(RateLimiter(times=100, seconds=60))],
)
@cache_response()
async def get_authenticated_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user details"""
    logger.debug(f"Fetching user details for: {current_user.id}")
    return format_user_response(current_user)


@router.get(
    "/users",
    response_model=List[UserResponse],
    dependencies=[Depends(RateLimiter(times=5, seconds=60))],
)
@cache_response()
async def get_all_users(
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_user),
) -> List[UserResponse]:
    """Get all users (admin only)"""
    try:
        logger.info(f"User list request from: {current_user.id}")

        # Example admin check (uncomment when ready)
        # if not current_user.is_admin:
        #     logger.warning(f"Unauthorized access attempt by: {current_user.id}")
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail={"message": "Unauthorized access"},
        #     )

        logger.debug("Fetching user list from service")
        users = await user_service.get_all_users(current_user)
        logger.info(f"Returning {len(users)} users")
        return users

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "User list error",
            extra={
                "requesting_user": current_user.id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to retrieve users"},
        )
