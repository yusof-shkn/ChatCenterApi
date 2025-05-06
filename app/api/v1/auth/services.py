from datetime import datetime, timedelta, timezone
import uuid
import logging
import json
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from tortoise.exceptions import DoesNotExist, IntegrityError
from fastapi.encoders import jsonable_encoder

from app.models.postgres_models import Session, User
from app.core.config import settings
from app.core.cache import RedisCacheManager
from .schemas import UserCreate, LogoutResponse, UserResponse

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, cache: RedisCacheManager):
        self.cache = cache
        self.session_prefix = (
            f"{settings.cache.KEY_PREFIX}{settings.cache.SESSION_KEY_PREFIX}"
        )

    async def create_session(self, user_id: uuid.UUID, username: str) -> str:
        """Create and store a new user session"""
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
            payload = {
                "sub": username,
                "user_id": str(user_id),
                "exp": expires_at.timestamp(),
                "iat": datetime.now(timezone.utc).timestamp(),
            }

            token = jwt.encode(
                payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM
            )

            # Store session in database
            await Session.create(
                token=token,
                user_id=user_id,
                expires_at=expires_at,
                status=True,
            )

            # Cache session in Redis using configured TTL
            await self.cache.set(
                f"{self.session_prefix}{token}",
                str(user_id),
                ttl=settings.cache.SESSION_TTL,
            )

            return token

        except Exception as e:
            logger.error(f"Session creation failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Session creation failed",
            )

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user with proper validation"""
        try:
            if await User.exists(username=user_data.username):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already exists",
                )

            hashed_password = pwd_context.hash(user_data.password)
            user = await User.create(
                username=user_data.username,
                email=user_data.email,
                password_hash=hashed_password,
            )
            await UserService.clear_users_cache(self)
            return user

        except IntegrityError as e:
            logger.error(f"Registration integrity error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database integrity error",
            )

    async def logout_user(self, token: str) -> LogoutResponse:
        """Invalidate a user session"""
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("user_id")

            # Update database session
            session = await Session.get(token=token)
            session.status = False
            await session.save()

            # Remove from Redis using prefixed key
            await self.cache.delete(f"{self.session_prefix}{token}")

            return LogoutResponse(message="Successfully logged out")

        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )
        except JWTError as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )


class UserService:
    def __init__(self, cache: RedisCacheManager):
        self.cache = cache
        self.cache_key = f"{settings.cache.KEY_PREFIX}{settings.cache.USER_KEY}"

    async def get_all_users(self, current_user) -> List[UserResponse]:
        """Get all users with Redis caching"""
        if not current_user.is_admin:
            logger.error(f"User not Admin: {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowd to retrieve users",
            )
        try:
            cached = await self.cache.get(self.cache_key)
            if cached:
                return [UserResponse(**item) for item in json.loads(cached)]

            users = await User.all()
            user_data = [
                UserResponse(
                    id=str(user.id),
                    username=user.username,
                    email=user.email,
                    created_at=user.created_at,
                ).dict()
                for user in users
            ]

            await self.cache.set(
                self.cache_key,
                json.dumps(jsonable_encoder(user_data)),
                ttl=settings.cache.USER_TTL,
            )

            return [UserResponse(**user) for user in user_data]

        except Exception as e:
            logger.error(f"Failed to fetch users: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve users",
            )

    async def clear_users_cache(self) -> None:
        """Invalidate users cache using configured key"""
        try:
            await self.cache.delete(self.cache_key)
        except Exception as e:
            logger.warning(f"Cache clearance failed: {str(e)}")
