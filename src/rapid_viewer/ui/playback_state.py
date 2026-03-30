"""PlaybackState model -- central source of truth for waypoint navigation.

Emits Qt signals when current waypoint changes, enabling all UI components
(code panel, toolbar, GL widget) to stay synchronized.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from rapid_viewer.parser.tokens import MoveInstruction


class PlaybackState(QObject):
    """Observable state for step-through playback of parsed move instructions.

    Signals:
        current_changed(int): Emitted when current_index changes. Payload is new index.
        moves_changed(): Emitted when the move list is replaced via set_moves().
    """

    current_changed = pyqtSignal(int)
    moves_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._moves: list[MoveInstruction] = []
        self._current_index: int = -1

    # -- Properties ----------------------------------------------------------

    @property
    def current_index(self) -> int:
        """Current waypoint index (0-based). -1 if no moves loaded."""
        return self._current_index

    @property
    def total(self) -> int:
        """Total number of moves in the current list."""
        return len(self._moves)

    @property
    def current_move(self) -> MoveInstruction | None:
        """The currently selected MoveInstruction, or None if no moves."""
        if 0 <= self._current_index < len(self._moves):
            return self._moves[self._current_index]
        return None

    # -- Mutators ------------------------------------------------------------

    def set_moves(self, moves: list[MoveInstruction]) -> None:
        """Replace the move list and reset index.

        Always emits moves_changed(). If the new list is non-empty,
        also emits current_changed(0).
        """
        self._moves = list(moves)
        if self._moves:
            self._current_index = 0
            self.moves_changed.emit()
            self.current_changed.emit(0)
        else:
            self._current_index = -1
            self.moves_changed.emit()

    def set_index(self, index: int) -> None:
        """Set current index if valid and different from current.

        Does nothing (no signal) if index is out of range or same as current.
        """
        if index < 0 or index >= len(self._moves):
            return
        if index == self._current_index:
            return
        self._current_index = index
        self.current_changed.emit(index)

    def step_forward(self) -> None:
        """Advance to next waypoint. No-op at end of list."""
        self.set_index(self._current_index + 1)

    def step_backward(self) -> None:
        """Go back to previous waypoint. No-op at start of list."""
        self.set_index(self._current_index - 1)
