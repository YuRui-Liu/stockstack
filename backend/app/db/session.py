import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(database_url: str | None = None) -> AsyncEngine:
    url = database_url or os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://localhost:5432/stockstack"
    )
    return create_async_engine(url, pool_size=5, max_overflow=5, pool_pre_ping=True)


engine = build_engine()
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
