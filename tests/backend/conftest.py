"""Shared fixtures for backend tests."""

import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Override settings before importing app
os.environ["AUTOSUB_DB_PATH"] = ":memory:"
os.environ["AUTOSUB_REDIS_URL"] = "redis://localhost:6379/15"
os.environ["AUTOSUB_VIDEO_INPUT_DIR"] = tempfile.mkdtemp()
os.environ["AUTOSUB_SUBTITLE_OUTPUT_DIR"] = tempfile.mkdtemp()
os.environ["AUTOSUB_VIDEO_OUTPUT_DIR"] = tempfile.mkdtemp()
os.environ["AUTOSUB_MODEL_DIR"] = tempfile.mkdtemp()
os.environ["AUTOSUB_TEMP_DIR"] = tempfile.mkdtemp()

from backend.db.database import Base, get_db
from backend.main import app


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine (in-memory SQLite)."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a test database session that rolls back after each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def temp_video(tmp_path):
    """Create a fake video file for testing."""
    video = tmp_path / "test_video.mp4"
    video.write_bytes(b"\x00" * 1024)
    return str(video)


@pytest.fixture
def temp_srt(tmp_path):
    """Create a sample SRT file for testing."""
    srt = tmp_path / "test.srt"
    srt.write_text(
        "1\n"
        "00:00:01,000 --> 00:00:03,000\n"
        "Hello world\n"
        "\n"
        "2\n"
        "00:00:04,000 --> 00:00:06,500\n"
        "[Speaker 1]: This is a test\n"
        "\n"
        "3\n"
        "00:00:07,000 --> 00:00:10,000\n"
        "Final subtitle line\n",
        encoding="utf-8",
    )
    return str(srt)
