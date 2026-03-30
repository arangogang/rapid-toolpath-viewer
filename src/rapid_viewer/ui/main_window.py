"""Main application window for ABB RAPID Toolpath Viewer.

Provides the QMainWindow with:
  - File > Open menu action (Ctrl+O) to load .mod files via native dialog
  - File > Exit menu action (Ctrl+Q) to close the application
  - Title bar update with filename after a successful load
  - Internal storage of ParseResult for downstream phase consumption
"""

from pathlib import Path

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

APP_TITLE = "ABB RAPID Toolpath Viewer"


class MainWindow(QMainWindow):
    """Main window of the ABB RAPID Toolpath Viewer application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(800, 600)
        self._parse_result = None
        self._setup_menu()

    def _setup_menu(self) -> None:
        """Build the menu bar with File menu entries."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _open_file(self) -> None:
        """Open a native file dialog and load the selected .mod file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open RAPID Module",
            "",
            "RAPID Module (*.mod);;All Files (*)",
        )
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str) -> None:
        """Load and parse a .mod file. Public method also used by tests.

        Reads the file with UTF-8 / latin-1 encoding fallback (read_mod_file
        handles Windows-1252 encoded files from RobotStudio), parses the content,
        stores the ParseResult internally, and updates the title bar with the
        filename.

        Args:
            file_path: Absolute or relative path to the .mod file.
        """
        path = Path(file_path)
        try:
            from rapid_viewer.parser.rapid_parser import parse_module, read_mod_file

            source = read_mod_file(path)
            self._parse_result = parse_module(source)
            self.setWindowTitle(f"{APP_TITLE} - {path.name}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")

    @property
    def parse_result(self):
        """The ParseResult from the most recently loaded file, or None."""
        return self._parse_result
