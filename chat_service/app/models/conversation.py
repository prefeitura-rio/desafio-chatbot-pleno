import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Conversation(Base):
    """
    Represents a conversation between a user and the chat system.

    Attributes:
        id (UUID): Primary key
        user_id (UUID): Foreign key to the user who owns this conversation
        title (str): Title of the conversation
        system_prompt (str, optional): System prompt for the conversation
        created_at (datetime): When the conversation was created
        updated_at (datetime): When the conversation was last updated
        messages (relationship): Relationship to associated messages
    """

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of Conversation"""
        return f"<Conversation(id={self.id}, title='{self.title}')>"
