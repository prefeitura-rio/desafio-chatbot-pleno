"""
Authentication schemas.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    """
    Token response schema.

    Attributes:
        access_token (str): Access token
        refresh_token (str): Refresh token
        token_type (str): Token type
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """
    Login request schema.

    Attributes:
        email (str): User email
        password (str): User password
    """

    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """
    Refresh token request schema.

    Attributes:
        refresh_token (str): Refresh token
    """

    refresh_token: str


class RegisterRequest(BaseModel):
    """
    Registration request schema.

    Attributes:
        email (EmailStr): User email
        username (str): Username
        password (str): User password
        full_name (str): Full name
    """

    email: EmailStr
    username: Optional[str] = None
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None 