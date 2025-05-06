from fastapi.security import OAuth2PasswordBearer
from app.core.cache import RedisCacheManager
from .services import AuthService, UserService
from app.dependencies import get_redis
from fastapi import Depends

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Dependency injection helpers
async def get_auth_service(
    redis: RedisCacheManager = Depends(get_redis),
) -> AuthService:
    return AuthService(redis)


async def get_user_service(
    redis: RedisCacheManager = Depends(get_redis),
) -> UserService:
    return UserService(redis)
