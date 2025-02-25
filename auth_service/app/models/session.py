"""
User session model.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class Session(Base):
    """
    User session model for managing active login sessions.

    Attributes:
        id (UUID): Session ID
        user_id (UUID): User ID (foreign key)
        refresh_token (str): Refresh token for this session
        user_agent (str): User agent information
        ip_address (str): IP address of the client
        is_active (bool): Whether the session is active
        expires_at (datetime): Session expiration time
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
    """

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token = Column(String(255), nullable=False, unique=True, index=True)
    user_agent = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # Max length for IPv6
    is_active = Column(Boolean(), default=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", lazy="joined")
    
    def __repr__(self) -> str:
        """
        Get string representation of the session.

        Returns:
            str: String representation
        """
        return f"<Session id={self.id}, user_id={self.user_id}, is_active={self.is_active}>" 