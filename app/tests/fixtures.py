from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base


def get_test_db():
    test_engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
