"""EditModel and EditPoint -- mutable edit layer over parsed MoveInstruction data.

EditPoint wraps a frozen MoveInstruction into a mutable dataclass for editing.
EditModel manages a list of EditPoints and owns a QUndoStack for undo/redo.

Public API:
    EditPoint.from_move()        -- create mutable EditPoint from frozen MoveInstruction
    EditModel.load()             -- populate from list[MoveInstruction], clear undo
    EditModel.point_at()         -- access EditPoint by index
    EditModel.point_count        -- number of loaded points
    EditModel.undo_stack         -- QUndoStack instance
    EditModel.is_dirty           -- whether edits have been made since last save/load
    EditModel.apply_offset()     -- offset selected points by delta vector
    EditModel.set_property()     -- set speed/zone/laser_on on selected points
    EditModel.delete_points()    -- soft-delete points with reconnect/break mode
    EditModel.insert_after()     -- insert new point after source index
    EditModel.build_edited_moves() -- synthesize MoveInstructions from current state

Signals:
    model_reset()            -- emitted when a new file is loaded
    dirty_changed(bool)      -- emitted when clean/dirty state changes
    points_changed()         -- emitted by QUndoCommands after every mutation/undo
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QUndoStack

from rapid_viewer.parser.tokens import MoveInstruction


@dataclass
class EditPoint:
    """Mutable wrapper around a frozen MoveInstruction for editing.

    Stores the original instruction for diff/export and provides mutable
    copies of the editable fields (pos, speed, zone, laser_on).
    """

    original: MoveInstruction
    pos: np.ndarray       # mutable copy of target.pos, shape (3,)
    speed: str
    zone: str
    laser_on: bool
    deleted: bool = False  # soft-delete flag for Phase 5
    is_inserted: bool = False  # True for points created by InsertPointCommand

    @classmethod
    def from_move(cls, move: MoveInstruction) -> EditPoint:
        """Create an EditPoint from a frozen MoveInstruction.

        For MoveAbsJ (target=None), pos defaults to np.zeros(3).
        """
        pos = (
            move.target.pos.copy()
            if move.target is not None
            else np.zeros(3, dtype=np.float64)
        )
        return cls(
            original=move,
            pos=pos,
            speed=move.speed,
            zone=move.zone,
            laser_on=move.laser_on,
        )


class EditModel(QObject):
    """Mutable model layer over parsed move instructions with QUndoStack.

    Signals:
        model_reset(): Emitted when load() replaces the point list.
        dirty_changed(bool): Emitted when undo stack clean state changes.
            True means the model has unsaved changes.
    """

    model_reset = pyqtSignal()
    dirty_changed = pyqtSignal(bool)
    points_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._undo_stack = QUndoStack(self)
        self._points: list[EditPoint] = []
        # cleanChanged(bool): True means stack IS clean
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)

    @property
    def undo_stack(self) -> QUndoStack:
        """The QUndoStack owned by this model."""
        return self._undo_stack

    @property
    def is_dirty(self) -> bool:
        """Whether the model has unsaved changes."""
        return not self._undo_stack.isClean()

    @property
    def point_count(self) -> int:
        """Number of loaded EditPoints."""
        return len(self._points)

    def point_at(self, index: int) -> EditPoint | None:
        """Return the EditPoint at the given index, or None if out of range."""
        if 0 <= index < len(self._points):
            return self._points[index]
        return None

    def load(self, moves: list[MoveInstruction]) -> None:
        """Load move instructions as mutable EditPoints.

        Clears the undo stack and marks the model as clean.
        Emits model_reset().
        """
        self._points = [EditPoint.from_move(m) for m in moves]
        self._undo_stack.clear()
        self._undo_stack.setClean()
        self.model_reset.emit()

    def apply_offset(self, indices: list[int], delta: np.ndarray) -> None:
        """Offset selected points by delta vector. Pushes QUndoCommand."""
        from rapid_viewer.ui.commands import OffsetPointsCommand

        cmd = OffsetPointsCommand(self, indices, delta)
        self._undo_stack.push(cmd)

    def set_property(self, indices: list[int], field: str, value: str | bool) -> None:
        """Set a property on selected points. Pushes QUndoCommand."""
        from rapid_viewer.ui.commands import SetPropertyCommand

        cmd = SetPropertyCommand(self, indices, field, value)
        self._undo_stack.push(cmd)

    def delete_points(self, indices: list[int], mode: str) -> None:
        """Soft-delete selected points. mode is 'reconnect' or 'break'."""
        from rapid_viewer.ui.commands import DeletePointsCommand

        cmd = DeletePointsCommand(self, indices, mode)
        self._undo_stack.push(cmd)

    def insert_after(self, source_index: int, delta: np.ndarray) -> int:
        """Insert a new point after source_index. Returns index of new point."""
        from rapid_viewer.ui.commands import InsertPointCommand

        cmd = InsertPointCommand(self, source_index, delta)
        self._undo_stack.push(cmd)
        return source_index + 1

    def build_edited_moves(self) -> list[MoveInstruction]:
        """Synthesize MoveInstructions from current EditPoint state.

        Skips deleted points. Reflects modified pos/speed/zone/laser_on.
        Points without a Cartesian target (MoveAbsJ) are passed through unchanged.
        """
        from rapid_viewer.parser.tokens import RobTarget

        result: list[MoveInstruction] = []
        for point in self._points:
            if point.deleted:
                continue
            if point.original.target is None:
                result.append(point.original)
                continue
            new_target = RobTarget(
                name=point.original.target.name,
                pos=point.pos.copy(),
                orient=point.original.target.orient,
                confdata=point.original.target.confdata,
                extjoint=point.original.target.extjoint,
                source_line=point.original.target.source_line,
            )
            new_move = MoveInstruction(
                move_type=point.original.move_type,
                target=new_target,
                circle_point=point.original.circle_point,
                joint_target=point.original.joint_target,
                speed=point.speed,
                zone=point.zone,
                tool=point.original.tool,
                wobj=point.original.wobj,
                source_line=point.original.source_line,
                has_cartesian=point.original.has_cartesian,
                laser_on=point.laser_on,
            )
            result.append(new_move)
        return result

    def _on_clean_changed(self, clean: bool) -> None:
        """Forward QUndoStack.cleanChanged to dirty_changed with inverted sense."""
        self.dirty_changed.emit(not clean)
