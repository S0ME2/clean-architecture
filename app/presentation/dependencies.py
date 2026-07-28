import redis

from app.application.book_service import BookService
from app.config import CACHE_TTL, DATABASE_URL, REDIS_URL
from app.infrastructure.book_cache import BookCache
from app.infrastructure.unit_of_work import UnitOfWork

redis_client = redis.from_url(
    REDIS_URL,
    decode_responses=True,
)

book_cache = BookCache(
    redis_client=redis_client,
    ttl=CACHE_TTL,
)


def get_book_service():
    uow = UnitOfWork(DATABASE_URL)

    try:
        yield BookService(uow=uow, cache=book_cache)
    except Exception:
        uow.rollback()
        raise
    finally:
        uow.close()
