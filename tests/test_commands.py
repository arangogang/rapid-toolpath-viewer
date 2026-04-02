"""Tests for QUndoCommand subclasses -- offset, set property, delete, insert.

Covers: MOD-01, MOD-02, MOD-03, MOD-04
"""

from __future__ import annotations

import numpy as np

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget, JointTarget
from rapid_viewer.ui.edit_model import EditModel, EditPoint


def _make_move(
    line: int,
    *,
    move_type: MoveType = MoveType.MOVEL,
    laser_on: bool = False,
) -> MoveInstruction:
    """Create a minimal MoveInstruction for testing."""
    if move_type == MoveType.MOVEABSJ:
        return MoveInstruction(
            move_type=move_type,
            target=None,
            circle_point=None,
            joint_target=JointTarget(
                name=f"jpos{line}",
                robax=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                extax=(9e9, 9e9, 9e9, 9e9, 9e9, 9e9),
                source_line=line,
            ),
            speed="v100",
            zone="fine",
            tool="tool0",
            wobj="wobj0",
            source_line=line,
            has_cartesian=False,
            laser_on=laser_on,
        )
    return MoveInstruction(
        move_type=move_type,
        target=RobTarget(
            name=f"p{line}",
            pos=np.array([float(line), 0.0, 0.0], dtype=np.float64),
            orient=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
            confdata=(0, 0, 0, 0),
            extjoint=(9e9, 9e9, 9e9, 9e9, 9e9, 9e9),
            source_line=line,
        ),
        circle_point=None,
        joint_target=None,
        speed="v100",
        zone="fine",
        tool="tool0",
        wobj="wobj0",
        source_line=line,
        has_cartesian=True,
        laser_on=laser_on,
    )


class TestOffsetCommand:
    """Tests for OffsetPointsCommand redo/undo."""

    def test_single_point_offset_redo(self, qtbot):
        """Offset single point by delta via redo."""
        from rapid_viewer.ui.commands import OffsetPointsCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        delta = np.array([10.0, 0.0, 0.0])
        cmd = OffsetPointsCommand(model, [0], delta)
        model.undo_stack.push(cmd)

        assert model.point_at(0).pos[0] == 11.0  # 1.0 + 10.0

    def test_single_point_offset_undo(self, qtbot):
        """Undo restores original position."""
        from rapid_viewer.ui.commands import OffsetPointsCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2)])

        delta = np.array([10.0, 5.0, 0.0])
        cmd = OffsetPointsCommand(model, [0], delta)
        model.undo_stack.push(cmd)

        model.undo_stack.undo()
        assert np.allclose(model.point_at(0).pos, [1.0, 0.0, 0.0])

    def test_multi_point_offset(self, qtbot):
        """Offset multiple points simultaneously."""
        from rapid_viewer.ui.commands import OffsetPointsCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        delta = np.array([5.0, 5.0, 5.0])
        cmd = OffsetPointsCommand(model, [0, 2], delta)
        model.undo_stack.push(cmd)

        assert model.point_at(0).pos[0] == 6.0   # 1.0 + 5.0
        assert model.point_at(2).pos[0] == 8.0   # 3.0 + 5.0
        # Unmodified point
        assert model.point_at(1).pos[0] == 2.0

    def test_emits_points_changed(self, qtbot):
        """Offset command emits points_changed on redo and undo."""
        from rapid_viewer.ui.commands import OffsetPointsCommand

        model = EditModel()
        model.load([_make_move(1)])

        received = []
        model.points_changed.connect(lambda: received.append("changed"))

        delta = np.array([1.0, 0.0, 0.0])
        cmd = OffsetPointsCommand(model, [0], delta)
        model.undo_stack.push(cmd)
        assert len(received) == 1

        model.undo_stack.undo()
        assert len(received) == 2


class TestSetPropertyCommand:
    """Tests for SetPropertyCommand redo/undo."""

    def test_set_speed_single(self, qtbot):
        """Set speed on a single point."""
        from rapid_viewer.ui.commands import SetPropertyCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2)])

        cmd = SetPropertyCommand(model, [0], "speed", "v500")
        model.undo_stack.push(cmd)

        assert model.point_at(0).speed == "v500"
        assert model.point_at(1).speed == "v100"  # unchanged

    def test_set_zone_multi(self, qtbot):
        """Set zone on multiple points."""
        from rapid_viewer.ui.commands import SetPropertyCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        cmd = SetPropertyCommand(model, [0, 1, 2], "zone", "z10")
        model.undo_stack.push(cmd)

        for i in range(3):
            assert model.point_at(i).zone == "z10"

    def test_set_laser_on_bool(self, qtbot):
        """Set laser_on boolean property."""
        from rapid_viewer.ui.commands import SetPropertyCommand

        model = EditModel()
        model.load([_make_move(1)])

        cmd = SetPropertyCommand(model, [0], "laser_on", True)
        model.undo_stack.push(cmd)
        assert model.point_at(0).laser_on is True

    def test_undo_restores_old_values(self, qtbot):
        """Undo restores original property values."""
        from rapid_viewer.ui.commands import SetPropertyCommand

        model = EditModel()
        model.load([_make_move(1)])
        assert model.point_at(0).speed == "v100"

        cmd = SetPropertyCommand(model, [0], "speed", "v500")
        model.undo_stack.push(cmd)
        assert model.point_at(0).speed == "v500"

        model.undo_stack.undo()
        assert model.point_at(0).speed == "v100"

    def test_emits_points_changed(self, qtbot):
        """SetPropertyCommand emits points_changed on redo and undo."""
        from rapid_viewer.ui.commands import SetPropertyCommand

        model = EditModel()
        model.load([_make_move(1)])

        received = []
        model.points_changed.connect(lambda: received.append("changed"))

        cmd = SetPropertyCommand(model, [0], "speed", "v500")
        model.undo_stack.push(cmd)
        assert len(received) == 1

        model.undo_stack.undo()
        assert len(received) == 2


class TestDeleteCommand:
    """Tests for DeletePointsCommand redo/undo."""

    def test_reconnect_sets_deleted(self, qtbot):
        """Reconnect mode sets deleted=True on target points."""
        from rapid_viewer.ui.commands import DeletePointsCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        cmd = DeletePointsCommand(model, [1], "reconnect")
        model.undo_stack.push(cmd)

        assert model.point_at(1).deleted is True
        assert model.point_at(0).deleted is False
        assert model.point_at(2).deleted is False

    def test_break_sets_laser_off_on_next(self, qtbot):
        """Break mode sets laser_on=False on first non-deleted point after span."""
        from rapid_viewer.ui.commands import DeletePointsCommand

        model = EditModel()
        model.load([
            _make_move(1, laser_on=True),
            _make_move(2, laser_on=True),
            _make_move(3, laser_on=True),
        ])

        cmd = DeletePointsCommand(model, [1], "break")
        model.undo_stack.push(cmd)

        assert model.point_at(1).deleted is True
        assert model.point_at(2).laser_on is False

    def test_undo_restores_deleted_and_laser(self, qtbot):
        """Undo restores deleted flags and laser_on state."""
        from rapid_viewer.ui.commands import DeletePointsCommand

        model = EditModel()
        model.load([
            _make_move(1, laser_on=True),
            _make_move(2, laser_on=True),
            _make_move(3, laser_on=True),
        ])

        cmd = DeletePointsCommand(model, [1], "break")
        model.undo_stack.push(cmd)
        assert model.point_at(1).deleted is True
        assert model.point_at(2).laser_on is False

        model.undo_stack.undo()
        assert model.point_at(1).deleted is False
        assert model.point_at(2).laser_on is True

    def test_emits_points_changed(self, qtbot):
        """DeletePointsCommand emits points_changed on redo and undo."""
        from rapid_viewer.ui.commands import DeletePointsCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2)])

        received = []
        model.points_changed.connect(lambda: received.append("changed"))

        cmd = DeletePointsCommand(model, [0], "reconnect")
        model.undo_stack.push(cmd)
        assert len(received) == 1

        model.undo_stack.undo()
        assert len(received) == 2


class TestInsertCommand:
    """Tests for InsertPointCommand redo/undo."""

    def test_insert_creates_point(self, qtbot):
        """Insert creates new EditPoint at source_index + 1."""
        from rapid_viewer.ui.commands import InsertPointCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        delta = np.array([5.0, 0.0, 0.0])
        cmd = InsertPointCommand(model, 0, delta)
        model.undo_stack.push(cmd)

        assert model.point_count == 4
        inserted = model.point_at(1)
        assert inserted is not None
        assert inserted.pos[0] == 6.0  # 1.0 + 5.0

    def test_insert_copies_properties(self, qtbot):
        """Inserted point copies speed/zone/laser_on from source."""
        from rapid_viewer.ui.commands import InsertPointCommand

        model = EditModel()
        model.load([_make_move(1, laser_on=True)])
        model.point_at(0).speed = "v500"

        delta = np.array([0.0, 0.0, 0.0])
        cmd = InsertPointCommand(model, 0, delta)
        model.undo_stack.push(cmd)

        inserted = model.point_at(1)
        assert inserted.speed == "v500"
        assert inserted.laser_on is True

    def test_undo_removes_inserted_point(self, qtbot):
        """Undo removes the inserted point, restoring original count."""
        from rapid_viewer.ui.commands import InsertPointCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        delta = np.array([5.0, 0.0, 0.0])
        cmd = InsertPointCommand(model, 0, delta)
        model.undo_stack.push(cmd)
        assert model.point_count == 4

        model.undo_stack.undo()
        assert model.point_count == 3

    def test_emits_points_changed(self, qtbot):
        """InsertPointCommand emits points_changed on redo and undo."""
        from rapid_viewer.ui.commands import InsertPointCommand

        model = EditModel()
        model.load([_make_move(1)])

        received = []
        model.points_changed.connect(lambda: received.append("changed"))

        delta = np.array([1.0, 0.0, 0.0])
        cmd = InsertPointCommand(model, 0, delta)
        model.undo_stack.push(cmd)
        assert len(received) == 1

        model.undo_stack.undo()
        assert len(received) == 2

    def test_insert_sets_is_inserted_true(self, qtbot):
        """InsertPointCommand sets is_inserted=True on the new point."""
        from rapid_viewer.ui.commands import InsertPointCommand

        model = EditModel()
        model.load([_make_move(1), _make_move(2)])

        delta = np.array([0.0, 0.0, 0.0])
        cmd = InsertPointCommand(model, 0, delta)
        model.undo_stack.push(cmd)

        inserted = model.point_at(1)
        assert inserted.is_inserted is True
        # Original points should not be marked as inserted
        assert model.point_at(0).is_inserted is False
