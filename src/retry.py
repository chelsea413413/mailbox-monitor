"""Retry decorator with exponential backoff."""
from __future__ import annotations

import functools
import time
from typing import Callable, Type


def retry(
    max_retries: int = 3,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    logger=None,
):
    """Decorate a function to retry on exception with exponential backoff.

    Args:
        max_retries: total attempts (including the first try).
        backoff: base delay in seconds; actual delay = backoff ** attempt.
        exceptions: exception types that should trigger a retry.
        logger: optional logger for warning messages.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        delay = backoff ** attempt
                        msg = (
                            f"{func.__name__} attempt {attempt}/{max_retries} "
                            f"failed: {exc}. Retrying in {delay:.1f}s..."
                        )
                        if logger:
                            logger.warning(msg)
                        time.sleep(delay)
                    else:
                        if logger:
                            logger.error(
                                f"{func.__name__} exhausted {max_retries} retries: {exc}"
                            )
            raise last_exc

        return wrapper

    return decorator
