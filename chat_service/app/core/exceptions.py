"""
Custom exception classes for the Chat Service.
"""

from typing import Optional, Any, Dict


class ChatServiceException(Exception):
    """
    Base exception class for Chat Service.

    Attributes:
        status_code (int): HTTP status code
        detail (str): Error message
        code (str): Error code for API clients
        headers (Optional[Dict[str, Any]]): Additional headers
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        code: str = "internal_error",
        headers: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize ChatServiceException.

        Args:
            status_code (int): HTTP status code
            detail (str): Error message
            code (str, optional): Error code for API clients. Defaults to "internal_error".
            headers (Optional[Dict[str, Any]], optional): Additional headers. Defaults to None.
        """
        self.status_code = status_code
        self.detail = detail
        self.code = code
        self.headers = headers
        super().__init__(detail)


class NotFoundException(ChatServiceException):
    """Exception for resource not found errors."""

    def __init__(self, detail: str = "Resource not found", code: str = "not_found"):
        """
        Initialize NotFoundException.

        Args:
            detail (str, optional): Error message. Defaults to "Resource not found".
            code (str, optional): Error code. Defaults to "not_found".
        """
        super().__init__(status_code=404, detail=detail, code=code)


class ForbiddenException(ChatServiceException):
    """Exception for access denied errors."""

    def __init__(self, detail: str = "Access denied", code: str = "forbidden"):
        """
        Initialize ForbiddenException.

        Args:
            detail (str, optional): Error message. Defaults to "Access denied".
            code (str, optional): Error code. Defaults to "forbidden".
        """
        super().__init__(status_code=403, detail=detail, code=code)


class UnauthorizedException(ChatServiceException):
    """Exception for authentication errors."""

    def __init__(self, detail: str = "Unauthorized", code: str = "unauthorized"):
        """
        Initialize UnauthorizedException.

        Args:
            detail (str, optional): Error message. Defaults to "Unauthorized".
            code (str, optional): Error code. Defaults to "unauthorized".
        """
        super().__init__(status_code=401, detail=detail, code=code)


class BadRequestException(ChatServiceException):
    """Exception for invalid request errors."""

    def __init__(self, detail: str = "Bad request", code: str = "bad_request"):
        """
        Initialize BadRequestException.

        Args:
            detail (str, optional): Error message. Defaults to "Bad request".
            code (str, optional): Error code. Defaults to "bad_request".
        """
        super().__init__(status_code=400, detail=detail, code=code)


class RateLimitException(ChatServiceException):
    """Exception for rate limit errors."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        code: str = "rate_limit_exceeded",
        retry_after: Optional[int] = None,
    ):
        """
        Initialize RateLimitException.

        Args:
            detail (str, optional): Error message. Defaults to "Rate limit exceeded".
            code (str, optional): Error code. Defaults to "rate_limit_exceeded".
            retry_after (Optional[int], optional): Seconds to wait before retrying. Defaults to None.
        """
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(status_code=429, detail=detail, code=code, headers=headers)


class ServiceUnavailableException(ChatServiceException):
    """Exception for service unavailable errors."""

    def __init__(
        self, detail: str = "Service unavailable", code: str = "service_unavailable"
    ):
        """
        Initialize ServiceUnavailableException.

        Args:
            detail (str, optional): Error message. Defaults to "Service unavailable".
            code (str, optional): Error code. Defaults to "service_unavailable".
        """
        super().__init__(status_code=503, detail=detail, code=code)


class DatabaseException(ChatServiceException):
    """Exception for database errors."""

    def __init__(self, detail: str = "Database error", code: str = "database_error"):
        """
        Initialize DatabaseException.

        Args:
            detail (str, optional): Error message. Defaults to "Database error".
            code (str, optional): Error code. Defaults to "database_error".
        """
        super().__init__(status_code=500, detail=detail, code=code)


class LLMServiceException(ChatServiceException):
    """Exception for LLM service errors."""

    def __init__(
        self, detail: str = "LLM service error", code: str = "llm_service_error"
    ):
        """
        Initialize LLMServiceException.

        Args:
            detail (str, optional): Error message. Defaults to "LLM service error".
            code (str, optional): Error code. Defaults to "llm_service_error".
        """
        super().__init__(status_code=502, detail=detail, code=code)
