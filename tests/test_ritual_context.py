"""Tests for the ritual context calculator."""

from __future__ import annotations

from datetime import datetime, timezone

from agentic_ritual_engine.core.ritual_context import RitualContext, compute_context


def test_compute_context_returns_expected_keys():
    """compute_context should return all documented fields."""
    dt = datetime(2025, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
    result = compute_context(lat=36.17, lon=-115.14, dt=dt)

    assert "datetime" in result
    assert "location" in result
    assert "moon_phase" in result
    assert "sunrise" in result
    assert "sunset" in result
    assert "weekday" in result
    assert "planetary_hour_guess" in result


def test_compute_context_location():
    """Location should echo the supplied coordinates."""
    result = compute_context(lat=51.5, lon=-0.1)
    assert result["location"]["lat"] == 51.5
    assert result["location"]["lon"] == -0.1


def test_compute_context_weekday():
    """Known date should produce expected weekday."""
    dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)  # Wednesday
    result = compute_context(lat=0, lon=0, dt=dt)
    assert result["weekday"] == "Wednesday"


def test_ritual_context_dataclass():
    """RitualContext should initialise and describe itself."""
    ctx = RitualContext()
    assert ctx.loaded is False
    ctx.load_defaults()
    assert ctx.loaded is True
    desc = ctx.describe()
    assert "Ritual context" in desc
