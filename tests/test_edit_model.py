"""Tests for EditModel and EditPoint -- mutable edit layer with QUndoStack.

Covers: EDIT-01, EDIT-02
"""

import numpy as np

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget, JointTarget
from rapid_viewer.ui.edit_model import EditModel, EditPoint


def _make_move(line: int, *, move_type: MoveType = MoveType.MOVEL) -> MoveInstruction:
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
    )


class TestEditPoint:
    """Unit tests for EditPoint dataclass."""

    def test_from_move_copies_pos(self):
        """EditPoint.from_move copies pos as mutable np.ndarray."""
        move = _make_move(1)
        point = EditPoint.from_move(move)

        assert np.array_equal(point.pos, move.target.pos)
        # Verify it is a copy, not same reference
        assert point.pos is not move.target.pos
        # Verify mutable
        point.pos[0] = 999.0
        assert move.target.pos[0] != 999.0

    def test_from_move_copies_fields(self):
        """EditPoint.from_move copies speed, zone, laser_on, stores original."""
        move = _make_move(1)
        point = EditPoint.from_move(move)

        assert point.speed == "v100"
        assert point.zone == "fine"
        assert point.laser_on is False
        assert point.original is move
        assert point.deleted is False

    def test_from_move_moveabsj(self):
        """EditPoint.from_move with MoveAbsJ (target=None) sets pos to zeros."""
        move = _make_move(1, move_type=MoveType.MOVEABSJ)
        point = EditPoint.from_move(move)

        assert np.array_equal(point.pos, np.zeros(3))
        assert point.original is move

    def test_from_move_is_inserted_false(self):
        """EditPoint.from_move creates point with is_inserted=False."""
        move = _make_move(1)
        point = EditPoint.from_move(move)

        assert point.is_inserted is False


class TestEditModel:
    """Unit tests for EditModel with QUndoStack."""

    def test_initial_empty(self, qtbot):
        """New EditModel has empty points list and clean undo stack."""
        model = EditModel()
        assert model.point_count == 0
        assert model.is_dirty is False

    def test_undo_stack(self, qtbot):
        """EditModel.undo_stack returns QUndoStack instance."""
        from PyQt6.QtGui import QUndoStack

        model = EditModel()
        assert isinstance(model.undo_stack, QUndoStack)

    def test_load(self, qtbot):
        """load(moves) populates points, clears undo stack, emits model_reset."""
        model = EditModel()
        moves = [_make_move(1), _make_move(2), _make_move(3)]

        received = []
        model.model_reset.connect(lambda: received.append("model_reset"))

        model.load(moves)

        assert model.point_count == 3
        assert received == ["model_reset"]

    def test_load_clears_undo(self, qtbot):
        """QUndoStack.isClean() is True after load."""
        model = EditModel()
        moves = [_make_move(1), _make_move(2)]
        model.load(moves)

        assert model.undo_stack.isClean()
        assert model.is_dirty is False

    def test_point_at(self, qtbot):
        """point_at(index) returns the EditPoint at given index."""
        model = EditModel()
        moves = [_make_move(1), _make_move(2)]
        model.load(moves)

        point = model.point_at(0)
        assert point is not None
        assert np.array_equal(point.pos, np.array([1.0, 0.0, 0.0]))

        point1 = model.point_at(1)
        assert point1 is not None
        assert np.array_equal(point1.pos, np.array([2.0, 0.0, 0.0]))

    def test_point_at_invalid(self, qtbot):
        """point_at with out-of-range index returns None."""
        model = EditModel()
        model.load([_make_move(1)])

        assert model.point_at(-1) is None
        assert model.point_at(999) is None

    def test_point_count(self, qtbot):
        """point_count returns number of loaded points."""
        model = EditModel()
        assert model.point_count == 0

        model.load([_make_move(1), _make_move(2), _make_move(3)])
        assert model.point_count == 3

    def test_dirty_changed_signal(self, qtbot):
        """dirty_changed signal emitted when clean state changes."""
        model = EditModel()
        model.load([_make_move(1)])

        received = []
        model.dirty_changed.connect(lambda dirty: received.append(dirty))

        # Manually mark stack as not clean to test signal
        model.undo_stack.setClean()
        # Push a dummy command to make it dirty
        from PyQt6.QtGui import QUndoCommand
        cmd = QUndoCommand("test")
        model.undo_stack.push(cmd)

        assert model.is_dirty is True
        assert True in received  # dirty_changed(True) was emitted

    def test_is_dirty_initially_false(self, qtbot):
        """is_dirty returns False initially and after load."""
        model = EditModel()
        assert model.is_dirty is False

        model.load([_make_move(1)])
        assert model.is_dirty is False


def _make_move_laser(line: int, laser_on: bool = False) -> MoveInstruction:
    """Create a MoveInstruction with configurable laser_on."""
    return MoveInstruction(
        move_type=MoveType.MOVEL,
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


class TestEditModelMutations:
    """Tests for EditModel mutation methods (apply_offset, set_property, etc.)."""

    def test_apply_offset(self, qtbot):
        """apply_offset shifts point position by delta."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        model.apply_offset([0], np.array([10.0, 0.0, 0.0]))
        assert model.point_at(0).pos[0] == 11.0

    def test_apply_offset_undo(self, qtbot):
        """Undo after apply_offset restores original position."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2)])

        model.apply_offset([0], np.array([10.0, 0.0, 0.0]))
        assert model.point_at(0).pos[0] == 11.0

        model.undo_stack.undo()
        assert model.point_at(0).pos[0] == 1.0

    def test_set_property_speed(self, qtbot):
        """set_property changes speed on selected points."""
        model = EditModel()
        model.load([_make_move(1)])

        model.set_property([0], "speed", "v500")
        assert model.point_at(0).speed == "v500"

    def test_delete_points_reconnect(self, qtbot):
        """delete_points with reconnect sets deleted=True."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        model.delete_points([1], "reconnect")
        assert model.point_at(1).deleted is True

    def test_delete_points_break(self, qtbot):
        """delete_points with break sets deleted=True and laser_on=False on next."""
        model = EditModel()
        model.load([
            _make_move_laser(1, True),
            _make_move_laser(2, True),
            _make_move_laser(3, True),
        ])

        model.delete_points([1], "break")
        assert model.point_at(1).deleted is True
        assert model.point_at(2).laser_on is False

    def test_insert_after(self, qtbot):
        """insert_after creates a new point at source_index + 1."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        idx = model.insert_after(0, np.array([5.0, 0.0, 0.0]))
        assert idx == 1
        assert model.point_count == 4
        assert model.point_at(1).pos[0] == 6.0  # 1.0 + 5.0

    def test_insert_after_undo(self, qtbot):
        """Undo after insert_after removes the inserted point."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        model.insert_after(0, np.array([5.0, 0.0, 0.0]))
        assert model.point_count == 4

        model.undo_stack.undo()
        assert model.point_count == 3

    def test_build_edited_moves_skips_deleted(self, qtbot):
        """build_edited_moves skips deleted points."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2), _make_move(3)])

        model.delete_points([1], "reconnect")
        moves = model.build_edited_moves()
        assert len(moves) == 2

    def test_build_edited_moves_reflects_offset(self, qtbot):
        """build_edited_moves reflects modified positions."""
        model = EditModel()
        model.load([_make_move(1), _make_move(2)])

        model.apply_offset([0], np.array([10.0, 0.0, 0.0]))
        moves = model.build_edited_moves()
        assert moves[0].target.pos[0] == 11.0

    def test_points_changed_signal(self, qtbot):
        """points_changed signal emitted on mutation."""
        model = EditModel()
        model.load([_make_move(1)])

        received = []
        model.points_changed.connect(lambda: received.append("changed"))

        model.apply_offset([0], np.array([1.0, 0.0, 0.0]))
        assert len(received) == 1
