"""
Security utilities for authentication and authorization.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.exceptions import (
    UnauthorizedException,
    CredentialsException,
    TokenExpiredException,
)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: The plain text password
        hashed_password: The hashed password

    Returns:
        bool: True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: The plain text password

    Returns:
        str: The hashed password
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> Dict[str, Union[bool, str]]:
    """
    Validate password strength based on configured policies.

    Args:
        password: The password to validate

    Returns:
        Dict[str, Union[bool, str]]: Validation result with success flag and error message
    """
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return {
            "valid": False,
            "message": f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters long",
        }

    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(char.isupper() for char in password):
        return {"valid": False, "message": "Password must contain at least one uppercase letter"}

    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(char.islower() for char in password):
        return {"valid": False, "message": "Password must contain at least one lowercase letter"}

    if settings.PASSWORD_REQUIRE_NUMBER and not any(char.isdigit() for char in password):
        return {"valid": False, "message": "Password must contain at least one number"}

    if settings.PASSWORD_REQUIRE_SPECIAL_CHAR and not any(
        char in string.punctuation for char in password
    ):
        return {
            "valid": False,
            "message": "Password must contain at least one special character",
        }

    return {"valid": True, "message": "Password meets strength requirements"}


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Token data
        expires_delta: Token expiration time.
            Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: JWT token
    """
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Token data

    Returns:
        str: JWT refresh token
    """
    to_encode = data.copy()

    # Set expiration time
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})

    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode JWT token.

    Args:
        token: JWT token

    Returns:
        Dict[str, Any]: Decoded token data

    Raises:
        TokenExpiredException: If token is expired
        UnauthorizedException: If token is invalid
    """
    try:
        # Decode token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredException(detail="Token expired", code="token_expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(detail="Invalid token", code="invalid_token")


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.

    Args:
        email: User email

    Returns:
        str: Password reset token
    """
    # Set expiration time
    expire = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    
    # Create token data
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "password_reset",
        "jti": secrets.token_hex(32),  # Add a unique token ID
    }
    
    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


def generate_email_verification_token(email: str) -> str:
    """
    Generate an email verification token.

    Args:
        email: User email

    Returns:
        str: Email verification token
    """
    # Set expiration time
    expire = datetime.utcnow() + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS)
    
    # Create token data
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "email_verification",
        "jti": secrets.token_hex(32),  # Add a unique token ID
    }
    
    # Encode token
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    
    return encoded_jwt


def generate_random_password(length: int = 12) -> str:
    """
    Generate a random secure password.

    Args:
        length: Password length

    Returns:
        str: Random password
    """
    # Define character sets
    uppercase_letters = string.ascii_uppercase
    lowercase_letters = string.ascii_lowercase
    digits = string.digits
    special_chars = string.punctuation
    
    # Ensure at least one of each type
    password = [
        secrets.choice(uppercase_letters),
        secrets.choice(lowercase_letters),
        secrets.choice(digits),
        secrets.choice(special_chars),
    ]
    
    # Fill the rest with random characters
    for _ in range(length - 4):
        password.append(
            secrets.choice(uppercase_letters + lowercase_letters + digits + special_chars)
        )
    
    # Shuffle the password
    secrets.SystemRandom().shuffle(password)
    
    # Convert to string
    return "".join(password) 