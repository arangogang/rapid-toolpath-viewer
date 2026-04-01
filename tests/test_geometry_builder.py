"""Tests for the geometry builder — converts ParseResult into GPU-ready vertex arrays.

Covers: GeometryBuffers shape, arc tessellation, MoveAbsJ exclusion, vertex layout.
"""

import numpy as np
import pytest

from rapid_viewer.parser.tokens import (
    MoveInstruction,
    MoveType,
    ParseResult,
    RobTarget,
    JointTarget,
)
from rapid_viewer.renderer.geometry_builder import (
    GeometryBuffers,
    build_geometry,
    tessellate_arc,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_robtarget(name: str, pos: tuple[float, float, float], line: int = 1) -> RobTarget:
    """Create a minimal RobTarget for testing."""
    return RobTarget(
        name=name,
        pos=np.array(pos, dtype=np.float64),
        orient=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
        confdata=(0, 0, 0, 0),
        extjoint=(9e9,) * 6,
        source_line=line,
    )


def _make_move(
    move_type: MoveType,
    pos: tuple[float, float, float] | None = None,
    name: str = "pt",
    circle_pos: tuple[float, float, float] | None = None,
    has_cartesian: bool = True,
    line: int = 1,
) -> MoveInstruction:
    """Create a minimal MoveInstruction for testing."""
    target = _make_robtarget(name, pos, line) if pos is not None else None
    circle_point = _make_robtarget(f"{name}_cir", circle_pos, line) if circle_pos else None
    joint_target = None
    if not has_cartesian:
        joint_target = JointTarget(
            name="jt1", robax=(0.0,) * 6, extax=(9e9,) * 6, source_line=line
        )
    return MoveInstruction(
        move_type=move_type,
        target=target,
        circle_point=circle_point,
        joint_target=joint_target,
        speed="v100",
        zone="fine",
        tool="tool0",
        wobj="wobj0",
        source_line=line,
        has_cartesian=has_cartesian,
    )


def _make_parse_result(moves: list[MoveInstruction]) -> ParseResult:
    """Wrap moves in a minimal ParseResult."""
    return ParseResult(
        module_name="TestModule",
        moves=moves,
        targets={},
        joint_targets={},
        source_text="",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_empty_parse_result():
    """build_geometry with no moves returns all arrays shape (0, 6)."""
    result = _make_parse_result([])
    buffers = build_geometry(result)
    assert buffers.solid_verts.shape == (0, 6)
    assert buffers.dashed_verts.shape == (0, 6)
    assert buffers.marker_verts.shape == (0, 6)


def test_movel_produces_solid_segment():
    """Two MoveL moves produce a solid line segment (2 verts) and 2 markers."""
    moves = [
        _make_move(MoveType.MOVEL, (0, 0, 0), name="p1"),
        _make_move(MoveType.MOVEL, (100, 0, 0), name="p2"),
    ]
    buffers = build_geometry(_make_parse_result(moves))
    # One segment = 2 vertices in solid_verts (GL_LINES)
    assert buffers.solid_verts.shape[0] == 2
    assert buffers.dashed_verts.shape == (0, 6)
    # Markers at each Cartesian waypoint
    assert buffers.marker_verts.shape[0] == 2


def test_movej_produces_dashed_segment():
    """Two MoveJ moves produce a dashed line segment, no solid segments."""
    moves = [
        _make_move(MoveType.MOVEJ, (0, 0, 0), name="p1"),
        _make_move(MoveType.MOVEJ, (100, 0, 0), name="p2"),
    ]
    buffers = build_geometry(_make_parse_result(moves))
    assert buffers.dashed_verts.shape[0] == 2
    assert buffers.solid_verts.shape == (0, 6)


def test_moveabsj_skipped():
    """MoveAbsJ (has_cartesian=False, target=None) produces no geometry."""
    moves = [
        _make_move(MoveType.MOVEABSJ, pos=None, has_cartesian=False),
    ]
    buffers = build_geometry(_make_parse_result(moves))
    assert buffers.solid_verts.shape == (0, 6)
    assert buffers.dashed_verts.shape == (0, 6)
    assert buffers.marker_verts.shape == (0, 6)


def test_movec_tessellates_arc():
    """MoveC with valid start/via/end produces arc polyline in solid_verts."""
    moves = [
        # Start position (MoveL to establish prev_pos)
        _make_move(MoveType.MOVEL, (100, 0, 0), name="start"),
        # Arc: start=(100,0,0), via=(50,50,0), end=(0,100,0)
        _make_move(
            MoveType.MOVEC,
            pos=(0, 100, 0),
            name="arc_end",
            circle_pos=(50, 50, 0),
        ),
    ]
    buffers = build_geometry(_make_parse_result(moves), arc_segments=32)
    # Arc tessellated to 32 segments = 32 line pairs = 64 verts
    # Plus markers. solid_verts includes the arc polyline (>=32 pairs)
    assert buffers.solid_verts.shape[0] >= 32


def test_arc_collinear_fallback():
    """tessellate_arc with collinear points returns (n_segments+1, 3), no crash."""
    start = np.array([0.0, 0.0, 0.0])
    via = np.array([50.0, 0.0, 0.0])  # collinear
    end = np.array([100.0, 0.0, 0.0])
    result = tessellate_arc(start, via, end, n_segments=16)
    assert result.shape == (17, 3)  # n_segments + 1


def test_vertex_layout_dtype():
    """All GeometryBuffers arrays are float32 with shape (N, 6) or (0, 6)."""
    moves = [
        _make_move(MoveType.MOVEL, (0, 0, 0)),
        _make_move(MoveType.MOVEL, (1, 1, 1)),
    ]
    buffers = build_geometry(_make_parse_result(moves))
    for arr in [buffers.solid_verts, buffers.dashed_verts, buffers.marker_verts]:
        assert arr.dtype == np.float32
        assert arr.ndim == 2
        assert arr.shape[1] == 6


def test_marker_at_every_cartesian_waypoint():
    """3 MoveL moves produce 3 markers (one per Cartesian waypoint)."""
    moves = [
        _make_move(MoveType.MOVEL, (0, 0, 0), name="p1"),
        _make_move(MoveType.MOVEL, (10, 0, 0), name="p2"),
        _make_move(MoveType.MOVEL, (20, 0, 0), name="p3"),
    ]
    buffers = build_geometry(_make_parse_result(moves))
    assert buffers.marker_verts.shape[0] == 3
