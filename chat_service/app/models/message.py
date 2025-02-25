import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    Text,
    Enum,
    func,
    Integer,
    Float,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.db.base import Base


class MessageRole(str, PyEnum):
    """Enum for message roles"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"  # TODO: Alterar system prompt (trazer algo próximo do que o que a Anthropic disponibiliza como referencia do Claude)


class Message(Base):
    """
    Represents a message in a conversation.

    Attributes:
        id (UUID): Primary key
        conversation_id (UUID): Foreign key to the conversation
        role (MessageRole): Role of the message sender (user/assistant/system)
        content (str): Content of the message
        user_id (UUID, optional): User who sent the message (if role is "user")
        embedding (Vector): Vector embedding of the message content
        created_at (datetime): When the message was created
        conversation (relationship): Relationship to the parent conversation
    """

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Metadata for tracking
    model_used = Column(String(255), nullable=True)
    tokens_prompt = Column(Integer, nullable=True)
    tokens_completion = Column(Integer, nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        """String representation of Message"""
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"
