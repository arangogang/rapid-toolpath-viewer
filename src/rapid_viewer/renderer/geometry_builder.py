"""Convert ParseResult into numpy vertex arrays for GPU upload.

All output arrays are float32 with interleaved layout [x, y, z, r, g, b],
shape (N, 6). MoveAbsJ moves (has_cartesian=False) are always skipped.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

import pyrr

from rapid_viewer.parser.tokens import MoveInstruction, MoveType, ParseResult

# Color palette (RGB float 0.0-1.0)
COLOR_MOVEL = (0.2, 0.8, 0.2)  # solid green
COLOR_MOVEJ = (0.8, 0.5, 0.1)  # dashed orange
COLOR_MOVEC = (0.2, 0.6, 1.0)  # arc blue
COLOR_MARKER = (1.0, 1.0, 0.3)  # waypoint yellow


@dataclass
class GeometryBuffers:
    """GPU-ready vertex arrays for the toolpath scene.

    solid_verts: MoveL segments + MoveC arc polylines
    dashed_verts: MoveJ segments
    marker_verts: one point per Cartesian waypoint
    Each array shape (N, 6) float32: [x, y, z, r, g, b]
    """

    solid_verts: np.ndarray
    dashed_verts: np.ndarray
    marker_verts: np.ndarray
    triad_verts: np.ndarray


def build_geometry(result: ParseResult, arc_segments: int = 32) -> GeometryBuffers:
    """Convert ParseResult into renderable vertex arrays.

    Iterates result.moves in order. Tracks prev_pos to form line segments.
    MoveAbsJ (has_cartesian=False or target is None) are skipped entirely.
    """
    solid: list[float] = []
    dashed: list[float] = []
    markers: list[float] = []
    prev_pos: np.ndarray | None = None

    for move in result.moves:
        if not move.has_cartesian or move.target is None:
            continue

        curr_pos = move.target.pos.astype(np.float64)

        if move.move_type == MoveType.MOVEL:
            if prev_pos is not None:
                _add_segment(solid, prev_pos, curr_pos, COLOR_MOVEL)

        elif move.move_type == MoveType.MOVEJ:
            if prev_pos is not None:
                _add_segment(dashed, prev_pos, curr_pos, COLOR_MOVEJ)

        elif move.move_type == MoveType.MOVEC:
            if prev_pos is not None and move.circle_point is not None:
                arc_pts = tessellate_arc(
                    prev_pos,
                    move.circle_point.pos.astype(np.float64),
                    curr_pos,
                    arc_segments,
                )
                _add_polyline(solid, arc_pts, COLOR_MOVEC)

        # Marker at every Cartesian waypoint
        markers.extend([*curr_pos, *COLOR_MARKER])
        prev_pos = curr_pos

    def _to_array(buf: list[float]) -> np.ndarray:
        if buf:
            return np.array(buf, dtype=np.float32).reshape(-1, 6)
        return np.empty((0, 6), dtype=np.float32)

    return GeometryBuffers(
        solid_verts=_to_array(solid),
        dashed_verts=_to_array(dashed),
        marker_verts=_to_array(markers),
        triad_verts=build_triad_vertices(result.moves),
    )


def tessellate_arc(
    start: np.ndarray,
    via: np.ndarray,
    end: np.ndarray,
    n_segments: int = 32,
) -> np.ndarray:
    """Tessellate a 3-point circular arc into (n_segments+1, 3) points.

    start: previous move endpoint (robot TCP start of arc)
    via:   MoveC circle_point.pos (shapes the arc, not the start)
    end:   MoveC target.pos

    Falls back to np.linspace straight line for degenerate (collinear) input.
    """
    v1 = via - start
    v2 = end - start
    normal = np.cross(v1, v2)
    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-6:
        return np.linspace(start, end, n_segments + 1)
    normal = normal / norm_len

    ax = np.dot(v1, v1)
    ay = np.dot(v1, v2)
    bx = np.dot(v1, v2)
    by = np.dot(v2, v2)
    cx = np.dot(v1, v1) / 2
    cy = np.dot(v2, v2) / 2
    det = ax * by - bx * bx
    if abs(det) < 1e-10:
        return np.linspace(start, end, n_segments + 1)

    s = (cx * by - cy * bx) / det
    t = (ax * cy - bx * cx) / det
    center = start + s * v1 + t * v2
    radius = np.linalg.norm(start - center)

    u = (start - center) / np.linalg.norm(start - center)
    v_perp = np.cross(normal, u)

    via_angle = np.arctan2(np.dot(via - center, v_perp), np.dot(via - center, u))
    end_angle = np.arctan2(np.dot(end - center, v_perp), np.dot(end - center, u))

    if via_angle < 0:
        via_angle += 2 * np.pi
    if end_angle < via_angle:
        end_angle += 2 * np.pi

    angles = np.linspace(0.0, end_angle, n_segments + 1)
    points = (
        center[:, np.newaxis]
        + radius * np.cos(angles) * u[:, np.newaxis]
        + radius * np.sin(angles) * v_perp[:, np.newaxis]
    ).T
    return points


def _add_segment(
    buf: list[float], p0: np.ndarray, p1: np.ndarray, color: tuple
) -> None:
    """Append two vertices (start, end) for GL_LINES to buf."""
    buf.extend([*p0, *color, *p1, *color])


def _add_polyline(buf: list[float], pts: np.ndarray, color: tuple) -> None:
    """Append (N-1) line segment pairs for GL_LINES from a polyline array."""
    for i in range(len(pts) - 1):
        buf.extend([*pts[i], *color, *pts[i + 1], *color])


def build_triad_vertices(
    moves: list[MoveInstruction], length: float = 15.0
) -> np.ndarray:
    """Build TCP orientation triad vertices for all Cartesian moves.

    For each move with has_cartesian=True and a valid orient quaternion,
    generates 6 vertices (3 axis lines: R=X, G=Y, B=Z).

    ABB quaternion convention: [q1,q2,q3,q4] = [w,x,y,z]
    pyrr expects: [x,y,z,w]

    Returns shape (N*6, 6) float32, or (0, 6) if empty.
    """
    verts: list[float] = []

    # Axis colors: X=red, Y=green, Z=blue
    axis_colors = [
        (1.0, 0.0, 0.0),  # X axis: red
        (0.0, 1.0, 0.0),  # Y axis: green
        (0.0, 0.0, 1.0),  # Z axis: blue
    ]
    unit_axes = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0]),
    ]

    for move in moves:
        if not move.has_cartesian or move.target is None:
            continue

        pos = move.target.pos.astype(np.float64)
        orient = move.target.orient

        # Convert ABB [w,x,y,z] to pyrr [x,y,z,w]
        pyrr_quat = np.array(
            [orient[1], orient[2], orient[3], orient[0]], dtype=np.float64
        )
        # Normalize to avoid rotation matrix issues
        qlen = np.linalg.norm(pyrr_quat)
        if qlen < 1e-8:
            continue
        pyrr_quat = pyrr_quat / qlen

        rot = pyrr.matrix33.create_from_quaternion(pyrr_quat)

        for axis_vec, color in zip(unit_axes, axis_colors):
            axis_end = pos + rot @ (axis_vec * length)
            # Start vertex: position + color
            verts.extend([*pos, *color])
            # End vertex: axis_end + color
            verts.extend([*axis_end, *color])

    if verts:
        return np.array(verts, dtype=np.float32).reshape(-1, 6)
    return np.empty((0, 6), dtype=np.float32)
