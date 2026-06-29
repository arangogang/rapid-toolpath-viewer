"""Application identity and resource lookup.

Centralizes the product name, organization (for QSettings), and the on-disk
location of the window icon so both the source run and the PyInstaller bundle
resolve them the same way.
"""

from __future__ import annotations

import sys
from pathlib import Path

APP_NAME = "SURPHASE Rapid Viewer"
ORG_NAME = "SURPHASE"
APP_TITLE = APP_NAME  # window-title base; file name is prepended when a file is open

_ICON_FILENAME = "rapid_viewer.ico"


def find_icon() -> str | None:
    """Return an absolute path to the app icon, or None if not found.

    Resolution order:
      1. PyInstaller bundle dir (``sys._MEIPASS``) when frozen.
      2. The directory next to the executable (``dist/``).
      3. The repository root, four levels up from this file
         (``src/rapid_viewer/app_meta.py`` -> repo root).
    """
    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / _ICON_FILENAME)
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).parent / _ICON_FILENAME)

    candidates.append(Path(__file__).resolve().parents[2] / _ICON_FILENAME)

    for path in candidates:
        if path.is_file():
            return str(path)
    return None
