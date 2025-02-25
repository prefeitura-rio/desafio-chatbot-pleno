"""
User service for handling user-related operations.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Union

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """
    User service for handling user-related operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User email

        Returns:
            Optional[User]: User if found, None otherwise
        """
        result = await self.db.execute(select(User).where(func.lower(User.email) == email.lower()))
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Args:
            username: Username

        Returns:
            Optional[User]: User if found, None otherwise
        """
        if not username:
            return None
        result = await self.db.execute(
            select(User).where(func.lower(User.username) == username.lower())
        )
        return result.scalars().first()

    async def create(self, user_data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            user_data: User data

        Returns:
            User: Created user

        Raises:
            ConflictException: If the email or username is already taken
        """
        # Check if email already exists
        existing_user = await self.get_by_email(user_data.email)
        if existing_user:
            raise ConflictException(detail="Email already registered", code="email_exists")

        # Check if username already exists if provided
        if user_data.username:
            existing_username = await self.get_by_username(user_data.username)
            if existing_username:
                raise ConflictException(detail="Username already taken", code="username_exists")

        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )

        try:
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(detail="User creation failed", code="db_integrity_error")

    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[User]:
        """
        Update a user.

        Args:
            user_id: User ID
            user_data: User data

        Returns:
            Optional[User]: Updated user if found, None otherwise

        Raises:
            NotFoundException: If the user is not found
            ConflictException: If the email or username is already taken
        """
        # Check if user exists
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found", code="user_not_found")

        # Prepare update data
        update_data = user_data.dict(exclude_unset=True)

        # Check email uniqueness if changing email
        if "email" in update_data and update_data["email"] != user.email:
            existing_email = await self.get_by_email(update_data["email"])
            if existing_email:
                raise ConflictException(detail="Email already in use", code="email_exists")

        # Check username uniqueness if changing username
        if (
            "username" in update_data
            and update_data["username"]
            and update_data["username"] != user.username
        ):
            existing_username = await self.get_by_username(update_data["username"])
            if existing_username:
                raise ConflictException(detail="Username already taken", code="username_exists")

        # Update user
        try:
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
                .returning(User)
            )
            result = await self.db.execute(update_stmt)
            await self.db.flush()
            return result.scalars().first()
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(detail="User update failed", code="db_integrity_error")

    async def update_password(self, user_id: uuid.UUID, new_password: str) -> bool:
        """
        Update user password.

        Args:
            user_id: User ID
            new_password: New password

        Returns:
            bool: True if successful, False otherwise

        Raises:
            NotFoundException: If the user is not found
        """
        # Check if user exists
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found", code="user_not_found")

        # Update password
        try:
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(hashed_password=get_password_hash(new_password))
            )
            await self.db.execute(update_stmt)
            await self.db.flush()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def activate(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Activate a user.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: Activated user if found, None otherwise

        Raises:
            NotFoundException: If the user is not found
        """
        # Check if user exists
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found", code="user_not_found")

        # Activate user
        try:
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(is_active=True)
                .returning(User)
            )
            result = await self.db.execute(update_stmt)
            await self.db.flush()
            return result.scalars().first()
        except Exception:
            await self.db.rollback()
            return None

    async def deactivate(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Deactivate a user.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: Deactivated user if found, None otherwise

        Raises:
            NotFoundException: If the user is not found
        """
        # Check if user exists
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found", code="user_not_found")

        # Deactivate user
        try:
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(is_active=False)
                .returning(User)
            )
            result = await self.db.execute(update_stmt)
            await self.db.flush()
            return result.scalars().first()
        except Exception:
            await self.db.rollback()
            return None

    async def verify_email(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Verify a user's email.

        Args:
            user_id: User ID

        Returns:
            Optional[User]: Verified user if found, None otherwise

        Raises:
            NotFoundException: If the user is not found
        """
        # Check if user exists
        user = await self.get_by_id(user_id)
        if not user:
            raise NotFoundException(detail="User not found", code="user_not_found")

        # Verify email
        try:
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(is_verified=True)
                .returning(User)
            )
            result = await self.db.execute(update_stmt)
            await self.db.flush()
            return result.scalars().first()
        except Exception:
            await self.db.rollback()
            return None

    async def update_last_login(self, user_id: uuid.UUID) -> bool:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            update_stmt = (
                update(User)
                .where(User.id == user_id)
                .values(last_login=datetime.utcnow())
            )
            await self.db.execute(update_stmt)
            await self.db.flush()
            return True
        except Exception:
            await self.db.rollback()
            return False 