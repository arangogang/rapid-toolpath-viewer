"""QSyntaxHighlighter subclass for ABB RAPID language keywords.

Highlights:
- Move keywords (MoveL, MoveJ, MoveC, MoveAbsJ) in teal with bold
- PROC keywords (PROC, ENDPROC, MODULE, ENDMODULE) in purple with bold
- Data type keywords (CONST, PERS, VAR, LOCAL, robtarget, etc.) in blue
- Comments (! to end of line) in green
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


class RapidHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for RAPID .mod source code."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._highlight_block_num: int = -1  # 0-indexed

        # Highlight format: bright orange + extra bold (applied OVER syntax colors)
        self._highlight_fmt = QTextCharFormat()
        self._highlight_fmt.setForeground(QColor("#FF8C00"))
        self._highlight_fmt.setFontWeight(QFont.Weight.ExtraBold)

        ci = QRegularExpression.PatternOption.CaseInsensitiveOption

        # Move keywords: teal, bold
        move_fmt = QTextCharFormat()
        move_fmt.setForeground(QColor("#4EC9B0"))
        move_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in ("MoveL", "MoveJ", "MoveC", "MoveAbsJ"):
            pattern = QRegularExpression(rf"\b{kw}\b", ci)
            self._rules.append((pattern, move_fmt))

        # PROC keywords: purple, bold
        proc_fmt = QTextCharFormat()
        proc_fmt.setForeground(QColor("#C586C0"))
        proc_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in ("PROC", "ENDPROC", "MODULE", "ENDMODULE"):
            pattern = QRegularExpression(rf"\b{kw}\b", ci)
            self._rules.append((pattern, proc_fmt))

        # Data type keywords: blue
        type_fmt = QTextCharFormat()
        type_fmt.setForeground(QColor("#569CD6"))
        for kw in ("CONST", "PERS", "VAR", "LOCAL", "robtarget",
                    "jointtarget", "speeddata", "zonedata"):
            pattern = QRegularExpression(rf"\b{kw}\b", ci)
            self._rules.append((pattern, type_fmt))

        # Comments: ! to end of line, green
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6A9955"))
        self._rules.append((QRegularExpression(r"!.*$"), comment_fmt))

    def set_highlight_line(self, line_number: int) -> None:
        """Set the 1-indexed line that should get amber+bold formatting.

        Pass -1 or 0 to clear. Rehighlights only the affected blocks.
        """
        old = self._highlight_block_num
        self._highlight_block_num = line_number - 1  # convert to 0-indexed
        doc = self.document()
        if doc is None:
            return
        # Rehighlight old and new blocks so formatting updates immediately
        if old >= 0:
            block = doc.findBlockByNumber(old)
            if block.isValid():
                self.rehighlightBlock(block)
        if self._highlight_block_num >= 0:
            block = doc.findBlockByNumber(self._highlight_block_num)
            if block.isValid():
                self.rehighlightBlock(block)

    def highlightBlock(self, text: str) -> None:
        """Apply highlighting rules to a single block of text."""
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

        # Override with amber+bold on the highlighted line (after syntax rules
        # so it takes precedence over keyword colors)
        if self.currentBlock().blockNumber() == self._highlight_block_num:
            self.setFormat(0, len(text), self._highlight_fmt)
