"""Tests for PlaybackToolbar widget -- playback controls connected to PlaybackState.

Covers: PLAY-04, PLAY-05, PLAY-06, PLAY-07
"""

import numpy as np
import pytest

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget
from rapid_viewer.ui.playback_state import PlaybackState
from rapid_viewer.ui.playback_toolbar import PlaybackToolbar


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


class TestPlaybackToolbar:
    """Unit tests for PlaybackToolbar widget."""

    def test_position_label_updates(self, qtbot):
        """set_moves(3 items), set_index(1) -> label text is '2 / 3'."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        state.set_moves([_make_move(1), _make_move(2), _make_move(3)])
        state.set_index(1)

        assert toolbar._pos_label.text() == "2 / 3"

    def test_position_label_empty(self, qtbot):
        """No moves -> label text is '0 / 0'."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        assert toolbar._pos_label.text() == "0 / 0"

    def test_speed_slider_range(self, qtbot):
        """Slider minimum=5, maximum=100, default=10."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        assert toolbar._speed_slider.minimum() == 5
        assert toolbar._speed_slider.maximum() == 100
        assert toolbar._speed_slider.value() == 10

    def test_speed_to_interval(self, qtbot):
        """At speed 10 (1.0x), interval is 500ms; at 50 (5.0x), interval is 100ms."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        # Speed 10 = 1.0x -> 500 / 1.0 = 500ms
        toolbar._speed_slider.setValue(10)
        assert toolbar._compute_interval() == 500

        # Speed 50 = 5.0x -> 500 / 5.0 = 100ms
        toolbar._speed_slider.setValue(50)
        assert toolbar._compute_interval() == 100

    def test_scrubber_range_updates(self, qtbot):
        """set_moves(5 items) -> scrubber slider range is 0-4."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        state.set_moves([_make_move(i) for i in range(1, 6)])

        assert toolbar._scrubber.minimum() == 0
        assert toolbar._scrubber.maximum() == 4

    def test_scrubber_sets_index(self, qtbot):
        """scrubber.setValue(3) -> playback_state.current_index == 3."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        state.set_moves([_make_move(i) for i in range(1, 6)])
        toolbar._scrubber.setValue(3)

        assert state.current_index == 3

    def test_play_pause_toggle(self, qtbot):
        """Trigger play -> timer active; trigger again -> timer stopped."""
        state = PlaybackState()
        toolbar = PlaybackToolbar(state)
        qtbot.addWidget(toolbar)

        state.set_moves([_make_move(i) for i in range(1, 6)])

        # First toggle: play
        toolbar._toggle_play()
        assert toolbar._timer.isActive()

        # Second toggle: pause
        toolbar._toggle_play()
        assert not toolbar._timer.isActive()
