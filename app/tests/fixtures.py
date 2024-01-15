from sqlalchemy.orm import declarative_base, sessionmaker
from sqlmodel import SQLModel, create_engine

from app.settings import settings

Base = declarative_base()
if settings.mode == "testing":
    SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost:5433/testdb"
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@" \
                              f"{settings.postgres_server}:{settings.postgres_port}/{settings.postgres_db}"


engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db():
    if settings.mode == "testing":
        SQLModel.metadata.drop_all(engine)

    SQLModel.metadata.create_all(engine)


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
