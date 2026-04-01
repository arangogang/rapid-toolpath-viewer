"""Read-only RAPID code viewer with line numbers, no word wrap, and detail bar.

Provides a CodePanel widget that displays RAPID source code with:
  - Line numbers in a left gutter
  - No word wrap (long lines are clipped, horizontally scrollable)
  - Syntax highlighting via RapidHighlighter
  - A detail label at the bottom showing the full text of the highlighted line

Signals:
    line_clicked(int) -- emitted when user clicks a line (1-indexed)
"""

from __future__ import annotations

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from rapid_viewer.ui.rapid_highlighter import RapidHighlighter


class _LineNumberArea(QWidget):
    """Gutter widget that draws line numbers for the code editor."""

    def __init__(self, editor: "_CodeEditor") -> None:
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:
        self._editor.line_number_area_paint(event)


class _CodeEditor(QPlainTextEdit):
    """QPlainTextEdit subclass with a line number gutter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_number_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_width(0)

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_number_width(self, _count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(
                0, rect.y(), self._line_number_area.width(), rect.height()
            )
        if rect.contains(self.viewport().rect()):
            self._update_line_number_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint(self, event) -> None:
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#1e1e1e"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        painter.setPen(QColor("#858585"))
        font = self.font()
        painter.setFont(font)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

        painter.end()


class CodePanel(QWidget):
    """Read-only RAPID code viewer with line numbers and detail bar.

    Public API:
        set_source(text: str) -- load RAPID source text
        highlight_line(line_number: int) -- highlight and scroll to 1-indexed line
        get_cursor_line() -> int -- return 1-indexed line at current cursor position

    Signals:
        line_clicked(int) -- emitted when user clicks a line (1-indexed line number)
    """

    line_clicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighter: RapidHighlighter | None = None
        self._source_lines: list[str] = []

        # Editor setup — custom subclass with line numbers
        self._editor = _CodeEditor()
        self._editor.setReadOnly(True)
        self._editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Monospace font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(font)

        # Tab stop width: 4 spaces
        metrics = self._editor.fontMetrics()
        self._editor.setTabStopDistance(metrics.horizontalAdvance(" ") * 4)

        # Detail label at bottom — shows full text of currently highlighted line
        self._detail_label = QLabel()
        self._detail_label.setFont(QFont("Consolas", 9))
        self._detail_label.setStyleSheet(
            "QLabel { background: #1a1a2e; color: #e0e0e0; padding: 4px 6px; }"
        )
        self._detail_label.setWordWrap(True)
        self._detail_label.setMinimumHeight(20)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._editor, 1)
        layout.addWidget(self._detail_label, 0)

        # Connect cursor change to line_clicked signal
        self._editor.cursorPositionChanged.connect(self._on_cursor_changed)

    def set_source(self, text: str) -> None:
        """Load RAPID source text into the editor."""
        self._source_lines = text.splitlines()
        self._editor.setPlainText(text)
        if self._highlighter is None:
            self._highlighter = RapidHighlighter(self._editor.document())

    def highlight_line(self, line_number: int) -> None:
        """Highlight and scroll to a 1-indexed line number."""
        block = self._editor.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid() or line_number < 1:
            self._editor.setExtraSelections([])
            self._detail_label.setText("")
            return

        cursor = QTextCursor(block)
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#264F78"))
        selection.format.setProperty(
            QTextCharFormat.Property.FullWidthSelection, True
        )
        selection.cursor = cursor
        self._editor.setExtraSelections([selection])

        # Scroll to the line
        self._editor.setTextCursor(cursor)
        self._editor.centerCursor()

        # Update detail label with full line content
        if 0 < line_number <= len(self._source_lines):
            self._detail_label.setText(
                f"L{line_number}: {self._source_lines[line_number - 1].strip()}"
            )

    def get_cursor_line(self) -> int:
        """Return the 1-indexed line number at the current cursor position."""
        return self._editor.textCursor().blockNumber() + 1

    def _on_cursor_changed(self) -> None:
        """Emit line_clicked when the cursor position changes."""
        self.line_clicked.emit(self.get_cursor_line())
