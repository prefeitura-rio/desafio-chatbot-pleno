"""
Configuration settings for the Chat Service.

This module loads environment variables and provides a centralized
configuration for the entire application.
"""

import os
from typing import List, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Attributes:
        APP_NAME (str): Name of the application
        DEBUG (bool): Debug mode flag
        DATABASE_URL (str): PostgreSQL connection string
        REDIS_URL (str): Redis connection string
        RABBITMQ_URL (str): RabbitMQ connection string
        JWT_SECRET (str): Secret key for JWT token generation/validation
        JWT_ALGORITHM (str): Algorithm used for JWT
        ACCESS_TOKEN_EXPIRE_MINUTES (int): JWT token expiration time in minutes
        CORS_ORIGINS (List[str]): Allowed origins for CORS
        EMBEDDING_MODEL (str): Model to use for text embeddings
        EMBEDDING_DIMENSION (int): Dimension of text embeddings
        CACHE_TTL_SECONDS (int): Default cache TTL in seconds
    """

    # Application Settings
    APP_NAME: str = "Chat Service"
    DEBUG: bool = False

    # Database and Storage
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379/0"
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 1 week

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # AI and Embeddings
    EMBEDDING_MODEL: str = "text-embedding-ada-002"  # OpenAI's embedding model
    EMBEDDING_DIMENSION: int = 1536  # Dimension for OpenAI's text-embedding-ada-002

    # Caching
    CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # RabbitMQ
    RABBITMQ_QUEUE_NAME: str = "llm_requests"
    RABBITMQ_DEAD_LETTER_QUEUE: str = "llm_dead_letter"

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60

    # Message Queue
    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 5

    @field_validator("DATABASE_URL")
    def validate_database_url(cls, v: Optional[str]) -> str:
        """
        Validate that DATABASE_URL is provided.

        Args:
            v: The database URL value

        Returns:
            str: The validated database URL

        Raises:
            ValueError: If database URL is not provided
        """
        if not v:
            raise ValueError("DATABASE_URL must be provided")
        return v

    @field_validator("JWT_SECRET")
    def validate_jwt_secret(cls, v: Optional[str]) -> str:
        """
        Validate that JWT_SECRET is provided and has minimum length.

        Args:
            v: The JWT secret value

        Returns:
            str: The validated JWT secret

        Raises:
            ValueError: If JWT secret is not provided or too short
        """
        if not v:
            raise ValueError("JWT_SECRET must be provided")
        if len(v) < 32:
            raise ValueError("JWT_SECRET should be at least 32 characters")
        return v

    @field_validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """
        Convert comma-separated CORS_ORIGINS string to list if needed.

        Args:
            v: The CORS origins value

        Returns:
            List[str]: The validated CORS origins list
        """
        if isinstance(v, str) and v != "*":
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        """Pydantic config"""

        env_file = ".env"
        case_sensitive = True


# Create a global settings instance
settings = Settings()
