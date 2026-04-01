"""Tests for PropertyPanel widget (INSP-01).

Verifies: selection header, position formatting (3 decimals),
motion fields, laser ON/OFF display, and clear-to-default behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget


# Minimal EditPoint mock -- Plan 01 creates the real class in edit_model.py.
# Mirror the interface contract from the plan.
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
            panel._speed_label,
            panel._zone_label,
            panel._laser_label,
        ]:
            assert lbl.text() == "--"


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
        assert panel._speed_label.text() == "v500"
        assert panel._zone_label.text() == "z50"

    def test_laser_on(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(laser_on=True)
        panel.update_from_point(pt, count=1)
        assert panel._laser_label.text() == "ON"

    def test_laser_off(self, qtbot):
        panel = PropertyPanel()
        qtbot.addWidget(panel)
        pt = _make_edit_point(laser_on=False)
        panel.update_from_point(pt, count=1)
        assert panel._laser_label.text() == "OFF"


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
            panel._speed_label,
            panel._zone_label,
            panel._laser_label,
        ]:
            assert lbl.text() == "--"
