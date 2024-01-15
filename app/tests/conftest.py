import os

import dotenv

dotenv.load_dotenv()

import pytest
from app.tests.fixtures import create_db


@pytest.fixture(scope="function")
def db_session():
    # Connect to your test database and create tables
    create_db()

    yield

    # Tear down: Disconnect and drop the tables and delete the database file
    os.remove("test.db")
