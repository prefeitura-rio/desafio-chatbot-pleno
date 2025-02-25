"""
User schemas.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, UUID4, validator


class UserBase(BaseModel):
    """
    Base user schema.

    Attributes:
        email (EmailStr): User email
        username (str): Username
        full_name (str): Full name
        is_active (bool): Active status
        is_verified (bool): Email verification status
    """

    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False


class UserCreate(UserBase):
    """
    User creation schema.

    Attributes:
        password (str): User password
    """

    password: str = Field(..., min_length=8)
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(char.isupper() for char in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(char.islower() for char in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(char.isdigit() for char in v):
            raise ValueError("Password must contain at least one number")
        if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for char in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserUpdate(BaseModel):
    """
    User update schema.

    Attributes:
        email (EmailStr): User email
        username (str): Username
        full_name (str): Full name
        bio (str): User bio
        phone_number (str): Phone number
        profile_image_url (str): Profile image URL
    """

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    profile_image_url: Optional[str] = None


class UserResponse(UserBase):
    """
    User response schema.

    Attributes:
        id (UUID4): User ID
        bio (str): User bio
        profile_image_url (str): Profile image URL
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """

    id: UUID4
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        orm_mode = True
        from_attributes = True


class UserInDB(UserResponse):
    """
    User in database schema.

    Attributes:
        hashed_password (str): Hashed password
        is_superuser (bool): Superuser status
    """

    hashed_password: str
    is_superuser: bool = False

    class Config:
        """Pydantic config."""

        orm_mode = True
        from_attributes = True 