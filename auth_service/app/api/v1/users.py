"""
User API routes.
"""

import uuid
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    UnauthorizedException, 
    NotFoundException,
    PermissionDeniedException,
)
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import UserService
from app.core.security import oauth2_scheme, decode_token

# Create router
router = APIRouter()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Get current user from token.

    Args:
        db: Database session
        token: JWT token

    Returns:
        User: Current user

    Raises:
        UnauthorizedException: If token is invalid or user not found
    """
    try:
        # Decode token
        payload = decode_token(token)
        
        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(detail="Invalid token", code="invalid_token_payload")
        
        # Get user
        user_service = UserService(db)
        user = await user_service.get_by_id(uuid.UUID(user_id))
        
        if not user:
            raise UnauthorizedException(detail="User not found", code="user_not_found")
        
        if not user.is_active:
            raise UnauthorizedException(detail="Inactive user", code="inactive_user")
        
        return user
    except Exception as e:
        raise UnauthorizedException(detail=str(e), code="authentication_error")


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current superuser.

    Args:
        current_user: Current user

    Returns:
        User: Current superuser

    Raises:
        PermissionDeniedException: If user is not a superuser
    """
    if not current_user.is_superuser:
        raise PermissionDeniedException(detail="Insufficient permissions", code="not_superuser")
    return current_user


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user information.
    """
    user_service = UserService(db)
    updated_user = await user_service.update(current_user.id, user_data)
    return UserResponse.model_validate(updated_user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user by ID (admin only).
    """
    user_service = UserService(db)
    user = await user_service.get_by_id(user_id)
    
    if not user:
        raise NotFoundException(detail="User not found", code="user_not_found")
    
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    user_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    Update user by ID (admin only).
    """
    user_service = UserService(db)
    updated_user = await user_service.update(user_id, user_data)
    return UserResponse.model_validate(updated_user) 