"""
Authentication service for handling authentication-related operations.
"""

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Union

from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    CredentialsException,
    NotFoundException,
    UnauthorizedException,
    AccountDisabledException,
    EmailNotVerifiedException,
)
from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_password_reset_token,
    generate_email_verification_token,
)
from app.models.session import Session
from app.models.token_blacklist import TokenBlacklist
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.schemas.user import UserCreate
from app.services.user import UserService


class AuthService:
    """
    Authentication service for handling authentication-related operations.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the service.

        Args:
            db: Database session
        """
        self.db = db
        self.user_service = UserService(db)

    async def authenticate(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user.

        Args:
            email: User email
            password: User password

        Returns:
            Optional[User]: User if authentication is successful, None otherwise

        Raises:
            CredentialsException: If credentials are invalid
            AccountDisabledException: If account is disabled
            EmailNotVerifiedException: If email is not verified
        """
        # Get user by email
        user = await self.user_service.get_by_email(email)
        if not user:
            raise CredentialsException(detail="Invalid email or password")

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise CredentialsException(detail="Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise AccountDisabledException(detail="Account is disabled")

        # Update last login
        await self.user_service.update_last_login(user.id)

        return user

    async def login(
        self, login_data: LoginRequest, user_agent: Optional[str] = None, ip_address: Optional[str] = None
    ) -> TokenResponse:
        """
        Log in a user.

        Args:
            login_data: Login data
            user_agent: User agent
            ip_address: IP address

        Returns:
            TokenResponse: Token response

        Raises:
            CredentialsException: If credentials are invalid
            AccountDisabledException: If account is disabled
            EmailNotVerifiedException: If email is not verified
        """
        # Authenticate user
        user = await self.authenticate(login_data.email, login_data.password)

        # Create tokens
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # Store refresh token in session
        await self._create_session(
            user_id=user.id,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Return tokens
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def register(self, register_data: RegisterRequest) -> User:
        """
        Register a new user.

        Args:
            register_data: Registration data

        Returns:
            User: Created user

        Raises:
            ConflictException: If the email or username is already taken
        """
        # Create user data
        user_data = UserCreate(
            email=register_data.email,
            username=register_data.username,
            password=register_data.password,
            full_name=register_data.full_name,
            is_active=True,
            is_verified=False,
        )

        # Create user
        return await self.user_service.create(user_data)

    async def refresh_token(self, refresh_token_data: RefreshTokenRequest) -> TokenResponse:
        """
        Refresh access token.

        Args:
            refresh_token_data: Refresh token data

        Returns:
            TokenResponse: Token response

        Raises:
            UnauthorizedException: If refresh token is invalid or expired
        """
        # Verify refresh token exists in session
        session = await self._get_session_by_refresh_token(refresh_token_data.refresh_token)
        if not session:
            raise UnauthorizedException(detail="Invalid refresh token", code="invalid_refresh_token")

        try:
            # Decode refresh token
            payload = decode_token(refresh_token_data.refresh_token)
            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedException(detail="Invalid token", code="invalid_token_payload")

            # Check if token is blacklisted
            is_blacklisted = await self._is_token_blacklisted(payload.get("jti", ""))
            if is_blacklisted:
                raise UnauthorizedException(detail="Token has been revoked", code="token_revoked")

            # Get user
            user = await self.user_service.get_by_id(uuid.UUID(user_id))
            if not user:
                raise UnauthorizedException(detail="User not found", code="user_not_found")

            # Check if user is active
            if not user.is_active:
                raise AccountDisabledException(detail="Account is disabled")

            # Create new tokens
            access_token = create_access_token(data={"sub": user_id})
            new_refresh_token = create_refresh_token(data={"sub": user_id})

            # Update session with new refresh token
            await self._update_session(
                session.id, 
                new_refresh_token=new_refresh_token
            )

            # Return new tokens
            return TokenResponse(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
            )

        except Exception as e:
            # Revoke session on error
            if session:
                await self._revoke_session(session.id)
            raise UnauthorizedException(detail=str(e), code="refresh_token_error")

    async def logout(self, user_id: uuid.UUID, refresh_token: str) -> bool:
        """
        Log out a user.

        Args:
            user_id: User ID
            refresh_token: Refresh token

        Returns:
            bool: True if successful, False otherwise
        """
        # Get session by refresh token
        session = await self._get_session_by_refresh_token(refresh_token)
        if not session:
            return True  # Session doesn't exist, already logged out

        # Verify user owns session
        if str(session.user_id) != str(user_id):
            return False

        # Revoke session
        return await self._revoke_session(session.id)

    async def logout_all(self, user_id: uuid.UUID) -> bool:
        """
        Log out all sessions for a user.

        Args:
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete all sessions for user
            delete_stmt = delete(Session).where(Session.user_id == user_id)
            await self.db.execute(delete_stmt)
            await self.db.flush()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def verify_email_with_token(self, token: str) -> bool:
        """
        Verify email with token.

        Args:
            token: Email verification token

        Returns:
            bool: True if successful, False otherwise

        Raises:
            UnauthorizedException: If token is invalid or expired
        """
        try:
            # Decode token
            payload = decode_token(token)
            
            # Check token type
            if payload.get("type") != "email_verification":
                raise UnauthorizedException(detail="Invalid token type", code="invalid_token_type")
            
            # Get email
            email = payload.get("sub")
            if not email:
                raise UnauthorizedException(detail="Invalid token", code="invalid_token_payload")
            
            # Get user
            user = await self.user_service.get_by_email(email)
            if not user:
                raise NotFoundException(detail="User not found", code="user_not_found")
            
            # Verify email
            await self.user_service.verify_email(user.id)
            
            return True
        except Exception as e:
            return False

    async def request_password_reset(self, email: str) -> str:
        """
        Request password reset.

        Args:
            email: User email

        Returns:
            str: Password reset token

        Raises:
            NotFoundException: If user is not found
        """
        # Get user
        user = await self.user_service.get_by_email(email)
        if not user:
            raise NotFoundException(detail="User not found", code="user_not_found")
        
        # Generate reset token
        reset_token = generate_password_reset_token(email)
        
        # Store reset token and expiration
        expiration = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        try:
            update_stmt = (
                update(User)
                .where(User.id == user.id)
                .values(
                    password_reset_token=reset_token,
                    password_reset_expires=expiration,
                )
            )
            await self.db.execute(update_stmt)
            await self.db.flush()
        except Exception:
            await self.db.rollback()
            raise
        
        return reset_token

    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """
        Reset password with token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            bool: True if successful, False otherwise

        Raises:
            UnauthorizedException: If token is invalid or expired
            NotFoundException: If user is not found
        """
        try:
            # Decode token
            payload = decode_token(token)
            
            # Check token type
            if payload.get("type") != "password_reset":
                raise UnauthorizedException(detail="Invalid token type", code="invalid_token_type")
            
            # Get email
            email = payload.get("sub")
            if not email:
                raise UnauthorizedException(detail="Invalid token", code="invalid_token_payload")
            
            # Get user
            user = await self.user_service.get_by_email(email)
            if not user:
                raise NotFoundException(detail="User not found", code="user_not_found")
            
            # Verify token matches stored token
            if user.password_reset_token != token:
                raise UnauthorizedException(detail="Invalid token", code="invalid_token")
            
            # Check expiration
            if user.password_reset_expires < datetime.utcnow():
                raise UnauthorizedException(detail="Token expired", code="token_expired")
            
            # Update password
            success = await self.user_service.update_password(user.id, new_password)
            
            # Clear reset token
            if success:
                try:
                    update_stmt = (
                        update(User)
                        .where(User.id == user.id)
                        .values(
                            password_reset_token=None,
                            password_reset_expires=None,
                        )
                    )
                    await self.db.execute(update_stmt)
                    await self.db.flush()
                except Exception:
                    await self.db.rollback()
            
            return success
        except Exception as e:
            return False

    async def revoke_token(self, token: str, user_id: uuid.UUID) -> bool:
        """
        Revoke a token.

        Args:
            token: JWT token
            user_id: User ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Decode token to get expiration and jti
            payload = decode_token(token)
            
            # Extract data
            jti = payload.get("jti", secrets.token_hex(32))
            exp = payload.get("exp", datetime.utcnow() + timedelta(days=7))
            
            # Convert exp to datetime
            if isinstance(exp, int):
                expires_at = datetime.fromtimestamp(exp)
            else:
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            # Add to blacklist
            blacklist_entry = TokenBlacklist(
                token_jti=jti,
                user_id=user_id,
                expires_at=expires_at,
            )
            
            self.db.add(blacklist_entry)
            await self.db.flush()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def _create_session(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Session:
        """
        Create a session.

        Args:
            user_id: User ID
            refresh_token: Refresh token
            user_agent: User agent
            ip_address: IP address

        Returns:
            Session: Created session
        """
        # Calculate expiration (refresh token expiration)
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        # Check if max sessions reached
        await self._enforce_max_sessions(user_id)
        
        # Create session
        session = Session(
            user_id=user_id,
            refresh_token=refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            is_active=True,
            expires_at=expires_at,
        )
        
        try:
            self.db.add(session)
            await self.db.flush()
            await self.db.refresh(session)
            return session
        except IntegrityError:
            await self.db.rollback()
            raise ConflictException(detail="Session creation failed", code="db_integrity_error")

    async def _get_session_by_refresh_token(self, refresh_token: str) -> Optional[Session]:
        """
        Get session by refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Optional[Session]: Session if found, None otherwise
        """
        result = await self.db.execute(
            select(Session)
            .where(
                and_(
                    Session.refresh_token == refresh_token,
                    Session.is_active == True,
                    Session.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalars().first()

    async def _update_session(
        self, session_id: uuid.UUID, new_refresh_token: str
    ) -> Optional[Session]:
        """
        Update a session.

        Args:
            session_id: Session ID
            new_refresh_token: New refresh token

        Returns:
            Optional[Session]: Updated session if found, None otherwise
        """
        # Calculate new expiration
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        try:
            update_stmt = (
                update(Session)
                .where(Session.id == session_id)
                .values(
                    refresh_token=new_refresh_token,
                    expires_at=expires_at,
                    updated_at=datetime.utcnow(),
                )
                .returning(Session)
            )
            result = await self.db.execute(update_stmt)
            await self.db.flush()
            return result.scalars().first()
        except Exception:
            await self.db.rollback()
            return None

    async def _revoke_session(self, session_id: uuid.UUID) -> bool:
        """
        Revoke a session.

        Args:
            session_id: Session ID

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            delete_stmt = delete(Session).where(Session.id == session_id)
            await self.db.execute(delete_stmt)
            await self.db.flush()
            return True
        except Exception:
            await self.db.rollback()
            return False

    async def _enforce_max_sessions(self, user_id: uuid.UUID) -> None:
        """
        Enforce maximum number of sessions per user.

        Args:
            user_id: User ID
        """
        # Get active sessions for user
        result = await self.db.execute(
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.is_active == True,
                    Session.expires_at > datetime.utcnow(),
                )
            )
            .order_by(Session.created_at)
        )
        sessions = result.scalars().all()
        
        # If max sessions reached, delete oldest sessions
        if len(sessions) >= settings.MAX_SESSIONS_PER_USER:
            # Calculate how many sessions to remove
            to_remove = len(sessions) - settings.MAX_SESSIONS_PER_USER + 1
            for i in range(to_remove):
                if i < len(sessions):
                    await self._revoke_session(sessions[i].id)

    async def _is_token_blacklisted(self, token_jti: str) -> bool:
        """
        Check if a token is blacklisted.

        Args:
            token_jti: Token JTI

        Returns:
            bool: True if blacklisted, False otherwise
        """
        if not token_jti:
            return False
            
        result = await self.db.execute(
            select(TokenBlacklist)
            .where(
                and_(
                    TokenBlacklist.token_jti == token_jti,
                    TokenBlacklist.expires_at > datetime.utcnow(),
                )
            )
        )
        return result.scalars().first() is not None 