"""Tests for the FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agentic_ritual_engine.core import symbolic_kb
from agentic_ritual_engine.main import app, kb


@pytest.fixture(autouse=True)
def _setup_db(tmp_path):
    """Initialise a temp SQLite DB and wire it into the app's global KB."""
    db_path = tmp_path / "test_ritual.db"
    db_url = f"sqlite:///{db_path}"

    # Reset module-level engine state so init_db creates fresh tables
    symbolic_kb._engine = None
    symbolic_kb._SessionLocal = None

    symbolic_kb.init_db(db_url)
    kb.engine_url = db_url
    kb.is_initialized = True
    yield
    symbolic_kb._engine = None
    symbolic_kb._SessionLocal = None


@pytest.fixture()
def client():
    return TestClient(app)


def test_symbols_endpoint_empty(client):
    """GET /symbols should return an empty list when no data exists."""
    response = client.get("/symbols")
    assert response.status_code == 200
    assert response.json() == []


def test_symbols_endpoint_invalid_filters(client):
    """GET /symbols with invalid JSON filters should return 400."""
    response = client.get("/symbols", params={"filters": "not-json"})
    assert response.status_code == 400


def test_symbol_not_found(client):
    """GET /symbols/{slug} should return 404 for missing symbols."""
    response = client.get("/symbols/nonexistent-slug")
    assert response.status_code == 404


def test_image_not_found(client):
    """GET /images/{id} should return 404 for missing images."""
    response = client.get("/images/999")
    assert response.status_code == 404


def test_context_endpoint(client):
    """GET /context should return celestial data."""
    response = client.get("/context", params={"lat": 36.17, "lon": -115.14})
    assert response.status_code == 200
    data = response.json()
    assert "moon_phase" in data
    assert "weekday" in data
