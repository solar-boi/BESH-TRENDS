"""
Utility functions for the DART pricing system.
"""
import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logging from application entry points."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    root.setLevel(level)


def retry_operation(
    max_attempts: int = 3,
    delay: int = 2,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator for retrying operations that may fail due to network issues.

    Args:
        max_attempts: Maximum number of retry attempts.
        delay: Delay between retries in seconds.
        exceptions: Tuple of exceptions to catch and retry on.

    Returns:
        Decorated function that will retry on failure.

    Example:
        @retry_operation(max_attempts=3, delay=2, exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get(url)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        logger.error(
                            "All %d attempts failed for %s: %s",
                            max_attempts,
                            func.__name__,
                            e,
                        )
                        raise last_exception
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %ds...",
                        attempt + 1,
                        max_attempts,
                        func.__name__,
                        e,
                        delay,
                    )
                    time.sleep(delay)
            raise last_exception  # Should never reach here
        return wrapper
    return decorator
