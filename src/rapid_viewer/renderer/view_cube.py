"""Navigation view cube for orthographic view snapping.

Renders a 3D cube overlay in the top-right corner of the GL widget
using QPainter. Clicking a visible face snaps the camera to that
orthographic view direction. XYZ axis lines with labels are drawn
through the cube center.

The rotation matrix used for drawing is the view matrix's 3x3 rotation
part — the same source of truth as the bottom-left axes indicator —
ensuring all on-screen coordinate displays are consistent.

Face-to-camera mapping (turntable camera convention):
  Front  (+Z): yaw=0,     pitch=0
  Back   (-Z): yaw=pi,    pitch=0
  Right  (+X): yaw=pi/2,  pitch=0
  Left   (-X): yaw=-pi/2, pitch=0
  Top    (+Y): yaw=0,     pitch=+pi/2
  Bottom (-Y): yaw=0,     pitch=-pi/2
"""

from __future__ import annotations

import math

import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF

# Cube half-size (unit cube from -1 to +1)
_VERTS = np.array(
    [
        [-1, -1, -1],  # 0: left-bottom-back
        [+1, -1, -1],  # 1: right-bottom-back
        [+1, +1, -1],  # 2: right-top-back
        [-1, +1, -1],  # 3: left-top-back
        [-1, -1, +1],  # 4: left-bottom-front
        [+1, -1, +1],  # 5: right-bottom-front
        [+1, +1, +1],  # 6: right-top-front
        [-1, +1, +1],  # 7: left-top-front
    ],
    dtype=np.float64,
)

_HP = math.pi / 2 - 0.01  # half-pi with epsilon for pitch clamp

# (vertex_indices, normal, label, base_color, snap_yaw, snap_pitch)
_FACES = [
    ([4, 5, 6, 7], np.array([0, 0, +1.0]), "+Z", QColor(100, 150, 220), 0.0, 0.0),
    ([1, 0, 3, 2], np.array([0, 0, -1.0]), "-Z", QColor(100, 150, 220), math.pi, 0.0),
    ([5, 1, 2, 6], np.array([+1, 0, 0.0]), "+X", QColor(220, 120, 120), math.pi / 2, 0.0),
    ([0, 4, 7, 3], np.array([-1, 0, 0.0]), "-X", QColor(220, 120, 120), -math.pi / 2, 0.0),
    ([7, 6, 2, 3], np.array([0, +1, 0.0]), "+Y", QColor(120, 200, 120), 0.0, _HP),
    ([0, 1, 5, 4], np.array([0, -1, 0.0]), "-Y", QColor(120, 200, 120), 0.0, -_HP),
]

# Axis tips extending beyond the cube, with colors and labels
_AXIS_LEN = 1.7
_AXES = [
    (np.array([_AXIS_LEN, 0.0, 0.0]), QColor(255, 80, 80), "X"),
    (np.array([0.0, _AXIS_LEN, 0.0]), QColor(80, 220, 80), "Y"),
    (np.array([0.0, 0.0, _AXIS_LEN]), QColor(80, 130, 255), "Z"),
]


def _project_3x3(rot: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply 3x3 rotation to Nx3 points using pyrr's row-vector convention.

    pyrr view matrices use row-vector convention: point @ matrix.
    So transformed = pts @ rot  (each row is a point).
    The result x/y map to screen right/up; z is depth.
    """
    return pts @ rot  # (N, 3)


class ViewCube:
    """Draws a navigation cube and handles click-to-snap-view."""

    def __init__(self, size: int = 110, padding: int = 10) -> None:
        self._size = size
        self._padding = padding

    def rect(self, widget_w: int, widget_h: int) -> QRectF:
        """Bounding rect of the view cube area (top-right corner)."""
        x = widget_w - self._size - self._padding
        y = self._padding
        return QRectF(x, y, self._size, self._size)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(
        self,
        painter: QPainter,
        view_rot: np.ndarray,
        widget_w: int,
        widget_h: int,
    ) -> None:
        """Draw the view cube using QPainter.

        Args:
            painter: Active QPainter on the GL widget.
            view_rot: 3x3 rotation from camera.view_rotation() (row-vector convention).
            widget_w: Widget width in pixels.
            widget_h: Widget height in pixels.
        """
        rect = self.rect(widget_w, widget_h)
        cx = rect.center().x()
        cy = rect.center().y()
        scale = self._size * 0.30

        # Transform cube vertices: world → view space (row-vector: pts @ rot)
        transformed = _project_3x3(view_rot, _VERTS)  # (8, 3)

        # Project to 2D screen: x=right, y needs flip (screen Y is down)
        pts_2d = [
            (cx + transformed[i, 0] * scale, cy - transformed[i, 1] * scale)
            for i in range(8)
        ]

        # Sort faces back-to-front for painter's algorithm
        face_order = []
        for indices, normal, label, color, yaw_s, pitch_s in _FACES:
            # Transform face normal the same way
            tn = (normal @ view_rot).astype(np.float64)
            avg_z = sum(transformed[i, 2] for i in indices) / 4.0
            face_order.append((avg_z, indices, tn, label, color))
        face_order.sort(key=lambda f: f[0])  # back first

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent background circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(20, 20, 30, 100)))
        painter.drawEllipse(rect)

        # Draw faces
        label_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(label_font)

        for avg_z, indices, tn, label, base_color in face_order:
            poly = QPolygonF([QPointF(*pts_2d[i]) for i in indices])

            facing = max(0.0, float(tn[2]))  # 0=edge-on, 1=fully facing
            alpha = int(80 + 175 * facing)
            brightness = int(facing * 40)
            fc = QColor(
                min(255, base_color.red() + brightness),
                min(255, base_color.green() + brightness),
                min(255, base_color.blue() + brightness),
                alpha,
            )

            painter.setPen(QPen(QColor(50, 50, 50, 160), 1.2))
            painter.setBrush(QBrush(fc))
            painter.drawPolygon(poly)

            # Face label (only on sufficiently front-facing faces)
            if facing > 0.35:
                fcx = sum(pts_2d[i][0] for i in indices) / 4.0
                fcy = sum(pts_2d[i][1] for i in indices) / 4.0
                text_alpha = int(255 * min(1.0, facing * 1.8))
                painter.setPen(QPen(QColor(240, 240, 240, text_alpha)))
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(label)
                painter.drawText(
                    QPointF(fcx - tw / 2, fcy + fm.ascent() / 2 - 1), label
                )

        # Draw XYZ axis lines through center
        for direction, color, label in _AXES:
            end_3d = (direction @ view_rot).astype(np.float64)
            ex = cx + end_3d[0] * scale
            ey = cy - end_3d[1] * scale
            painter.setPen(QPen(color, 2.2))
            painter.drawLine(QPointF(cx, cy), QPointF(ex, ey))
            # Label at axis tip
            painter.setPen(QPen(color))
            axis_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
            painter.setFont(axis_font)
            fm = painter.fontMetrics()
            tw = fm.horizontalAdvance(label)
            painter.drawText(QPointF(ex - tw / 2, ey + fm.ascent() / 2 - 1), label)

        painter.restore()

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def hit_test(
        self,
        x: float,
        y: float,
        view_rot: np.ndarray,
        widget_w: int,
        widget_h: int,
    ) -> tuple[float, float] | None:
        """Return (snap_yaw, snap_pitch) if click hits a visible cube face.

        Args:
            x, y: Mouse position in widget coords.
            view_rot: 3x3 rotation from camera.view_rotation().
            widget_w, widget_h: Widget dimensions.

        Returns:
            (yaw, pitch) to snap to, or None if no face was hit.
        """
        rect = self.rect(widget_w, widget_h)
        if not rect.contains(QPointF(x, y)):
            return None

        cx = rect.center().x()
        cy = rect.center().y()
        scale = self._size * 0.30

        transformed = _project_3x3(view_rot, _VERTS)
        pts_2d = [
            (cx + transformed[i, 0] * scale, cy - transformed[i, 1] * scale)
            for i in range(8)
        ]

        # Check front-facing faces (most visible first)
        hits: list[tuple[float, float, float]] = []
        for indices, normal, label, color, yaw_s, pitch_s in _FACES:
            tn = (normal @ view_rot).astype(np.float64)
            if tn[2] <= 0.0:
                continue  # back-facing
            poly = QPolygonF([QPointF(*pts_2d[i]) for i in indices])
            if poly.containsPoint(QPointF(x, y), Qt.FillRule.OddEvenFill):
                hits.append((float(tn[2]), yaw_s, pitch_s))

        if hits:
            hits.sort(key=lambda h: h[0], reverse=True)
            return (hits[0][1], hits[0][2])
        return None
