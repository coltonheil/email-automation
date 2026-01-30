#!/usr/bin/env python3
"""
Retry Utilities
Provides robust retry logic with exponential backoff for API calls
"""

import time
import logging
from typing import Callable, TypeVar, Optional, Any
from functools import wraps

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/email-automation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
    on_failure: Optional[Callable] = None
):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay between retries (default: 60.0)
        backoff_factor: Multiplier for delay after each retry (default: 2.0)
        exceptions: Tuple of exceptions to catch (default: all exceptions)
        on_retry: Optional callback called on each retry (receives attempt number, exception)
        on_failure: Optional callback called when all retries exhausted (receives exception)
    
    Example:
        @retry_with_backoff(max_attempts=5, initial_delay=2.0)
        def fetch_emails():
            # ... API call that might fail ...
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        # All retries exhausted
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}",
                            exc_info=True
                        )
                        
                        if on_failure:
                            on_failure(e)
                        
                        raise
                    
                    # Log retry
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e)
                    
                    # Wait before retry
                    time.sleep(delay)
                    
                    # Exponential backoff (capped at max_delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            # Should never reach here, but for type safety
            raise last_exception
        
        return wrapper
    return decorator


class RetryableAPICall:
    """
    Context manager for retryable API calls with logging
    
    Usage:
        with RetryableAPICall("Composio fetch emails") as call:
            result = composio_api.fetch_emails(...)
            call.success(result)
    """
    
    def __init__(
        self,
        operation_name: str,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        log_context: Optional[dict] = None
    ):
        self.operation_name = operation_name
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.log_context = log_context or {}
        self.attempt = 0
        self.result = None
        self.error = None
    
    def __enter__(self):
        self.attempt += 1
        logger.info(
            f"Starting: {self.operation_name} (attempt {self.attempt}/{self.max_attempts})",
            extra=self.log_context
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Success
            logger.info(f"Completed: {self.operation_name}", extra=self.log_context)
            return False
        
        # Error occurred
        self.error = exc_val
        
        if self.attempt < self.max_attempts:
            # Retry
            delay = self.initial_delay * (2 ** (self.attempt - 1))
            logger.warning(
                f"Failed: {self.operation_name} (attempt {self.attempt}/{self.max_attempts}): "
                f"{str(exc_val)}. Retrying in {delay:.1f}s...",
                extra=self.log_context
            )
            time.sleep(delay)
            return True  # Suppress exception, will retry
        else:
            # All retries exhausted
            logger.error(
                f"Failed permanently: {self.operation_name} after {self.max_attempts} attempts: "
                f"{str(exc_val)}",
                exc_info=True,
                extra=self.log_context
            )
            return False  # Re-raise exception
    
    def success(self, result: Any = None):
        """Mark operation as successful and store result"""
        self.result = result


def safe_api_call(
    func: Callable[..., T],
    *args,
    default: Optional[T] = None,
    operation_name: Optional[str] = None,
    **kwargs
) -> Optional[T]:
    """
    Safely call an API function with automatic retry and error handling
    
    Args:
        func: Function to call
        *args: Positional arguments for func
        default: Default value to return on failure (default: None)
        operation_name: Name for logging (default: func.__name__)
        **kwargs: Keyword arguments for func
    
    Returns:
        Result of func or default value on failure
    
    Example:
        emails = safe_api_call(
            composio_api.fetch_emails,
            account_id="123",
            default=[],
            operation_name="Fetch Gmail unread"
        )
    """
    name = operation_name or func.__name__
    
    @retry_with_backoff(max_attempts=3)
    def wrapped():
        return func(*args, **kwargs)
    
    try:
        return wrapped()
    except Exception as e:
        logger.error(f"{name} failed permanently: {str(e)}", exc_info=True)
        return default


class ErrorCollector:
    """
    Collects errors during batch operations for later reporting
    
    Usage:
        errors = ErrorCollector()
        
        for email in emails:
            try:
                process_email(email)
            except Exception as e:
                errors.add(f"Email {email['id']}", e)
        
        if errors.has_errors():
            errors.report()
    """
    
    def __init__(self):
        self.errors: list[tuple[str, Exception]] = []
    
    def add(self, context: str, error: Exception):
        """Add an error with context"""
        self.errors.append((context, error))
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    
    def has_errors(self) -> bool:
        """Check if any errors were collected"""
        return len(self.errors) > 0
    
    def count(self) -> int:
        """Get error count"""
        return len(self.errors)
    
    def report(self) -> str:
        """Generate error report"""
        if not self.errors:
            return "No errors"
        
        lines = [f"Collected {len(self.errors)} errors:"]
        for context, error in self.errors:
            lines.append(f"  - {context}: {str(error)}")
        
        report = '\n'.join(lines)
        logger.error(f"Error report:\n{report}")
        return report
    
    def raise_if_errors(self, message: str = "Operation completed with errors"):
        """Raise exception if errors were collected"""
        if self.has_errors():
            raise RuntimeError(f"{message}:\n{self.report()}")


# Ensure logs directory exists
import os
os.makedirs('logs', exist_ok=True)
