"""Read-only RAPID code viewer with syntax highlighting and line highlight.

Provides a CodePanel widget that displays RAPID source code in a monospace
QPlainTextEdit with automatic syntax highlighting via RapidHighlighter.
Supports highlighting a specific line (for waypoint-code linking) and
emitting a signal when the user clicks on a line.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget

from rapid_viewer.ui.rapid_highlighter import RapidHighlighter


class CodePanel(QWidget):
    """Read-only RAPID code viewer with syntax highlighting and line highlight.

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

        # Editor setup
        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)

        # Monospace font: Consolas (Windows) with Courier New fallback
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(font)

        # Tab stop width: 4 spaces
        metrics = self._editor.fontMetrics()
        self._editor.setTabStopDistance(metrics.horizontalAdvance(" ") * 4)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)

        # Connect cursor change to line_clicked signal
        self._editor.cursorPositionChanged.connect(self._on_cursor_changed)

    def set_source(self, text: str) -> None:
        """Load RAPID source text into the editor."""
        self._editor.setPlainText(text)
        if self._highlighter is None:
            self._highlighter = RapidHighlighter(self._editor.document())

    def highlight_line(self, line_number: int) -> None:
        """Highlight and scroll to a 1-indexed line number.

        If line_number is out of range, clears any existing highlight.
        """
        block = self._editor.document().findBlockByLineNumber(line_number - 1)
        if not block.isValid() or line_number < 1:
            self._editor.setExtraSelections([])
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

    def get_cursor_line(self) -> int:
        """Return the 1-indexed line number at the current cursor position."""
        return self._editor.textCursor().blockNumber() + 1

    def _on_cursor_changed(self) -> None:
        """Emit line_clicked when the cursor position changes."""
        self.line_clicked.emit(self.get_cursor_line())
