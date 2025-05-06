from aiocache import cached
from app.core.config import settings


def cache_response(ttl: int = settings.DEFAULT_CACHE_TTL):
    return cached(
        key_builder=lambda f, *args, **kwargs: f"{f.__module__}:{f.__name__}:{args}:{kwargs}",
        ttl=ttl,
        namespace=settings.REDIS_NAMESPACE,
    )
