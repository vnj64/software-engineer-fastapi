import os

import dotenv
import pytest

dotenv.load_dotenv()

from app.tests.fixtures import create_db  # noqa: E402


@pytest.fixture(scope="function")
def db_session():
    create_db()

    yield

    os.remove("test.db")
