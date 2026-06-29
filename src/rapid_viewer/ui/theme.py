"""SURPHASE dark theme — application-wide palette and Qt stylesheet.

Provides a unified dark "engineering tool" look (matching the 3D viewport and
code panel) with a deep-blue brand accent. Apply once at startup via
``apply_theme(app)`` before the main window is shown.

Public API:
    apply_theme(app)        -- set Fusion style + dark palette + global stylesheet
    ACCENT, WINDOW_BG, ...  -- brand color constants (hex strings)
    GL_CLEAR_COLOR          -- (r, g, b, a) floats for glClearColor, theme-matched
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QPalette

# ---------------------------------------------------------------------------
# Brand palette (SURPHASE — deep blue accent on dark slate)
# ---------------------------------------------------------------------------

ACCENT = "#2563eb"          # deep blue — primary brand accent
ACCENT_HOVER = "#3b82f6"
ACCENT_PRESSED = "#1d4ed8"

WINDOW_BG = "#1b1b2b"       # main window / chrome background
PANEL_BG = "#232336"        # panels, group boxes, toolbars
BASE_BG = "#15151f"         # text editors, input fields (darkest)
ELEVATED_BG = "#2b2b40"     # hovered/elevated surfaces
BORDER = "#34344a"          # subtle separators
BORDER_STRONG = "#45456a"

TEXT = "#e4e4ef"            # primary text
TEXT_DIM = "#9a9ab2"        # secondary / disabled-ish labels
TEXT_DISABLED = "#5a5a72"

DANGER = "#e0483e"          # destructive (delete)
DANGER_HOVER = "#f05a50"

# Viewport clear color, matched to WINDOW_BG (0x1b/0x1b/0x2b)
GL_CLEAR_COLOR = (0x1b / 255.0, 0x1b / 255.0, 0x2b / 255.0, 1.0)


def _palette() -> QPalette:
    """Build a dark QPalette so even unstyled widgets read sensible colors."""
    pal = QPalette()
    window = QColor(WINDOW_BG)
    base = QColor(BASE_BG)
    panel = QColor(PANEL_BG)
    text = QColor(TEXT)
    accent = QColor(ACCENT)

    pal.setColor(QPalette.ColorRole.Window, window)
    pal.setColor(QPalette.ColorRole.WindowText, text)
    pal.setColor(QPalette.ColorRole.Base, base)
    pal.setColor(QPalette.ColorRole.AlternateBase, panel)
    pal.setColor(QPalette.ColorRole.Text, text)
    pal.setColor(QPalette.ColorRole.Button, panel)
    pal.setColor(QPalette.ColorRole.ButtonText, text)
    pal.setColor(QPalette.ColorRole.ToolTipBase, panel)
    pal.setColor(QPalette.ColorRole.ToolTipText, text)
    pal.setColor(QPalette.ColorRole.Highlight, accent)
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    pal.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_DIM))
    pal.setColor(QPalette.ColorRole.Link, accent)

    disabled = QColor(TEXT_DISABLED)
    for grp in (QPalette.ColorGroup.Disabled,):
        pal.setColor(grp, QPalette.ColorRole.Text, disabled)
        pal.setColor(grp, QPalette.ColorRole.WindowText, disabled)
        pal.setColor(grp, QPalette.ColorRole.ButtonText, disabled)
    return pal


# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Malgun Gothic", sans-serif;
    font-size: 10pt;
    outline: 0;
}}

QMainWindow, QDialog {{
    background-color: {WINDOW_BG};
}}

QWidget {{
    background-color: {WINDOW_BG};
    color: {TEXT};
}}

/* --- Menu bar --- */
QMenuBar {{
    background-color: {WINDOW_BG};
    color: {TEXT};
    border-bottom: 1px solid {BORDER};
    padding: 2px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 12px;
    border-radius: 4px;
}}
QMenuBar::item:selected {{ background-color: {ELEVATED_BG}; }}
QMenuBar::item:pressed {{ background-color: {ACCENT}; color: #ffffff; }}

QMenu {{
    background-color: {PANEL_BG};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 26px 6px 22px;
    border-radius: 4px;
}}
QMenu::item:selected {{ background-color: {ACCENT}; color: #ffffff; }}
QMenu::item:disabled {{ color: {TEXT_DISABLED}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* --- Tool bar --- */
QToolBar {{
    background-color: {PANEL_BG};
    border: 0px;
    border-top: 1px solid {BORDER};
    padding: 4px 6px;
    spacing: 4px;
}}
QToolBar::separator {{
    width: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}
QToolButton {{
    background: transparent;
    color: {TEXT};
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 5px 8px;
}}
QToolButton:hover {{ background-color: {ELEVATED_BG}; border-color: {BORDER}; }}
QToolButton:pressed, QToolButton:checked {{ background-color: {ACCENT}; color: #ffffff; }}
QToolButton:disabled {{ color: {TEXT_DISABLED}; }}

/* --- Buttons --- */
QPushButton {{
    background-color: {ELEVATED_BG};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 5px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background-color: {BORDER_STRONG}; }}
QPushButton:pressed {{ background-color: {ACCENT}; color: #ffffff; }}
QPushButton:default {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {TEXT_DISABLED}; background-color: {PANEL_BG}; border-color: {BORDER}; }}

/* --- Inputs --- */
QLineEdit, QPlainTextEdit, QTextEdit, QAbstractSpinBox {{
    background-color: {BASE_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 6px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
}}
QLineEdit:focus, QAbstractSpinBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QAbstractSpinBox:disabled {{ color: {TEXT_DISABLED}; background-color: {PANEL_BG}; }}

QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    background: {ELEVATED_BG};
    border: 0px;
    width: 16px;
}}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {ACCENT}; }}
QAbstractSpinBox::up-arrow {{ image: none; width: 7px; height: 7px;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-bottom: 5px solid {TEXT}; }}
QAbstractSpinBox::down-arrow {{ image: none; width: 7px; height: 7px;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {TEXT}; }}

/* --- Combo box --- */
QComboBox {{
    background-color: {BASE_BG};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 4px 8px;
    min-height: 20px;
}}
QComboBox:hover {{ border-color: {BORDER_STRONG}; }}
QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: 0px; width: 20px; }}
QComboBox::down-arrow {{ image: none; width: 8px; height: 8px;
    border-left: 5px solid transparent; border-right: 5px solid transparent;
    border-top: 6px solid {TEXT}; margin-right: 6px; }}
QComboBox QAbstractItemView {{
    background-color: {PANEL_BG};
    color: {TEXT};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    selection-background-color: {ACCENT};
    selection-color: #ffffff;
    padding: 2px;
}}

/* --- Group box --- */
QGroupBox {{
    background-color: {PANEL_BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 14px;
    padding: 10px 10px 8px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 1px 6px;
    color: {ACCENT_HOVER};
    background-color: {PANEL_BG};
}}

/* --- Labels --- */
QLabel {{ background: transparent; color: {TEXT}; }}

/* --- Sliders --- */
QSlider::groove:horizontal {{
    height: 5px;
    background: {BORDER};
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {TEXT};
    border: 0px;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOVER}; }}

/* --- Scroll bars --- */
QScrollBar:vertical {{ background: {WINDOW_BG}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER_STRONG}; min-height: 28px; border-radius: 6px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar:horizontal {{ background: {WINDOW_BG}; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDER_STRONG}; min-width: 28px; border-radius: 6px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --- Splitter --- */
QSplitter::handle {{ background: {BORDER}; }}
QSplitter::handle:horizontal {{ width: 2px; }}
QSplitter::handle:vertical {{ height: 2px; }}
QSplitter::handle:hover {{ background: {ACCENT}; }}

/* --- Status bar --- */
QStatusBar {{
    background-color: {PANEL_BG};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
}}
QStatusBar::item {{ border: 0px; }}

/* --- Scroll area / abstract views --- */
QScrollArea {{ border: 0px; background: transparent; }}
QAbstractScrollArea {{ background: {BASE_BG}; }}

/* --- Tooltip --- */
QToolTip {{
    background-color: {PANEL_BG};
    color: {TEXT};
    border: 1px solid {ACCENT};
    border-radius: 4px;
    padding: 4px 6px;
}}
"""


def apply_theme(app) -> None:
    """Apply the SURPHASE dark theme to a QApplication.

    Sets the Fusion base style (predictable across platforms), a dark
    palette, and the global stylesheet. Call before showing any window.
    """
    app.setStyle("Fusion")
    app.setPalette(_palette())
    app.setStyleSheet(STYLESHEET)
