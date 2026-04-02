"""Tests for MainWindow file loading, layout, signal wiring, and Save As export.

Requirements covered:
  FILE-01 -- File dialog with .mod filter (manual-only; verified at checkpoint)
  FILE-02 -- Title bar updates with filename after loading .mod file
  LINK-01 -- Bidirectional 3D-to-code linking (layout/wiring)
  LINK-02 -- Code-to-3D linking (layout/wiring)
  PARS-08 -- PROC selector filtering
  EXP-01  -- Save As export with overwrite protection
"""

from pathlib import Path
from unittest.mock import patch

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

    assert window.minimumWidth() >= 1024
    assert window.minimumHeight() >= 700


def test_splitter_layout(qtbot):
    """Central widget is a QSplitter with GL widget and code panel."""
    from PyQt6.QtWidgets import QSplitter

    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    central = window.centralWidget()
    assert isinstance(central, QSplitter)
    assert central.count() == 2


def test_load_file_populates_code_panel(qtbot):
    """After load_file, code panel editor has non-empty text."""
    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    fixture_path = str(FIXTURES_DIR / "simple.mod")
    window.load_file(fixture_path)

    text = window._code_panel._editor.toPlainText()
    assert len(text) > 0
    assert "MODULE" in text


def test_load_file_populates_proc_combo(qtbot):
    """After loading multiproc.mod, PROC combo has All PROCs + procedure names."""
    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    fixture_path = str(FIXTURES_DIR / "multiproc.mod")
    window.load_file(fixture_path)

    combo = window._proc_combo
    items = [combo.itemText(i) for i in range(combo.count())]
    assert items[0] == "All PROCs"
    assert "main" in items
    assert "path2" in items


def test_save_as_prevents_overwrite(qtbot):
    """EXP-01: Save As prevents overwriting the original file."""
    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    fixture_path = str(FIXTURES_DIR / "simple.mod")
    window.load_file(fixture_path)

    # Mock dialog to return the same path as the loaded file
    original_path = str(window._current_file_path)
    with (
        patch(
            "rapid_viewer.ui.main_window.QFileDialog.getSaveFileName",
            return_value=(original_path, ""),
        ),
        patch(
            "rapid_viewer.ui.main_window.QMessageBox.warning",
        ) as mock_warning,
    ):
        window._save_as()
        mock_warning.assert_called_once()
        assert "Cannot overwrite" in mock_warning.call_args[0][2]


def test_save_as_exports_file(qtbot, tmp_path):
    """EXP-01: Save As exports a .mod file to the chosen path."""
    from rapid_viewer.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    fixture_path = str(FIXTURES_DIR / "simple.mod")
    window.load_file(fixture_path)

    save_path = str(tmp_path / "exported.mod")
    with patch(
        "rapid_viewer.ui.main_window.QFileDialog.getSaveFileName",
        return_value=(save_path, ""),
    ):
        window._save_as()

    saved = Path(save_path)
    assert saved.exists()
    content = saved.read_text(encoding="utf-8")
    # Should contain the MODULE declaration from the original
    assert "MODULE" in content
