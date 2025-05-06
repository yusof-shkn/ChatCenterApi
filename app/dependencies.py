from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, FastAPI
from app.models.postgres_models import User
from app.core.config import settings
from passlib.context import CryptContext
import logging
from jose import JWTError, jwt
from app.core.cache import RedisCacheManager
from app.core.nlp.services import NLPService
from fastapi import Request
from fastapi import Request

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_redis(request: Request) -> RedisCacheManager:
    return request.app.state.redis_cache


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Retrieve the current user from a JWT token.
    """
    logger.info(f"Validating token: {token[:10]}...")
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode JWT
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        logger.debug(f"JWT payload: {payload}")
        username: str = payload.get("sub")
        if username is None:
            logger.warning("No username in JWT payload")
            raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise credentials_exception

    # Fetch user from database
    try:
        user = await User.filter(username=username).first()
        if user is None:
            logger.warning(f"User not found: {username}")
            raise credentials_exception
        logger.info(f"Authenticated user: {username}, id: {user.id}")
        return user
    except Exception as e:
        logger.error(f"Failed to fetch user {username}: {str(e)}")
        raise credentials_exception


# Update get_nlp_service to use request context


async def get_nlp_service(request: Request) -> NLPService:
    """
    Get NLPService from app state using request context
    """
    return request.app.state.nlp_service
