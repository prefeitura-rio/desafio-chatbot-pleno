"""
Token blacklist model.
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class TokenBlacklist(Base):
    """
    Token blacklist model for tracking revoked tokens.

    Attributes:
        id (UUID): Blacklist entry ID
        token_jti (str): JWT token ID (jti claim)
        user_id (UUID): User ID (foreign key)
        expires_at (datetime): Token expiration time
        created_at (datetime): Creation timestamp
    """

    __tablename__ = "token_blacklist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_jti = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", lazy="joined")
    
    def __repr__(self) -> str:
        """
        Get string representation of the blacklist entry.

        Returns:
            str: String representation
        """
        return f"<TokenBlacklist id={self.id}, token_jti={self.token_jti}, user_id={self.user_id}>" 