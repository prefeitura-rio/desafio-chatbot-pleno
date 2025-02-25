"""API module initialization."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router

# Create v1 router
api_router_v1 = APIRouter(prefix="/api/v1")

# Include routers
api_router_v1.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router_v1.include_router(users_router, prefix="/users", tags=["users"]) 