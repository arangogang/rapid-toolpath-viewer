"""Tests for CodePanel widget.

Verifies source loading, line highlighting, scroll behavior,
read-only mode, and cursor line detection.
"""

import pytest
from PyQt6.QtGui import QTextCursor

from rapid_viewer.ui.code_panel import CodePanel


SAMPLE_SOURCE = "line1\nline2\nline3\nline4\nline5"

LONG_SOURCE = "\n".join(f"line{i}" for i in range(1, 201))


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------


def test_set_source(qtbot):
    """set_source loads text into the editor with all lines present."""
    panel = CodePanel()
    qtbot.addWidget(panel)
    panel.set_source("line1\nline2\nline3")
    text = panel._editor.toPlainText()
    assert text == "line1\nline2\nline3"
    assert panel._editor.document().blockCount() == 3


# ---------------------------------------------------------------------------
# Line highlighting
# ---------------------------------------------------------------------------


def test_highlight_line_valid(qtbot):
    """highlight_line(2) creates an ExtraSelection on line 2."""
    panel = CodePanel()
    qtbot.addWidget(panel)
    panel.set_source(SAMPLE_SOURCE)
    panel.highlight_line(2)
    selections = panel._editor.extraSelections()
    assert len(selections) == 1
    # The cursor in the selection should be on block index 1 (0-indexed)
    assert selections[0].cursor.blockNumber() == 1


def test_highlight_line_scrolls(qtbot):
    """highlight_line(N) for a long document scrolls cursor to that line."""
    panel = CodePanel()
    qtbot.addWidget(panel)
    panel.set_source(LONG_SOURCE)
    panel.highlight_line(150)
    # The editor's text cursor should be on block 149 (0-indexed)
    assert panel._editor.textCursor().blockNumber() == 149


def test_highlight_line_invalid(qtbot):
    """highlight_line with out-of-range values does not crash."""
    panel = CodePanel()
    qtbot.addWidget(panel)
    panel.set_source(SAMPLE_SOURCE)
    # Should not raise
    panel.highlight_line(0)
    panel.highlight_line(999)
    # extraSelections should be cleared or empty after invalid line
    selections = panel._editor.extraSelections()
    assert len(selections) == 0


# ---------------------------------------------------------------------------
# Read-only
# ---------------------------------------------------------------------------


def test_editor_is_readonly(qtbot):
    """After set_source, the editor is read-only."""
    panel = CodePanel()
    qtbot.addWidget(panel)
    panel.set_source(SAMPLE_SOURCE)
    assert panel._editor.isReadOnly() is True


# ---------------------------------------------------------------------------
# Cursor line detection
# ---------------------------------------------------------------------------


def test_get_cursor_line(qtbot):
    """get_cursor_line returns 1-indexed line number at cursor position."""
    panel = CodePanel()
    qtbot.addWidget(panel)
    panel.set_source(SAMPLE_SOURCE)
    # Programmatically move cursor to line 3 (block index 2)
    block = panel._editor.document().findBlockByLineNumber(2)
    cursor = QTextCursor(block)
    panel._editor.setTextCursor(cursor)
    assert panel.get_cursor_line() == 3
