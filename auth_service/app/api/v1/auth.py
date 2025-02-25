"""
Authentication API routes.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CredentialsException,
    UnauthorizedException,
    RateLimitException,
    NotFoundException,
)
from app.db.base import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
)
from app.schemas.user import UserResponse
from app.services.auth import AuthService
from app.services.redis import RedisService
from app.core.security import oauth2_scheme, decode_token


# Create router
router = APIRouter()

# Create Redis service
redis_service = RedisService()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.
    """
    # Get client IP
    client_ip = request.client.host
    
    # Check rate limit
    is_allowed, attempts, reset_in = await redis_service.signup_rate_limit(client_ip)
    if not is_allowed:
        raise RateLimitException(
            detail=f"Too many signup attempts. Try again in {reset_in} seconds."
        )
    
    # Register user
    auth_service = AuthService(db)
    user = await auth_service.register(register_data)
    
    # Convert to response model
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    user_agent: str = Header(None),
):
    """
    Log in a user and get access token.
    """
    # Get client IP
    client_ip = request.client.host
    
    # Check rate limit
    is_allowed, attempts, reset_in = await redis_service.login_rate_limit(login_data.email)
    if not is_allowed:
        raise RateLimitException(
            detail=f"Too many login attempts. Try again in {reset_in} seconds."
        )
    
    # Authenticate user
    auth_service = AuthService(db)
    try:
        return await auth_service.login(
            login_data,
            user_agent=user_agent,
            ip_address=client_ip,
        )
    except CredentialsException as e:
        # Increment rate limit counter even on failure
        await redis_service.login_rate_limit(login_data.email)
        raise e


@router.post("/login/oauth", response_model=TokenResponse)
async def login_oauth(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    user_agent: str = Header(None),
):
    """
    OAuth2 compatible login endpoint.
    """
    # Get client IP
    client_ip = request.client.host
    
    # Check rate limit
    is_allowed, attempts, reset_in = await redis_service.login_rate_limit(form_data.username)
    if not is_allowed:
        raise RateLimitException(
            detail=f"Too many login attempts. Try again in {reset_in} seconds."
        )
    
    # Create login data
    login_data = LoginRequest(email=form_data.username, password=form_data.password)
    
    # Authenticate user
    auth_service = AuthService(db)
    try:
        return await auth_service.login(
            login_data,
            user_agent=user_agent,
            ip_address=client_ip,
        )
    except CredentialsException as e:
        # Increment rate limit counter even on failure
        await redis_service.login_rate_limit(form_data.username)
        raise e


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token.
    """
    auth_service = AuthService(db)
    return await auth_service.refresh_token(refresh_token_data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    refresh_token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Log out a user.
    """
    try:
        # Decode token
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(detail="Invalid token", code="invalid_token_payload")
        
        # Logout user
        auth_service = AuthService(db)
        success = await auth_service.logout(user_id, refresh_token_data.refresh_token)
        if not success:
            raise UnauthorizedException(detail="Logout failed", code="logout_failed")
        
        # Revoke token
        await auth_service.revoke_token(token, user_id)
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception:
        # Return success even on error to avoid leaking information
        return Response(status_code=status.HTTP_204_NO_CONTENT) 