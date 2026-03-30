"""Playback toolbar -- step/play/speed/scrubber controls for waypoint navigation.

Connects to a PlaybackState instance and provides UI controls for:
- Step back / Step forward buttons
- Play/Pause toggle with QTimer-driven auto-advance
- Speed slider (0.5x - 10.0x)
- Scrubber slider (seek to any waypoint)
- Position label showing "N / M" format
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QLabel, QSlider, QToolBar, QWidget

from rapid_viewer.ui.playback_state import PlaybackState


class PlaybackToolbar(QToolBar):
    """Playback controls: step, play/pause, speed, scrubber, position label.

    Requires a PlaybackState instance. Connects to its signals for updates.
    """

    waypoint_picked = pyqtSignal(int)  # reserved for consistency

    def __init__(self, playback_state: PlaybackState, parent: QWidget | None = None) -> None:
        super().__init__("Playback", parent)
        self._state = playback_state
        self._blocking_scrubber = False

        # --- Actions: Step Back, Play/Pause, Step Forward ---
        self._step_back_action = self.addAction("<<")
        self._step_back_action.triggered.connect(self._state.step_backward)

        self._play_action = self.addAction("Play")
        self._play_action.triggered.connect(self._toggle_play)

        self._step_fwd_action = self.addAction(">>")
        self._step_fwd_action.triggered.connect(self._state.step_forward)

        self.addSeparator()

        # --- Position label ---
        self._pos_label = QLabel("0 / 0")
        self.addWidget(self._pos_label)

        self.addSeparator()

        # --- Speed slider ---
        speed_label = QLabel("Speed:")
        self.addWidget(speed_label)

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(5, 100)
        self._speed_slider.setValue(10)
        self._speed_slider.setFixedWidth(120)
        self.addWidget(self._speed_slider)

        self.addSeparator()

        # --- Scrubber slider ---
        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setRange(0, 0)
        self.addWidget(self._scrubber)

        # --- Timer for auto-play ---
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._state.step_forward)

        # --- Connect signals ---
        self._state.current_changed.connect(self._on_index_changed)
        self._state.moves_changed.connect(self._on_moves_changed)
        self._scrubber.valueChanged.connect(self._on_scrubber_changed)
        self._speed_slider.valueChanged.connect(self._on_speed_changed)

    # -- Public helpers -------------------------------------------------------

    def _compute_interval(self) -> int:
        """Compute timer interval in ms from current speed slider value.

        Speed value 10 = 1.0x -> 500ms base interval.
        Formula: int(500 / (value / 10.0))
        """
        speed = self._speed_slider.value() / 10.0
        return int(500 / speed)

    # -- Slots ----------------------------------------------------------------

    def _toggle_play(self) -> None:
        """Toggle auto-play timer on/off."""
        if self._timer.isActive():
            self._timer.stop()
            self._play_action.setText("Play")
        else:
            self._timer.start(self._compute_interval())
            self._play_action.setText("Pause")

    def _on_index_changed(self, index: int) -> None:
        """Update label and scrubber when playback index changes."""
        self._pos_label.setText(f"{index + 1} / {self._state.total}")

        # Update scrubber without triggering valueChanged -> set_index loop
        self._blocking_scrubber = True
        self._scrubber.setValue(index)
        self._blocking_scrubber = False

        # Auto-stop at end
        if index >= self._state.total - 1 and self._timer.isActive():
            self._timer.stop()
            self._play_action.setText("Play")

    def _on_moves_changed(self) -> None:
        """Update scrubber range and label when move list changes."""
        total = self._state.total
        self._scrubber.setRange(0, max(0, total - 1))
        if total > 0:
            # Label will be updated by current_changed signal
            pass
        else:
            self._pos_label.setText("0 / 0")

    def _on_scrubber_changed(self, value: int) -> None:
        """Set playback index from scrubber, unless we are blocking."""
        if not self._blocking_scrubber:
            self._state.set_index(value)

    def _on_speed_changed(self, _value: int) -> None:
        """Update timer interval if currently playing."""
        if self._timer.isActive():
            self._timer.setInterval(self._compute_interval())
