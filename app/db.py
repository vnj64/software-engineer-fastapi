from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.settings import settings

Base = declarative_base()


async def create_db_session():
    engine = create_async_engine(
        url=f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@"
        f"{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}",
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        expire_on_commit=True,
        class_=AsyncSession,
    )

    return async_session
