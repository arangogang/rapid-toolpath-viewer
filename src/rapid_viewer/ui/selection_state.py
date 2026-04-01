"""SelectionState model -- observable multi-select state for waypoint selection.

Manages a set of selected waypoint indices and emits Qt signals when the
selection changes. Supports single-select, toggle (Ctrl/Shift+click), and clear.

Public API:
    SelectionState.selected_indices  -- current selection as frozenset[int]
    SelectionState.select_single()   -- replace selection with one index
    SelectionState.toggle()          -- add or remove index from selection
    SelectionState.extend_to()       -- alias for toggle (Shift+click behavior)
    SelectionState.clear()           -- empty the selection

Signals:
    selection_changed(object)  -- emitted with frozenset[int] payload on any change
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal


class SelectionState(QObject):
    """Observable state for waypoint multi-selection.

    Signals:
        selection_changed(object): Emitted when selection changes.
            Payload is frozenset[int] of selected indices.
            Uses pyqtSignal(object) because PyQt6 does not support
            frozenset as a signal type directly.
    """

    selection_changed = pyqtSignal(object)  # payload: frozenset[int]

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._selected: set[int] = set()

    @property
    def selected_indices(self) -> frozenset[int]:
        """Current selection as an immutable frozenset."""
        return frozenset(self._selected)

    def select_single(self, index: int) -> None:
        """Replace entire selection with a single index. Per D-02 plain click."""
        self._selected = {index}
        self.selection_changed.emit(frozenset(self._selected))

    def toggle(self, index: int) -> None:
        """Add or remove index from selection. Per D-02 Ctrl/Shift+click."""
        if index in self._selected:
            self._selected.discard(index)
        else:
            self._selected.add(index)
        self.selection_changed.emit(frozenset(self._selected))

    def extend_to(self, index: int) -> None:
        """Shift+click behavior -- same as toggle per D-02."""
        self.toggle(index)

    def clear(self) -> None:
        """Clear all selections."""
        self._selected.clear()
        self.selection_changed.emit(frozenset())
