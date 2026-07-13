"""Test DB fixtures. Points at a Postgres test database, creates the schema from
the models, and hands each test a session wrapped in a rolled-back transaction."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
import app.models  # noqa: F401  (register tables on Base.metadata)

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://limelight:limelight@127.0.0.1:5432/limelight_test",
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_URL, future=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    txn = connection.begin()
    Session = sessionmaker(bind=connection, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        txn.rollback()
        connection.close()
