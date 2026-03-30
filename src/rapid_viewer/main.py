"""Application entry point for ABB RAPID Toolpath Viewer.

Usage:
    python -m rapid_viewer.main [file.mod]
    python -m rapid_viewer      (if __main__.py is added later)

If a .mod file path is passed as a command-line argument, it is loaded
automatically after the window is shown.
"""

import sys

from PyQt6.QtWidgets import QApplication

from rapid_viewer.ui.main_window import MainWindow


def main() -> None:
    """Create the QApplication, show the main window, and start the event loop."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    # If a file path was passed as command-line argument, load it immediately
    if len(sys.argv) > 1:
        window.load_file(sys.argv[1])

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
