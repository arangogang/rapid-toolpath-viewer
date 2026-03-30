"""Tests for RAPID syntax highlighter.

Verifies keyword format categories: move keywords (teal, bold),
PROC keywords (purple, bold), data types (blue), comments (green).
"""

import pytest
from PyQt6.QtGui import QColor, QFont, QTextCharFormat
from PyQt6.QtWidgets import QPlainTextEdit

from rapid_viewer.ui.rapid_highlighter import RapidHighlighter


class TrackingHighlighter(RapidHighlighter):
    """Subclass that records setFormat calls for test assertions."""

    def __init__(self, doc):
        self.recorded: list[tuple[int, int, QTextCharFormat]] = []
        super().__init__(doc)

    def highlightBlock(self, text: str) -> None:
        self.recorded.clear()
        super().highlightBlock(text)

    def setFormat(self, start: int, count: int, fmt: QTextCharFormat) -> None:
        self.recorded.append((start, count, QTextCharFormat(fmt)))
        super().setFormat(start, count, fmt)


def _make_highlighter(qtbot, text: str) -> TrackingHighlighter:
    """Helper: create editor, attach tracking highlighter, set text."""
    editor = QPlainTextEdit()
    qtbot.addWidget(editor)
    highlighter = TrackingHighlighter(editor.document())
    editor.setPlainText(text)
    return highlighter


# ---------------------------------------------------------------------------
# Move keywords: teal (#4EC9B0), bold
# ---------------------------------------------------------------------------


def test_move_keywords_formatted(qtbot):
    """MoveL in a move instruction gets teal color and bold weight."""
    h = _make_highlighter(qtbot, "MoveL p10, v100, fine, tool0;")
    move_fmts = [(s, c, f) for s, c, f in h.recorded if f.foreground().color().name() == "#4ec9b0"]
    assert len(move_fmts) >= 1
    start, count, fmt = move_fmts[0]
    assert start == 0
    assert count == 5  # "MoveL"
    assert fmt.fontWeight() == QFont.Weight.Bold


# ---------------------------------------------------------------------------
# PROC keywords: purple (#C586C0), bold
# ---------------------------------------------------------------------------


def test_proc_keywords_formatted(qtbot):
    """PROC in a procedure declaration gets purple color and bold."""
    h = _make_highlighter(qtbot, "PROC main()")
    proc_fmts = [(s, c, f) for s, c, f in h.recorded if f.foreground().color().name() == "#c586c0"]
    assert len(proc_fmts) >= 1
    start, count, fmt = proc_fmts[0]
    assert start == 0
    assert count == 4  # "PROC"
    assert fmt.fontWeight() == QFont.Weight.Bold


# ---------------------------------------------------------------------------
# Data type keywords: blue (#569CD6)
# ---------------------------------------------------------------------------


def test_data_type_keywords_formatted(qtbot):
    """CONST and robtarget get blue color."""
    h = _make_highlighter(qtbot, "CONST robtarget p10 := [[0,0,0],[1,0,0,0],[0,0,0,0],[0,0,0,0,0,0]];")
    blue_fmts = [(s, c, f) for s, c, f in h.recorded if f.foreground().color().name() == "#569cd6"]
    # Should have at least CONST and robtarget
    assert len(blue_fmts) >= 2
    # CONST starts at 0
    const_match = [x for x in blue_fmts if x[0] == 0]
    assert len(const_match) == 1
    assert const_match[0][1] == 5  # "CONST"


# ---------------------------------------------------------------------------
# Comments: green (#6A9955)
# ---------------------------------------------------------------------------


def test_comment_formatted(qtbot):
    """! comment line gets green color for the entire line."""
    h = _make_highlighter(qtbot, "! this is a comment")
    green_fmts = [(s, c, f) for s, c, f in h.recorded if f.foreground().color().name() == "#6a9955"]
    assert len(green_fmts) >= 1
    start, count, fmt = green_fmts[0]
    assert start == 0
    assert count == 19  # entire line


# ---------------------------------------------------------------------------
# Case insensitivity
# ---------------------------------------------------------------------------


def test_case_insensitive(qtbot):
    """Both 'movel' and 'MOVEL' get highlighted as move keywords."""
    h_lower = _make_highlighter(qtbot, "movel p10, v100, fine, tool0;")
    h_upper = _make_highlighter(qtbot, "MOVEL p10, v100, fine, tool0;")
    lower_fmts = [(s, c, f) for s, c, f in h_lower.recorded if f.foreground().color().name() == "#4ec9b0"]
    upper_fmts = [(s, c, f) for s, c, f in h_upper.recorded if f.foreground().color().name() == "#4ec9b0"]
    assert len(lower_fmts) >= 1
    assert len(upper_fmts) >= 1
    assert lower_fmts[0][1] == 5  # "movel" length
    assert upper_fmts[0][1] == 5  # "MOVEL" length


# ---------------------------------------------------------------------------
# No false positives
# ---------------------------------------------------------------------------


def test_no_false_positive(qtbot):
    """'MoveLeft' should NOT be highlighted as a move keyword (word boundary)."""
    h = _make_highlighter(qtbot, "MoveLeft something;")
    teal_fmts = [(s, c, f) for s, c, f in h.recorded if f.foreground().color().name() == "#4ec9b0"]
    assert len(teal_fmts) == 0
