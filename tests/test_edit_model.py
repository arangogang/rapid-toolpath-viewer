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
