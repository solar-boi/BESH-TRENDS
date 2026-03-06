"""
Utility functions for the DART pricing system.
"""
import functools
import logging
import time
from typing import Any, Callable, Tuple, Type, TypeVar

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
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
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


def format_price(price_cents: float, decimals: int = 2) -> str:
    """
    Format a price in cents for display.

    Args:
        price_cents: Price in cents per kWh.
        decimals: Number of decimal places.

    Returns:
        Formatted string like "5.23¢/kWh".
    """
    return f"{price_cents:.{decimals}f}¢/kWh"


def format_price_change(old_price: float, new_price: float) -> str:
    """
    Format a price change with direction indicator.

    Args:
        old_price: Previous price in cents.
        new_price: Current price in cents.

    Returns:
        Formatted string like "+1.23¢" or "-0.45¢".
    """
    change = new_price - old_price
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f}¢"
