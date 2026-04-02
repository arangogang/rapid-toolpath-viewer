"""QUndoCommand subclasses for toolpath modification operations.

Provides undo/redo commands for:
    OffsetPointsCommand  -- shift point positions by a delta vector
    SetPropertyCommand   -- change speed/zone/laser_on on selected points
    DeletePointsCommand  -- soft-delete points with reconnect or break mode
    InsertPointCommand   -- insert a new point after a source point

All commands operate on EditModel/EditPoint and emit model.points_changed
on both redo() and undo() to trigger downstream geometry rebuilds.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtGui import QUndoCommand

if TYPE_CHECKING:
    from rapid_viewer.ui.edit_model import EditModel, EditPoint


class OffsetPointsCommand(QUndoCommand):
    """Shift the position of selected EditPoints by a delta vector.

    redo(): adds delta to each point's pos.
    undo(): restores saved original positions.
    """

    def __init__(
        self,
        model: EditModel,
        indices: list[int],
        delta: np.ndarray,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(f"Offset {len(indices)} point(s)", parent)
        self._model = model
        self._indices = list(indices)
        self._delta = delta.copy()
        self._old_positions = [model.point_at(i).pos.copy() for i in indices]

    def redo(self) -> None:
        for idx in self._indices:
            point = self._model.point_at(idx)
            point.pos += self._delta
        self._model.points_changed.emit()

    def undo(self) -> None:
        for i, idx in enumerate(self._indices):
            point = self._model.point_at(idx)
            point.pos[:] = self._old_positions[i]
        self._model.points_changed.emit()


class SetPropertyCommand(QUndoCommand):
    """Set a property (speed, zone, laser_on) on selected EditPoints.

    redo(): sets the new value on all indexed points.
    undo(): restores the saved old values.
    """

    def __init__(
        self,
        model: EditModel,
        indices: list[int],
        field: str,
        value: str | bool,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(f"Set {field} ({len(indices)} point(s))", parent)
        self._model = model
        self._indices = list(indices)
        self._field = field
        self._value = value
        self._old_values = [getattr(model.point_at(i), field) for i in indices]

    def redo(self) -> None:
        for idx in self._indices:
            setattr(self._model.point_at(idx), self._field, self._value)
        self._model.points_changed.emit()

    def undo(self) -> None:
        for i, idx in enumerate(self._indices):
            setattr(self._model.point_at(idx), self._field, self._old_values[i])
        self._model.points_changed.emit()


class DeletePointsCommand(QUndoCommand):
    """Soft-delete selected EditPoints with reconnect or break mode.

    reconnect: simply marks points as deleted; path skips over them.
    break: additionally sets laser_on=False on the first non-deleted point
           after each deleted span, breaking the toolpath continuity.

    redo(): sets deleted=True (and for break mode, laser_on=False on next).
    undo(): restores original deleted flags (and laser_on values for break mode).
    """

    def __init__(
        self,
        model: EditModel,
        indices: list[int],
        mode: str,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__(f"Delete {len(indices)} point(s) ({mode})", parent)
        self._model = model
        self._indices = sorted(indices)
        self._mode = mode
        self._old_deleted = [model.point_at(i).deleted for i in self._indices]

        # For break mode: find the first non-deleted point after the deleted span
        self._break_targets: list[tuple[int, bool]] = []  # (index, old_laser_on)
        if mode == "break":
            deleted_set = set(self._indices)
            max_idx = max(self._indices)
            for j in range(max_idx + 1, model.point_count):
                if j not in deleted_set:
                    point = model.point_at(j)
                    self._break_targets.append((j, point.laser_on))
                    break

    def redo(self) -> None:
        for idx in self._indices:
            self._model.point_at(idx).deleted = True
        for target_idx, _old_val in self._break_targets:
            self._model.point_at(target_idx).laser_on = False
        self._model.points_changed.emit()

    def undo(self) -> None:
        for i, idx in enumerate(self._indices):
            self._model.point_at(idx).deleted = self._old_deleted[i]
        for target_idx, old_val in self._break_targets:
            self._model.point_at(target_idx).laser_on = old_val
        self._model.points_changed.emit()


class InsertPointCommand(QUndoCommand):
    """Insert a new EditPoint after a source point.

    The new point copies speed/zone/laser_on from the source and has
    pos = source.pos + delta.

    redo(): inserts the new point at source_index + 1.
    undo(): removes the inserted point.
    """

    def __init__(
        self,
        model: EditModel,
        source_index: int,
        delta: np.ndarray,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__("Insert point", parent)
        self._model = model
        self._insert_index = source_index + 1

        source = model.point_at(source_index)
        from rapid_viewer.ui.edit_model import EditPoint

        self._new_point = EditPoint(
            original=source.original,
            pos=source.pos.copy() + delta,
            speed=source.speed,
            zone=source.zone,
            laser_on=source.laser_on,
        )

    def redo(self) -> None:
        self._model._points.insert(self._insert_index, self._new_point)
        self._model.points_changed.emit()

    def undo(self) -> None:
        self._model._points.pop(self._insert_index)
        self._model.points_changed.emit()
