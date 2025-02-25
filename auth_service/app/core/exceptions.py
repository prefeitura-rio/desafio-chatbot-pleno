"""
Custom exceptions for the Authentication Service.
"""

from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base API exception."""

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[Dict[str, Any]] = None,
        code: str = "error",
    ):
        """
        Initialize the exception.

        Args:
            status_code: HTTP status code
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        self.code = code
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class BadRequestException(BaseAPIException):
    """Bad request exception."""

    def __init__(
        self,
        detail: Any = "Bad request",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "bad_request",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail, headers=headers, code=code
        )


class UnauthorizedException(BaseAPIException):
    """Unauthorized exception."""

    def __init__(
        self,
        detail: Any = "Not authenticated",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "unauthorized",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers, code=code
        )


class PermissionDeniedException(BaseAPIException):
    """Permission denied exception."""

    def __init__(
        self,
        detail: Any = "Permission denied",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "permission_denied",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN, detail=detail, headers=headers, code=code
        )


class NotFoundException(BaseAPIException):
    """Not found exception."""

    def __init__(
        self,
        detail: Any = "Not found",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "not_found",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=detail, headers=headers, code=code
        )


class ConflictException(BaseAPIException):
    """Conflict exception."""

    def __init__(
        self,
        detail: Any = "Conflict",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "conflict",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_409_CONFLICT, detail=detail, headers=headers, code=code
        )


class RateLimitException(BaseAPIException):
    """Rate limit exception."""

    def __init__(
        self,
        detail: Any = "Too many requests",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "rate_limit",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
            code=code,
        )


class InternalServerException(BaseAPIException):
    """Internal server exception."""

    def __init__(
        self,
        detail: Any = "Internal server error",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "internal_error",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers,
            code=code,
        )


class CredentialsException(UnauthorizedException):
    """Credentials exception."""

    def __init__(
        self,
        detail: Any = "Invalid credentials",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "invalid_credentials",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(detail=detail, headers=headers, code=code)


class TokenExpiredException(UnauthorizedException):
    """Token expired exception."""

    def __init__(
        self,
        detail: Any = "Token expired",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "token_expired",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(detail=detail, headers=headers, code=code)


class InvalidTokenException(UnauthorizedException):
    """Invalid token exception."""

    def __init__(
        self,
        detail: Any = "Invalid token",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "invalid_token",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(detail=detail, headers=headers, code=code)


class AccountDisabledException(UnauthorizedException):
    """Account disabled exception."""

    def __init__(
        self,
        detail: Any = "Account disabled",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "account_disabled",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(detail=detail, headers=headers, code=code)


class EmailNotVerifiedException(UnauthorizedException):
    """Email not verified exception."""

    def __init__(
        self,
        detail: Any = "Email not verified",
        headers: Optional[Dict[str, Any]] = None,
        code: str = "email_not_verified",
    ):
        """
        Initialize the exception.

        Args:
            detail: Exception detail
            headers: HTTP headers
            code: Error code
        """
        super().__init__(detail=detail, headers=headers, code=code) 