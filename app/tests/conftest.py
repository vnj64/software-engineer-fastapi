import os

import dotenv

dotenv.load_dotenv()

import pytest

from app.tests.fixtures import create_db


@pytest.fixture(scope="function")
def db_session():
    create_db()

    yield

    os.remove("test.db")
