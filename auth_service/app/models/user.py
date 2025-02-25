"""
User model.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.base import Base


class User(Base):
    """
    User model representing application users.

    Attributes:
        id (UUID): User ID
        email (str): User email
        username (str): Username
        hashed_password (str): Hashed password
        is_active (bool): Active status
        is_verified (bool): Email verification status
        is_superuser (bool): Superuser status
        full_name (str): Full name
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean(), default=True)
    is_verified = Column(Boolean(), default=False)
    is_superuser = Column(Boolean(), default=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    
    # Additional profile fields
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Last login
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        """
        Get string representation of the user.

        Returns:
            str: String representation
        """
        return f"<User id={self.id}, email={self.email}, username={self.username}>" 