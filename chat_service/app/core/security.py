# core/security.py
"""
Security utilities for authentication and authorization.
"""

from datetime import datetime, timedelta
import jwt
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token.

    Args:
        data (Dict[str, Any]): Token data
        expires_delta (Optional[timedelta], optional): Token expiration time.
            Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token.

    Args:
        token (str): JWT token

    Returns:
        Dict[str, Any]: Decoded token data

    Raises:
        UnauthorizedException: If token is invalid
    """
    try:
        # Decode token
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )

        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(detail="Token expired", code="token_expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(detail="Invalid token", code="invalid_token")


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """
    Get current authenticated user from token.

    Args:
        token (str, optional): JWT token. Defaults to Depends(oauth2_scheme).

    Returns:
        Dict[str, Any]: User data

    Raises:
        UnauthorizedException: If token is invalid or user not found
    """
    try:
        # Decode token
        payload = decode_token(token)

        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(
                detail="Invalid token", code="invalid_token_payload"
            )

        # Return user data
        return {"id": user_id}
    except Exception as e:
        raise UnauthorizedException(detail=str(e), code="authentication_error")
