"""Tests for PropertyPanel widget (INSP-01, MOD-01..04).

Verifies: selection header, position formatting (3 decimals),
motion fields, laser ON/OFF display, clear-to-default behavior,
editable inputs, signal emissions, guard flag, and button states.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import patch

import numpy as np
import pytest

from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import QComboBox, QLineEdit

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget


# Minimal EditPoint mock -- mirrors interface contract from edit_model.py.
@dataclass
class _EditPoint:
    original: MoveInstruction
    pos: np.ndarray  # shape (3,)
    speed: str
    zone: str
    laser_on: bool
    deleted: bool = False


def _make_edit_point(
    *,
    x: float = 1234.567,
    y: float = -890.123,
    z: float = 456.789,
    speed: str = "v1000",
    zone: str = "z10",
    laser_on: bool = True,
    move_type: MoveType = MoveType.MOVEL,
) -> _EditPoint:
    """Create a test EditPoint with sensible defaults."""
    target = RobTarget(
        name="p1",
        pos=np.array([x, y, z]),
        orient=np.array([1.0, 0.0, 0.0, 0.0]),
        confdata=(0, 0, 0, 0),
        extjoint=(9e9,) * 6,
        source_line=10,
    )
    move = MoveInstruction(
        move_type=move_type,
        target=target,
        circle_point=None,
        joint_target=None,
        speed=speed,
        zone=zone,
        tool="tool0",
        wobj="wobj0",
        source_line=10,
        has_cartesian=True,
        laser_on=laser_on,
    )
    return _EditPoint(
        original=move,
        pos=np.array([x, y, z]),
        speed=speed,
        zone=zone,
        laser_on=laser_on,
    )


from rapid_viewer.ui.property_panel import PropertyPanel


class TestPropertyPanelInit:
    """PropertyPanel initializes with empty/default state."""

    def test_header_shows_no_selection(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert panel._header.text() == "No selection"

    def test_all_fields_show_dashes(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        for lbl in [
            panel._x_label,
            panel._y_label,
            panel._z_label,
            panel._type_label,
        ]:
            assert lbl.text() == "--"

    def test_speed_zone_initially_empty(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert panel._speed_input.text() == ""
        assert panel._zone_input.text() == ""

    def test_laser_combo_initially_on(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert panel._laser_combo.currentText() == "ON"


class TestPropertyPanelUpdateSingle:
    """update_from_point with a single point selected."""

    def test_header_single_selection(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=1)
        assert panel._header.text() == "1 point selected"

    def test_position_3_decimal_places(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(x=1234.567, y=-890.123, z=456.789)
        panel.update_from_point(pt, count=1)
        assert panel._x_label.text() == "1234.567"
        assert panel._y_label.text() == "-890.123"
        assert panel._z_label.text() == "456.789"

    def test_motion_fields(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(speed="v500", zone="z50", move_type=MoveType.MOVEJ)
        panel.update_from_point(pt, count=1)
        assert panel._type_label.text() == "MOVEJ"
        assert panel._speed_input.text() == "v500"
        assert panel._zone_input.text() == "z50"

    def test_laser_on(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(laser_on=True)
        panel.update_from_point(pt, count=1)
        assert panel._laser_combo.currentText() == "ON"

    def test_laser_off(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(laser_on=False)
        panel.update_from_point(pt, count=1)
        assert panel._laser_combo.currentText() == "OFF"


class TestPropertyPanelUpdateMulti:
    """update_from_point with multiple points selected."""

    def test_header_multi_selection(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=3)
        assert panel._header.text() == "3 points selected"


class TestPropertyPanelClear:
    """update_from_point(None, 0) resets to default state."""

    def test_clear_resets_header(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=1)
        panel.update_from_point(None, count=0)
        assert panel._header.text() == "No selection"

    def test_clear_resets_all_fields(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=1)
        panel.update_from_point(None, count=0)
        for lbl in [
            panel._x_label,
            panel._y_label,
            panel._z_label,
            panel._type_label,
        ]:
            assert lbl.text() == "--"
        assert panel._speed_input.text() == ""
        assert panel._zone_input.text() == ""


class TestPropertyPanelEditable:
    """Tests for editable widget behavior."""

    def test_offset_fields_exist(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert isinstance(panel._dx_input, QLineEdit)
        assert isinstance(panel._dy_input, QLineEdit)
        assert isinstance(panel._dz_input, QLineEdit)
        assert isinstance(panel._dx_input.validator(), QDoubleValidator)

    def test_apply_offset_emits_signal(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=1)
        panel._dx_input.setText("10.0")
        signals = []
        panel.offset_applied.connect(lambda dx, dy, dz: signals.append((dx, dy, dz)))
        panel._apply_offset_btn.click()
        assert len(signals) == 1
        assert signals[0] == (10.0, 0.0, 0.0)

    def test_speed_change_emits_signal(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(speed="v100")
        panel.update_from_point(pt, count=1)
        signals = []
        panel.speed_changed.connect(lambda v: signals.append(v))
        panel._speed_input.setText("v500")
        panel._speed_input.editingFinished.emit()
        assert len(signals) == 1
        assert signals[0] == "v500"

    def test_zone_change_emits_signal(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(zone="z10")
        panel.update_from_point(pt, count=1)
        signals = []
        panel.zone_changed.connect(lambda v: signals.append(v))
        panel._zone_input.setText("z50")
        panel._zone_input.editingFinished.emit()
        assert len(signals) == 1
        assert signals[0] == "z50"

    def test_laser_combo_emits_signal(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(laser_on=True)
        panel.update_from_point(pt, count=1)
        signals = []
        panel.laser_changed.connect(lambda v: signals.append(v))
        panel._laser_combo.setCurrentIndex(1)  # OFF
        assert len(signals) == 1
        assert signals[0] is False

    def test_delete_btn_styled_red(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert "#CC3333" in panel._delete_btn.styleSheet()

    def test_insert_btn_disabled_multi_select(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=2)
        assert panel._insert_btn.isEnabled() is False

    def test_insert_btn_enabled_single_select(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=1)
        assert panel._insert_btn.isEnabled() is True

    def test_delete_btn_enabled_when_selected(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=2)
        assert panel._delete_btn.isEnabled() is True

    def test_delete_btn_disabled_when_no_selection(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert panel._delete_btn.isEnabled() is False

    def test_no_spurious_signal_on_update(self, qtbot):
        """Guard flag prevents signal emission during update_from_point."""
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        signals = []
        panel.speed_changed.connect(lambda v: signals.append(("speed", v)))
        panel.zone_changed.connect(lambda v: signals.append(("zone", v)))
        panel.laser_changed.connect(lambda v: signals.append(("laser", v)))
        # Programmatic update should not trigger signals
        pt = _make_edit_point(speed="v100", zone="z10", laser_on=False)
        panel.update_from_point(pt, count=1)
        assert len(signals) == 0

    def test_insert_emits_signal(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point()
        panel.update_from_point(pt, count=1)
        panel._dx_input.setText("5.0")
        panel._dy_input.setText("10.0")
        signals = []
        panel.insert_requested.connect(lambda dx, dy, dz: signals.append((dx, dy, dz)))
        panel._insert_btn.click()
        assert len(signals) == 1
        assert signals[0] == (5.0, 10.0, 0.0)

    def test_apply_offset_disabled_no_selection(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        assert panel._apply_offset_btn.isEnabled() is False

    def test_show_delete_dialog_reconnect(self, qtbot):
        """_show_delete_dialog returns 'reconnect' when reconnect button clicked."""
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        with patch.object(panel, "_show_delete_dialog", return_value="reconnect"):
            signals = []
            panel.delete_requested.connect(lambda v: signals.append(v))
            panel._selection_count = 1
            panel._on_delete_clicked()
            assert signals == ["reconnect"]

    def test_show_delete_dialog_cancel(self, qtbot):
        """_show_delete_dialog returns None when cancel clicked -- no signal."""
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        with patch.object(panel, "_show_delete_dialog", return_value=None):
            signals = []
            panel.delete_requested.connect(lambda v: signals.append(v))
            panel._selection_count = 1
            panel._on_delete_clicked()
            assert signals == []
