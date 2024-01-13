from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.settings import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    f"postgresql://{settings.postgres_user}:{settings.postgres_password}@"
    f"{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)
