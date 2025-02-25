import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base

logger = logging.getLogger(__name__)

# Create async database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
async_session_factory = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def init_db() -> None:
    """
    Initialize database - create tables if they don't exist.

    Note: In production, use Alembic for migrations instead of
    creating tables directly.
    """
    try:
        # Create tables
        async with engine.begin() as conn:
            if settings.DEBUG:
                # Only create tables automatically in debug mode
                # In production, use Alembic migrations
                await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_db_connections() -> None:
    """Close database connections."""
    try:
        await engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session.

    Yields:
        AsyncSession: Database session

    Example:
        ```
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            items = await db.execute(select(Item))
            return items.scalars().all()
        ```
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
