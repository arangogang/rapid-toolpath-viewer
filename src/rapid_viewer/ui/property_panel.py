"""Read-only inspection panel for selected waypoint properties (INSP-01).

Displays: position (X/Y/Z), motion (type/speed/zone), laser state.
Updated via update_from_point() called by MainWindow when selection changes.

Public API:
    update_from_point(point, count) -- update display from EditPoint or clear
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PropertyPanel(QWidget):
    """Read-only inspection panel for selected waypoint properties (INSP-01).

    Displays: position (X/Y/Z), motion (type/speed/zone), laser state.
    Updated via update_from_point() called by MainWindow when selection changes.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(120)

        # Header: selection count
        self._header = QLabel("No selection")
        header_font = QFont()
        header_font.setPointSize(9)
        header_font.setBold(True)
        self._header.setFont(header_font)

        # Position group
        pos_group = QGroupBox("Position")
        pos_layout = QFormLayout()
        self._x_label = QLabel("--")
        self._y_label = QLabel("--")
        self._z_label = QLabel("--")
        pos_layout.addRow("X:", self._x_label)
        pos_layout.addRow("Y:", self._y_label)
        pos_layout.addRow("Z:", self._z_label)
        pos_group.setLayout(pos_layout)

        # Motion group
        motion_group = QGroupBox("Motion")
        motion_layout = QFormLayout()
        self._type_label = QLabel("--")
        self._speed_label = QLabel("--")
        self._zone_label = QLabel("--")
        motion_layout.addRow("Type:", self._type_label)
        motion_layout.addRow("Speed:", self._speed_label)
        motion_layout.addRow("Zone:", self._zone_label)
        motion_group.setLayout(motion_layout)

        # Laser group
        laser_group = QGroupBox("Laser")
        laser_layout = QFormLayout()
        self._laser_label = QLabel("--")
        laser_layout.addRow("State:", self._laser_label)
        laser_group.setLayout(laser_layout)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(self._header)
        layout.addWidget(pos_group)
        layout.addWidget(motion_group)
        layout.addWidget(laser_group)
        layout.addStretch()

    def update_from_point(self, point: object | None, count: int = 0) -> None:
        """Update display from an EditPoint (or None to clear).

        Args:
            point: EditPoint instance or None. When None, all fields reset to "--".
            count: Number of selected points for header display.
        """
        if point is None or count == 0:
            self._header.setText("No selection")
            for lbl in (
                self._x_label,
                self._y_label,
                self._z_label,
                self._type_label,
                self._speed_label,
                self._zone_label,
                self._laser_label,
            ):
                lbl.setText("--")
            return

        # Header: "1 point selected" or "N points selected"
        if count == 1:
            self._header.setText("1 point selected")
        else:
            self._header.setText(f"{count} points selected")

        # Position: 3 decimal places
        self._x_label.setText(f"{point.pos[0]:.3f}")
        self._y_label.setText(f"{point.pos[1]:.3f}")
        self._z_label.setText(f"{point.pos[2]:.3f}")

        # Motion
        self._type_label.setText(point.original.move_type.name)
        self._speed_label.setText(point.speed)
        self._zone_label.setText(point.zone)

        # Laser
        self._laser_label.setText("ON" if point.laser_on else "OFF")
