import dotenv
import pytest
from fastapi.testclient import TestClient

dotenv.load_dotenv()

from app.tests.fixtures import get_test_db  # noqa: E402

from ..main import server  # noqa: E402


@pytest.fixture
def client():
    return TestClient(server)


@pytest.fixture
def db():
    yield get_test_db()
