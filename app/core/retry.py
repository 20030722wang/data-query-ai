"""Lightweight async retry decorator — uses only stdlib asyncio, no extra deps."""

import asyncio
import functools
from collections.abc import Callable, Awaitable
from typing import TypeVar

from app.core.log import logger

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
):
    """Decorate an async callable with exponential-backoff retry logic.

    Args:
        max_attempts: Maximum total attempts before giving up.
        base_delay: Initial backoff in seconds (doubles each attempt).
        max_delay: Cap for the exponential backoff.
        exceptions: Tuple of exception types to retry on; others propagate immediately.

    Returns:
        A decorator that wraps the async function with retry behavior.
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}",
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s...",
                    )
                    await asyncio.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator
