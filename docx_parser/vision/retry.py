"""
Retry utilities for vision providers.

Provides retry decorators with exponential backoff for handling
transient API errors and rate limits.
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from .exceptions import RateLimitError, VisionError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds between retries.
        max_delay: Maximum delay in seconds between retries.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        retryable_exceptions: Tuple of exception types to retry on.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            RateLimitError,
            ConnectionError,
            TimeoutError,
        )


# Default configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool,
) -> float:
    """
    Calculate delay for the next retry attempt.

    Uses exponential backoff with optional jitter.

    Args:
        attempt: Current attempt number (0-indexed).
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Base for exponential calculation.
        jitter: Whether to add random jitter.

    Returns:
        Delay in seconds before next retry.
    """
    # Exponential backoff: base_delay * (exponential_base ^ attempt)
    delay = base_delay * (exponential_base**attempt)

    # Cap at max_delay
    delay = min(delay, max_delay)

    # Add jitter (0-50% of delay)
    if jitter:
        jitter_amount = delay * random.uniform(0, 0.5)
        delay += jitter_amount

    return delay


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds between retries.
        max_delay: Maximum delay in seconds between retries.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        retryable_exceptions: Tuple of exception types to retry on.
        on_retry: Optional callback called on each retry with (exception, attempt).

    Returns:
        Decorated function with retry behavior.

    Example:
        @with_retry(max_retries=3, base_delay=1.0)
        def call_api():
            return api.request()

        @with_retry(
            max_retries=5,
            retryable_exceptions=(RateLimitError, ConnectionError),
            on_retry=lambda e, a: logger.warning(f"Retry {a}: {e}")
        )
        def describe_image(path):
            return provider.describe_image(path)
    """
    if retryable_exceptions is None:
        retryable_exceptions = (RateLimitError, ConnectionError, TimeoutError)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = calculate_delay(
                            attempt, base_delay, max_delay, exponential_base, jitter
                        )
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                        if on_retry:
                            on_retry(e, attempt + 1)

                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed. Last error: {e}"
                        )

            # Re-raise the last exception
            raise last_exception  # type: ignore

        return wrapper  # type: ignore

    return decorator


def retry_on_rate_limit(
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Callable[[F], F]:
    """
    Specialized retry decorator for rate limit errors.

    Uses longer delays suitable for rate limiting scenarios.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.

    Returns:
        Decorated function.

    Example:
        @retry_on_rate_limit(max_retries=5)
        def call_openai():
            return client.chat.completions.create(...)
    """
    return with_retry(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=120.0,
        exponential_base=2.0,
        jitter=True,
        retryable_exceptions=(RateLimitError,),
    )


class RetryHandler:
    """
    Class-based retry handler for more control.

    Useful when you need to track retry state or customize behavior
    dynamically.

    Example:
        handler = RetryHandler(max_retries=3)

        result = handler.execute(
            lambda: api.request(),
            retryable_exceptions=(APIError,)
        )
    """

    def __init__(self, config: Optional[RetryConfig] = None) -> None:
        """
        Initialize the retry handler.

        Args:
            config: RetryConfig instance or None for defaults.
        """
        self.config = config or DEFAULT_RETRY_CONFIG
        self.attempts = 0
        self.last_exception: Optional[Exception] = None

    def reset(self) -> None:
        """Reset the handler state."""
        self.attempts = 0
        self.last_exception = None

    def execute(
        self,
        func: Callable[[], Any],
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    ) -> Any:
        """
        Execute a function with retry behavior.

        Args:
            func: Function to execute.
            retryable_exceptions: Override default retryable exceptions.

        Returns:
            Result of the function.

        Raises:
            Exception: The last exception if all retries fail.
        """
        self.reset()
        exceptions = retryable_exceptions or self.config.retryable_exceptions

        for attempt in range(self.config.max_retries + 1):
            self.attempts = attempt + 1
            try:
                return func()
            except exceptions as e:
                self.last_exception = e

                if attempt < self.config.max_retries:
                    delay = calculate_delay(
                        attempt,
                        self.config.base_delay,
                        self.config.max_delay,
                        self.config.exponential_base,
                        self.config.jitter,
                    )
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.config.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)

        raise self.last_exception  # type: ignore

    @property
    def total_attempts(self) -> int:
        """Get the total number of attempts made."""
        return self.attempts
