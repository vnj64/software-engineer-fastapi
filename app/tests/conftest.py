import dotenv
import pytest
from fastapi.testclient import TestClient

from app.tests.fixtures import get_test_db

from ..main import server

dotenv.load_dotenv()


@pytest.fixture
def client():
    return TestClient(server)


@pytest.fixture
def db():
    yield get_test_db()
