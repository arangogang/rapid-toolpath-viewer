"""Editable inspection panel for selected waypoint properties (INSP-01, MOD-01..04).

Displays: position (X/Y/Z read-only), offset inputs (dX/dY/dZ), motion (type/speed/zone),
laser state, and action buttons (Insert After, Delete).

Signals:
    offset_applied(float, float, float) -- dX, dY, dZ offset values
    speed_changed(str) -- new speed text
    zone_changed(str) -- new zone text
    laser_changed(bool) -- True=ON, False=OFF
    delete_requested(str) -- "reconnect" or "break"
    insert_requested(float, float, float) -- dX, dY, dZ for insertion

Public API:
    update_from_point(point, count) -- update display from EditPoint or clear
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator, QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class PropertyPanel(QWidget):
    """Editable inspection panel for selected waypoint properties.

    Signals:
        offset_applied(float, float, float) -- dX, dY, dZ offset values
        speed_changed(str) -- new speed text
        zone_changed(str) -- new zone text
        laser_changed(bool) -- True=ON, False=OFF
        delete_requested(str) -- "reconnect" or "break"
        insert_requested(float, float, float) -- dX, dY, dZ for insertion
    """

    offset_applied = pyqtSignal(float, float, float)
    speed_changed = pyqtSignal(str)
    zone_changed = pyqtSignal(str)
    laser_changed = pyqtSignal(bool)
    delete_requested = pyqtSignal(str)
    insert_requested = pyqtSignal(float, float, float)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(120)

        # Internal state tracking
        self._selection_count: int = 0
        self._updating: bool = False
        self._current_speed: str = ""
        self._current_zone: str = ""
        self._current_laser_on: bool = True

        # Base font for consistent sizing across the panel
        base_font = QFont()
        base_font.setPointSize(10)

        # Header: selection count
        self._header = QLabel("No selection")
        header_font = QFont()
        header_font.setPointSize(11)
        header_font.setBold(True)
        self._header.setFont(header_font)

        # Position group (read-only per D-01)
        pos_group = QGroupBox("Position")
        pos_group.setFont(base_font)
        pos_layout = QFormLayout()
        self._x_label = QLabel("--")
        self._y_label = QLabel("--")
        self._z_label = QLabel("--")
        pos_layout.addRow("X:", self._x_label)
        pos_layout.addRow("Y:", self._y_label)
        pos_layout.addRow("Z:", self._z_label)
        pos_group.setLayout(pos_layout)

        # Offset group (NEW)
        offset_group = QGroupBox("Offset")
        offset_group.setFont(base_font)
        offset_layout = QFormLayout()
        self._dx_input = QLineEdit()
        self._dy_input = QLineEdit()
        self._dz_input = QLineEdit()
        for inp in (self._dx_input, self._dy_input, self._dz_input):
            validator = QDoubleValidator()
            validator.setDecimals(3)
            inp.setValidator(validator)
            inp.setPlaceholderText("0.0")
            inp.returnPressed.connect(self._on_apply_offset)
        offset_layout.addRow("dX:", self._dx_input)
        offset_layout.addRow("dY:", self._dy_input)
        offset_layout.addRow("dZ:", self._dz_input)
        self._apply_offset_btn = QPushButton("Apply Offset")
        self._apply_offset_btn.setEnabled(False)
        self._apply_offset_btn.clicked.connect(self._on_apply_offset)
        offset_layout.addRow(self._apply_offset_btn)
        offset_group.setLayout(offset_layout)

        # Motion group
        motion_group = QGroupBox("Motion")
        motion_group.setFont(base_font)
        motion_layout = QFormLayout()
        self._type_label = QLabel("--")
        self._speed_input = QLineEdit()
        self._zone_input = QLineEdit()
        self._speed_input.editingFinished.connect(self._on_speed_finished)
        self._zone_input.editingFinished.connect(self._on_zone_finished)
        motion_layout.addRow("Type:", self._type_label)
        motion_layout.addRow("Speed:", self._speed_input)
        motion_layout.addRow("Zone:", self._zone_input)
        motion_group.setLayout(motion_layout)

        # Laser group
        laser_group = QGroupBox("Laser")
        laser_group.setFont(base_font)
        laser_layout = QFormLayout()
        self._laser_combo = QComboBox()
        self._laser_combo.addItems(["ON", "OFF"])
        self._laser_combo.currentIndexChanged.connect(self._on_laser_index_changed)
        laser_layout.addRow("State:", self._laser_combo)
        laser_group.setLayout(laser_layout)

        # Action buttons
        self._insert_btn = QPushButton("Insert After")
        self._insert_btn.setFont(base_font)
        self._insert_btn.setEnabled(False)
        self._insert_btn.clicked.connect(self._on_insert_clicked)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setFont(base_font)
        self._delete_btn.setStyleSheet(
            "QPushButton { background-color: #CC3333; color: white; padding: 4px 8px; }"
        )
        self._delete_btn.setShortcut("Del")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_clicked)

        # Scrollable content container
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.addWidget(self._header)
        content_layout.addWidget(pos_group)
        content_layout.addWidget(offset_group)
        content_layout.addWidget(motion_group)
        content_layout.addWidget(laser_group)
        content_layout.addStretch()
        content_layout.addWidget(self._insert_btn)
        content_layout.addWidget(self._delete_btn)

        # Scroll area wrapping the content
        scroll_area = QScrollArea()
        scroll_area.setWidget(content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # Main layout just holds the scroll area
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        # Initial disabled state for inputs
        self._set_inputs_enabled(False)

    def update_from_point(self, point: object | None, count: int = 0) -> None:
        """Update display from an EditPoint (or None to clear).

        Args:
            point: EditPoint instance or None. When None, all fields reset.
            count: Number of selected points for header display.
        """
        self._updating = True
        try:
            self._selection_count = count

            if point is None or count == 0:
                self._header.setText("No selection")
                for lbl in (self._x_label, self._y_label, self._z_label, self._type_label):
                    lbl.setText("--")
                self._speed_input.setText("")
                self._zone_input.setText("")
                self._laser_combo.setCurrentIndex(0)
                self._current_speed = ""
                self._current_zone = ""
                self._current_laser_on = True
                self._set_inputs_enabled(False)
                self._apply_offset_btn.setEnabled(False)
                self._delete_btn.setEnabled(False)
                self._insert_btn.setEnabled(False)
                return

            # Header
            if count == 1:
                self._header.setText("1 point selected")
            else:
                self._header.setText(f"{count} points selected")

            # Position (read-only)
            self._x_label.setText(f"{point.pos[0]:.3f}")
            self._y_label.setText(f"{point.pos[1]:.3f}")
            self._z_label.setText(f"{point.pos[2]:.3f}")

            # Motion
            self._type_label.setText(point.original.move_type.name)
            self._current_speed = point.speed
            self._current_zone = point.zone
            self._speed_input.setText(point.speed)
            self._zone_input.setText(point.zone)

            # Laser
            self._current_laser_on = point.laser_on
            self._laser_combo.setCurrentIndex(0 if point.laser_on else 1)

            # Enable controls
            self._set_inputs_enabled(True)
            self._apply_offset_btn.setEnabled(True)
            self._delete_btn.setEnabled(True)
            self._insert_btn.setEnabled(count == 1)
        finally:
            self._updating = False

    # -- Private slots --

    def _on_apply_offset(self) -> None:
        """Read offset fields, emit offset_applied signal, and clear inputs."""
        if self._selection_count == 0:
            return
        dx = self._parse_float(self._dx_input.text())
        dy = self._parse_float(self._dy_input.text())
        dz = self._parse_float(self._dz_input.text())
        if dx == 0.0 and dy == 0.0 and dz == 0.0:
            return
        self.offset_applied.emit(dx, dy, dz)
        # Clear inputs after applying to prevent accidental re-application
        self._dx_input.clear()
        self._dy_input.clear()
        self._dz_input.clear()

    def _on_speed_finished(self) -> None:
        """Emit speed_changed only if value actually differs."""
        if self._updating:
            return
        new_val = self._speed_input.text()
        if new_val != self._current_speed:
            self._current_speed = new_val
            self.speed_changed.emit(new_val)

    def _on_zone_finished(self) -> None:
        """Emit zone_changed only if value actually differs."""
        if self._updating:
            return
        new_val = self._zone_input.text()
        if new_val != self._current_zone:
            self._current_zone = new_val
            self.zone_changed.emit(new_val)

    def _on_laser_index_changed(self, index: int) -> None:
        """Emit laser_changed only if value actually differs."""
        if self._updating:
            return
        new_on = index == 0
        if new_on != self._current_laser_on:
            self._current_laser_on = new_on
            self.laser_changed.emit(new_on)

    def _on_delete_clicked(self) -> None:
        """Show confirmation dialog and emit delete_requested if confirmed."""
        result = self._show_delete_dialog(self._selection_count)
        if result is not None:
            self.delete_requested.emit(result)

    def _on_insert_clicked(self) -> None:
        """Read offset fields and emit insert_requested signal."""
        dx = self._parse_float(self._dx_input.text())
        dy = self._parse_float(self._dy_input.text())
        dz = self._parse_float(self._dz_input.text())
        self.insert_requested.emit(dx, dy, dz)

    def _show_delete_dialog(self, count: int) -> str | None:
        """Show delete confirmation dialog. Returns 'reconnect', 'break', or None."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Delete Point(s)")
        dlg.setText(f"Delete {count} point(s)?")
        dlg.setIcon(QMessageBox.Icon.Warning)
        reconnect_btn = dlg.addButton("Reconnect", QMessageBox.ButtonRole.AcceptRole)
        break_btn = dlg.addButton("Break", QMessageBox.ButtonRole.DestructiveRole)
        cancel_btn = dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        dlg.setDefaultButton(cancel_btn)
        dlg.setEscapeButton(cancel_btn)
        dlg.exec()
        clicked = dlg.clickedButton()
        if clicked is reconnect_btn:
            return "reconnect"
        elif clicked is break_btn:
            return "break"
        return None

    # -- Helpers --

    def _set_inputs_enabled(self, enabled: bool) -> None:
        """Enable or disable all editable input widgets."""
        for w in (
            self._dx_input,
            self._dy_input,
            self._dz_input,
            self._speed_input,
            self._zone_input,
            self._laser_combo,
        ):
            w.setEnabled(enabled)

    @staticmethod
    def _parse_float(text: str) -> float:
        """Parse float from text, defaulting to 0.0 on empty/invalid."""
        if not text.strip():
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0
