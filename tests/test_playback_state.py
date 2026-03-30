"""Tests for PlaybackState model -- playback navigation state with Qt signals.

Covers: PLAY-01, PLAY-02, PLAY-03
"""

import pytest
import numpy as np

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget
from rapid_viewer.ui.playback_state import PlaybackState


def _make_move(line: int) -> MoveInstruction:
    """Create a minimal MoveInstruction with the given source_line."""
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
    )


class TestPlaybackState:
    """Unit tests for PlaybackState model."""

    def test_initial_state(self, qtbot):
        """New PlaybackState has current_index=-1, total=0, current_move=None."""
        state = PlaybackState()
        qtbot.addWidget(state) if hasattr(state, 'show') else None
        assert state.current_index == -1
        assert state.total == 0
        assert state.current_move is None

    def test_set_moves(self, qtbot):
        """set_moves([m1, m2, m3]) sets current_index=0, total=3, emits moves_changed then current_changed(0)."""
        state = PlaybackState()
        moves = [_make_move(1), _make_move(2), _make_move(3)]

        signals_received = []
        state.moves_changed.connect(lambda: signals_received.append("moves_changed"))
        state.current_changed.connect(lambda idx: signals_received.append(("current_changed", idx)))

        state.set_moves(moves)

        assert state.current_index == 0
        assert state.total == 3
        assert signals_received == ["moves_changed", ("current_changed", 0)]

    def test_set_moves_empty(self, qtbot):
        """set_moves([]) sets current_index=-1, total=0."""
        state = PlaybackState()
        # First set some moves
        state.set_moves([_make_move(1), _make_move(2)])

        signals_received = []
        state.moves_changed.connect(lambda: signals_received.append("moves_changed"))
        state.current_changed.connect(lambda idx: signals_received.append(("current_changed", idx)))

        state.set_moves([])

        assert state.current_index == -1
        assert state.total == 0
        # moves_changed should be emitted, but current_changed should NOT (empty list)
        assert signals_received == ["moves_changed"]

    def test_step_forward(self, qtbot):
        """From index 0 with 3 moves, step_forward() sets index to 1, emits current_changed(1)."""
        state = PlaybackState()
        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])

        signals_received = []
        state.current_changed.connect(lambda idx: signals_received.append(idx))

        state.step_forward()

        assert state.current_index == 1
        assert signals_received == [1]

    def test_step_forward_at_end(self, qtbot):
        """From index 2 with 3 moves, step_forward() stays at 2, no signal emitted."""
        state = PlaybackState()
        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])
        state.set_index(2)

        signals_received = []
        state.current_changed.connect(lambda idx: signals_received.append(idx))

        state.step_forward()

        assert state.current_index == 2
        assert signals_received == []

    def test_step_backward(self, qtbot):
        """From index 2, step_backward() sets index to 1, emits current_changed(1)."""
        state = PlaybackState()
        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])
        state.set_index(2)

        signals_received = []
        state.current_changed.connect(lambda idx: signals_received.append(idx))

        state.step_backward()

        assert state.current_index == 1
        assert signals_received == [1]

    def test_step_backward_at_start(self, qtbot):
        """From index 0, step_backward() stays at 0, no signal emitted."""
        state = PlaybackState()
        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])

        signals_received = []
        state.current_changed.connect(lambda idx: signals_received.append(idx))

        state.step_backward()

        assert state.current_index == 0
        assert signals_received == []

    def test_set_index_valid(self, qtbot):
        """set_index(2) sets index to 2, emits current_changed(2)."""
        state = PlaybackState()
        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])

        signals_received = []
        state.current_changed.connect(lambda idx: signals_received.append(idx))

        state.set_index(2)

        assert state.current_index == 2
        assert signals_received == [2]

    def test_set_index_out_of_range(self, qtbot):
        """set_index(-1) and set_index(999) do nothing, no signal."""
        state = PlaybackState()
        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])

        signals_received = []
        state.current_changed.connect(lambda idx: signals_received.append(idx))

        state.set_index(-1)
        assert state.current_index == 0
        assert signals_received == []

        state.set_index(999)
        assert state.current_index == 0
        assert signals_received == []

    def test_current_move(self, qtbot):
        """After set_moves and set_index(1), current_move returns moves[1]."""
        state = PlaybackState()
        moves = [_make_move(1), _make_move(2), _make_move(3)]
        state.set_moves(moves)
        state.set_index(1)

        assert state.current_move is moves[1]
