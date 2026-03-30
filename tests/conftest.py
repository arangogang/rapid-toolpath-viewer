"""Pytest configuration and shared fixtures for rapid_viewer tests."""

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def simple_mod() -> str:
    """Return content of simple.mod (MoveL + MoveJ basic fixture)."""
    return (FIXTURES_DIR / "simple.mod").read_text(encoding="utf-8")


@pytest.fixture
def multiline_mod() -> str:
    """Return content of multiline.mod (multiline robtarget declarations)."""
    return (FIXTURES_DIR / "multiline.mod").read_text(encoding="utf-8")


@pytest.fixture
def movec_mod() -> str:
    """Return content of movecircular.mod (MoveC with CirPoint)."""
    return (FIXTURES_DIR / "movecircular.mod").read_text(encoding="utf-8")


@pytest.fixture
def moveabsj_mod() -> str:
    """Return content of moveabsj.mod (MoveAbsJ with jointtarget)."""
    return (FIXTURES_DIR / "moveabsj.mod").read_text(encoding="utf-8")


@pytest.fixture
def offs_mod() -> str:
    """Return content of offs_inline.mod (Offs() inline expressions)."""
    return (FIXTURES_DIR / "offs_inline.mod").read_text(encoding="utf-8")


@pytest.fixture
def multiproc_mod() -> str:
    """Return content of multiproc.mod (multiple PROCs for PARS-08 testing)."""
    return (FIXTURES_DIR / "multiproc.mod").read_text(encoding="utf-8")
