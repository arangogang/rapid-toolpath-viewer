"""Playback toolbar -- step/play/speed/scrubber controls for waypoint navigation.

Connects to a PlaybackState instance and provides UI controls for:
- Step back / Step forward buttons
- Play/Pause toggle with QTimer-driven auto-advance
- Speed slider (0.5x - 100.0x) + numeric spinbox
- Scrubber slider (seek to any waypoint)
- Position label showing "N / M" format
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QDoubleSpinBox,
    QLabel,
    QSizePolicy,
    QSlider,
    QToolBar,
    QWidget,
)

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
        self._blocking_speed = False
        self.setMovable(False)

        # Prevent toolbar from hiding buttons in overflow menu when window is small
        sp = self.sizePolicy()
        sp.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
        self.setSizePolicy(sp)

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

        # --- Speed controls: slider + spinbox ---
        speed_label = QLabel("Speed:")
        self.addWidget(speed_label)

        # Slider: 5..1000 maps to 0.5x..100.0x (value / 10.0 = multiplier)
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(5, 1000)
        self._speed_slider.setValue(10)
        self._speed_slider.setFixedWidth(120)
        self.addWidget(self._speed_slider)

        # Spinbox: direct numeric input for speed multiplier
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(0.5, 100.0)
        self._speed_spin.setValue(1.0)
        self._speed_spin.setSingleStep(0.5)
        self._speed_spin.setDecimals(1)
        self._speed_spin.setSuffix("x")
        self._speed_spin.setFixedWidth(75)
        self.addWidget(self._speed_spin)

        self.addSeparator()

        # --- Scrubber slider ---
        self._scrubber = QSlider(Qt.Orientation.Horizontal)
        self._scrubber.setRange(0, 0)
        self._scrubber.setMinimumWidth(100)
        self.addWidget(self._scrubber)

        # --- Timer for auto-play ---
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._state.step_forward)

        # --- Connect signals ---
        self._state.current_changed.connect(self._on_index_changed)
        self._state.moves_changed.connect(self._on_moves_changed)
        self._scrubber.valueChanged.connect(self._on_scrubber_changed)
        self._speed_slider.valueChanged.connect(self._on_slider_speed_changed)
        self._speed_spin.valueChanged.connect(self._on_spin_speed_changed)

    # -- Public helpers -------------------------------------------------------

    def _compute_interval(self) -> int:
        """Compute timer interval in ms from current speed spinbox value.

        Speed 1.0x -> 500ms base interval.
        Formula: max(1, int(500 / speed))
        """
        speed = self._speed_spin.value()
        return max(1, int(500 / speed))

    # -- Slots ----------------------------------------------------------------

    def _toggle_play(self) -> None:
        """Toggle auto-play timer on/off."""
        if self._timer.isActive():
            self._timer.stop()
            self._play_action.setText("Play")
        else:
            # Rewind to start if already at the end
            if (self._state.total > 0
                    and self._state.current_index >= self._state.total - 1):
                self._state.set_index(0)
            if self._state.total > 0:
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
            pass
        else:
            self._pos_label.setText("0 / 0")

    def _on_scrubber_changed(self, value: int) -> None:
        """Set playback index from scrubber, unless we are blocking."""
        if not self._blocking_scrubber:
            self._state.set_index(value)

    def _on_slider_speed_changed(self, value: int) -> None:
        """Sync spinbox from slider change."""
        if self._blocking_speed:
            return
        self._blocking_speed = True
        speed = value / 10.0
        self._speed_spin.setValue(speed)
        self._blocking_speed = False
        if self._timer.isActive():
            self._timer.setInterval(self._compute_interval())

    def _on_spin_speed_changed(self, value: float) -> None:
        """Sync slider from spinbox change."""
        if self._blocking_speed:
            return
        self._blocking_speed = True
        slider_val = int(value * 10)
        slider_val = max(self._speed_slider.minimum(), min(slider_val, self._speed_slider.maximum()))
        self._speed_slider.setValue(slider_val)
        self._blocking_speed = False
        if self._timer.isActive():
            self._timer.setInterval(self._compute_interval())
