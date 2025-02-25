"""
Chat Service - Main FastAPI Application

This module serves as the entry point for the Chat Service, setting up FastAPI,
database connections, and routers.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api import conversations, messages, search
from app.core.config import settings
from app.core.exceptions import ChatServiceException
from app.db.session import init_db, close_db_connections
from app.utils.cache import init_redis, close_redis
from app.utils.queue import init_rabbitmq, close_rabbitmq

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application lifecycle events - setup and teardown of connections.
    """
    # Initialize connections
    await init_db()
    await init_redis()
    await init_rabbitmq()

    logger.info("Application startup complete")
    yield

    # Close connections
    await close_db_connections()
    await close_redis()
    await close_rabbitmq()
    logger.info("Application shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="""
    Chat Service API for LLM Chat Application.
    
    This service manages conversations, messages, and provides semantic search 
    functionality using pgvector for vector embeddings.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")


# Exception handlers
@app.exception_handler(ChatServiceException)
async def chat_service_exception_handler(request: Request, exc: ChatServiceException):
    """Handle custom service exceptions"""
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "code": "validation_error"},
    )


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancer checks.

    Returns:
        dict: Status information
    """
    return {"status": "healthy", "service": settings.APP_NAME, "version": app.version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
