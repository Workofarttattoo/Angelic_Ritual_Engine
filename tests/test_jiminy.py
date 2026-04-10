"""Tests for the Jiminy Cricket conscience module."""

from __future__ import annotations

from agentic_ritual_engine.core.jimminy_cricket_module import (
    JiminyCricket,
    create_jiminy,
)


def test_create_jiminy_defaults():
    """create_jiminy should return a working JiminyCricket instance."""
    jiminy = create_jiminy()
    assert isinstance(jiminy, JiminyCricket)
    assert jiminy.config.enabled is True


def test_run_checks_all_pass():
    """All checks passing should return True."""
    jiminy = create_jiminy(checks=[lambda: True, lambda: True])
    assert jiminy.run_checks() is True


def test_run_checks_some_fail():
    """A failing check should make run_checks return False."""
    jiminy = create_jiminy(checks=[lambda: True, lambda: False])
    assert jiminy.run_checks() is False


def test_disabled_skips_checks():
    """Disabled conscience should skip checks and return True."""
    jiminy = create_jiminy(enabled=False, checks=[lambda: False])
    assert jiminy.run_checks() is True


def test_conscience_context_manager():
    """Context manager should execute without error."""
    jiminy = create_jiminy()
    with jiminy.conscience("test-task"):
        pass  # no-op
