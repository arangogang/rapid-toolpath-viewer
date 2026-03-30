"""Tests for MainWindow file loading and title bar update.

Requirements covered:
  FILE-01 -- File dialog with .mod filter (manual-only; verified at checkpoint)
  FILE-02 -- Title bar updates with filename after loading .mod file
"""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_title_update_after_load(qtbot):
    """FILE-02: Window title updates with filename after loading a .mod file."""
    from rapid_viewer.ui.main_window import APP_TITLE, MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    # Title starts with the app name only
    assert window.windowTitle() == APP_TITLE

    # Load a known-good fixture file
    fixture_path = str(FIXTURES_DIR / "simple.mod")
    window.load_file(fixture_path)

    # Title now includes the filename
    assert "simple.mod" in window.windowTitle()
    assert APP_TITLE in window.windowTitle()


def test_parse_result_stored_after_load(qtbot):
    """Verify ParseResult is stored internally after loading a .mod file."""
    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    # Before load: no result
    assert window.parse_result is None

    # After load: result populated with move instructions
    fixture_path = str(FIXTURES_DIR / "simple.mod")
    window.load_file(fixture_path)

    assert window.parse_result is not None
    assert len(window.parse_result.moves) > 0


def test_initial_window_size(qtbot):
    """Window has a reasonable minimum size for desktop use."""
    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.minimumWidth() >= 800
    assert window.minimumHeight() >= 600
