"""Turntable camera for interactive 3D toolpath viewing.

Implements orbit (left-drag), pan (middle-drag), and zoom (scroll wheel)
using yaw/pitch angles for smooth, predictable rotation at any angle.

Usage in QOpenGLWidget mouse events:
    # mousePressEvent:
    camera.orbit_start(x, y, widget_w, widget_h)
    camera.pan_start(x, y)

    # mouseMoveEvent:
    camera.orbit_update(x, y, widget_w, widget_h)
    camera.pan_update(x, y, widget_w, widget_h)

    # wheelEvent:
    camera.zoom(delta)   # delta = angleDelta().y() / 120.0

    # resizeGL:
    camera.set_aspect(w / max(h, 1))

    # paintGL:
    mvp = camera.mvp()
    glUniformMatrix4fv(loc, 1, GL_FALSE, mvp.flatten())
"""

from __future__ import annotations

import numpy as np
import pyrr


class ArcballCamera:
    """Turntable-style interactive camera.

    All coordinates in mm (RAPID coordinate system).
    Uses yaw/pitch angles instead of quaternion arcball for predictable
    rotation at any angle including past 90 degrees.
    """

    def __init__(self) -> None:
        self._yaw: float = 0.0            # horizontal rotation in radians
        self._pitch: float = 0.3           # vertical rotation in radians
        self._distance: float = 1000.0     # mm from target
        self._pan_offset: np.ndarray = np.zeros(3, dtype=np.float64)
        self._fov: float = 45.0
        self._aspect: float = 1.0
        self._near: float = 0.1
        self._far: float = 100_000.0

        # State for drag operations
        self._orbit_start_yaw: float = 0.0
        self._orbit_start_pitch: float = 0.0
        self._orbit_start_mouse: np.ndarray = np.zeros(2)
        self._pan_start_mouse: np.ndarray = np.zeros(2, dtype=np.float64)
        self._pan_start_offset: np.ndarray = np.zeros(3, dtype=np.float64)

    # ------------------------------------------------------------------
    # Orbit (left-drag) — turntable yaw/pitch
    # ------------------------------------------------------------------

    def orbit_start(self, x: float, y: float, w: float, h: float) -> None:
        """Record drag start position for orbit."""
        self._orbit_start_mouse = np.array([x, y])
        self._orbit_start_yaw = self._yaw
        self._orbit_start_pitch = self._pitch

    def orbit_update(self, x: float, y: float, w: float, h: float) -> None:
        """Update rotation from current drag position."""
        dx = x - self._orbit_start_mouse[0]
        dy = y - self._orbit_start_mouse[1]
        sensitivity = 0.005
        self._yaw = self._orbit_start_yaw - dx * sensitivity
        self._pitch = self._orbit_start_pitch + dy * sensitivity
        # Clamp pitch to avoid flipping (just short of poles)
        self._pitch = np.clip(self._pitch, -np.pi / 2 + 0.01, np.pi / 2 - 0.01)

    # ------------------------------------------------------------------
    # Pan (middle-drag)
    # ------------------------------------------------------------------

    def pan_start(self, x: float, y: float) -> None:
        """Record drag start position for pan."""
        self._pan_start_mouse = np.array([x, y], dtype=np.float64)
        self._pan_start_offset = self._pan_offset.copy()

    def pan_update(self, x: float, y: float, w: float, h: float) -> None:
        """Update pan offset from current drag position."""
        dx = (x - self._pan_start_mouse[0]) / w
        dy = (y - self._pan_start_mouse[1]) / h
        pan_speed = self._distance * 2.0

        # Camera right/up vectors from yaw/pitch
        cos_y, sin_y = np.cos(self._yaw), np.sin(self._yaw)
        right = np.array([cos_y, 0.0, -sin_y])
        cos_p = np.cos(self._pitch)
        up = np.array([
            -sin_y * np.sin(self._pitch),
            cos_p,
            -cos_y * np.sin(self._pitch),
        ])

        self._pan_offset = (
            self._pan_start_offset
            - right * dx * pan_speed
            + up * dy * pan_speed
        )

    # ------------------------------------------------------------------
    # Zoom (scroll wheel)
    # ------------------------------------------------------------------

    def zoom(self, delta: float) -> None:
        """Adjust camera distance. delta > 0 = zoom in, delta < 0 = zoom out."""
        factor = 1.0 - delta * 0.1
        self._distance = max(0.5, self._distance * factor)

    # ------------------------------------------------------------------
    # Camera configuration
    # ------------------------------------------------------------------

    def set_aspect(self, aspect: float) -> None:
        """Update viewport aspect ratio (width / height)."""
        self._aspect = float(aspect)

    def set_view(self, yaw: float, pitch: float) -> None:
        """Snap camera to a specific orientation (used by view cube)."""
        self._yaw = yaw
        self._pitch = np.clip(pitch, -np.pi / 2 + 0.01, np.pi / 2 - 0.01)

    @property
    def yaw(self) -> float:
        """Current yaw angle in radians."""
        return self._yaw

    @property
    def pitch(self) -> float:
        """Current pitch angle in radians."""
        return self._pitch

    def reset(self, center: np.ndarray, scene_radius: float) -> None:
        """Fit camera to scene bounding sphere. Called after file load."""
        self._yaw = 0.0
        self._pitch = 0.5  # slight tilt for 3D perspective
        self._pan_offset = center.astype(np.float64)
        self._distance = max(scene_radius * 2.5, 10.0)

    def view_rotation(self) -> np.ndarray:
        """3x3 rotation part of the view matrix (float32).

        This is the authoritative rotation for all on-screen indicators
        (axes triad, view cube). Using it ensures all coordinate displays
        are consistent with the 3D scene.
        """
        return self.view_matrix()[:3, :3].copy()

    # ------------------------------------------------------------------
    # Matrix generation
    # ------------------------------------------------------------------

    def view_matrix(self) -> np.ndarray:
        """4x4 float32 view matrix."""
        cos_y, sin_y = np.cos(self._yaw), np.sin(self._yaw)
        cos_p, sin_p = np.cos(self._pitch), np.sin(self._pitch)

        # Eye position on a sphere around pan_offset
        eye = self._pan_offset + self._distance * np.array([
            sin_y * cos_p,
            sin_p,
            cos_y * cos_p,
        ])

        target = self._pan_offset
        up = np.array([0.0, 1.0, 0.0])

        return pyrr.matrix44.create_look_at(
            eye.astype(np.float32),
            target.astype(np.float32),
            up.astype(np.float32),
            dtype=np.float32,
        )

    def projection_matrix(self) -> np.ndarray:
        """4x4 float32 perspective projection matrix."""
        return pyrr.matrix44.create_perspective_projection(
            self._fov, self._aspect, self._near, self._far, dtype=np.float32
        )

    def mvp(self) -> np.ndarray:
        """Full MVP matrix (model = identity for toolpath scene).

        pyrr matrices use row-vector convention (point @ matrix), so the
        combined MVP for ``point @ view @ proj`` is ``view @ proj``.
        When uploaded to GL with GL_FALSE the row-major layout is
        reinterpreted as column-major, which implicitly transposes the
        matrix -- matching the GLSL column-vector convention
        ``gl_Position = u_mvp * vec4(pos, 1.0)``.
        """
        return (self.view_matrix() @ self.projection_matrix()).astype(np.float32)
