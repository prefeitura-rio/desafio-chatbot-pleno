"""
Configuration settings for the Authentication Service.

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
        REDIS_URI (str): Redis connection string
        JWT_SECRET (str): Secret key for JWT token generation/validation
        JWT_ALGORITHM (str): Algorithm used for JWT
        ACCESS_TOKEN_EXPIRE_MINUTES (int): JWT token expiration time in minutes
        REFRESH_TOKEN_EXPIRE_DAYS (int): Refresh token expiration time in days
        CORS_ORIGINS (List[str]): Allowed origins for CORS
        PASSWORD_RESET_TOKEN_EXPIRE_HOURS (int): Password reset token expiration time in hours
        VERIFICATION_TOKEN_EXPIRE_HOURS (int): Email verification token expiration time in hours
    """

    # Application Settings
    APP_NAME: str = "Authentication Service"
    DEBUG: bool = False

    # Database and Storage
    DATABASE_URL: str
    REDIS_URI: str = "redis://redis:6379/0"

    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24  # 24 hours
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 48  # 48 hours

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Password Policy
    MIN_PASSWORD_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBER: bool = True
    PASSWORD_REQUIRE_SPECIAL_CHAR: bool = True

    # Rate Limiting
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 5  # 5 attempts per minute
    SIGNUP_RATE_LIMIT_PER_DAY: int = 10   # 10 accounts per day from same IP

    # Session Management
    MAX_SESSIONS_PER_USER: int = 5  # Maximum number of concurrent sessions per user

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