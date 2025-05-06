from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.core.config import settings
import logging
from fastapi import Depends, HTTPException
from fastapi import status
from app.models.postgres_models import User
import bcrypt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


async def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token.

    Args:
        token (str): The JWT token to verify.

    Returns:
        dict: Decoded JWT payload.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


async def authenticate_user(username: str, password: str) -> User | None:
    """
    Authenticate a user by username and password.

    Args:
        username (str): User's username.
        password (str): User's password.

    Returns:
        User | None: The authenticated user object or None if authentication fails.
    """
    user = await User.get_or_none(username=username)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
