"""Tests for the command parser."""

from __future__ import annotations

import pytest

from agentic_ritual_engine.core.command_parser import CommandParser, ParsedCommand


@pytest.fixture()
def parser():
    return CommandParser()


def test_parse_basic(parser):
    """Basic parse splits action from payload."""
    result = parser.parse("KRONKETA assemble the council")
    assert isinstance(result, ParsedCommand)
    assert result.action == "kronketa"
    assert "assemble" in result.payload


def test_parse_empty_raises(parser):
    """Empty input should raise ValueError."""
    with pytest.raises(ValueError, match="empty"):
        parser.parse("")


def test_parse_and_execute_known_trigger(parser):
    """Known triggers should be detected and executed."""
    result = parser.parse_and_execute("fire up KRONKETA now")
    assert result["trigger"] == "kronketa"
    assert result["status"] == "ok"


def test_parse_and_execute_unknown_trigger(parser):
    """Unknown text should return ignored status."""
    result = parser.parse_and_execute("random nonsense text")
    assert result["trigger"] is None
    assert result["status"] == "ignored"


def test_parse_and_execute_gavel(parser):
    result = parser.parse_and_execute("Bring the GAVEL down")
    assert result["trigger"] == "gavel"
    assert result["status"] == "ok"


def test_parse_and_execute_chrono_walker(parser):
    result = parser.parse_and_execute("Activate the CHRONO_WALKER simulation")
    assert result["trigger"] == "chrono_walker"
    assert result["status"] == "ok"
