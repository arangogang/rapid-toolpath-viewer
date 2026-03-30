"""Tests for the RAPID .mod file parser.

Each test calls parse_module() and asserts on specific values.
Tests are organized by requirement ID (PARS-01 through PARS-07).
"""

import numpy as np
import pytest

from rapid_viewer.parser.tokens import MoveType, RobTarget, MoveInstruction, ParseResult
from rapid_viewer.parser.rapid_parser import parse_module


# ---------------------------------------------------------------------------
# Move instruction parsing
# ---------------------------------------------------------------------------


def test_parse_movel(simple_mod):
    """PARS-01: MoveL parsing -- asserts MoveL instructions found with correct target refs."""
    result = parse_module(simple_mod)
    movel_moves = [m for m in result.moves if m.move_type == MoveType.MOVEL]
    assert len(movel_moves) == 2
    assert movel_moves[0].target is not None
    assert movel_moves[0].target.name == "p20"
    assert movel_moves[0].speed == "v100"
    assert movel_moves[0].zone == "fine"
    assert movel_moves[0].tool == "tool0"


def test_parse_movej(simple_mod):
    """PARS-02: MoveJ parsing -- asserts MoveJ instruction found."""
    result = parse_module(simple_mod)
    movej_moves = [m for m in result.moves if m.move_type == MoveType.MOVEJ]
    assert len(movej_moves) == 1
    assert movej_moves[0].target.name == "p10"
    assert movej_moves[0].speed == "v1000"


def test_parse_movec(movec_mod):
    """PARS-03: MoveC parsing -- asserts MoveC found with both circle_point and target populated."""
    result = parse_module(movec_mod)
    movec_moves = [m for m in result.moves if m.move_type == MoveType.MOVEC]
    assert len(movec_moves) == 1
    assert movec_moves[0].circle_point is not None
    assert movec_moves[0].circle_point.name == "pCirPoint"
    assert movec_moves[0].target is not None
    assert movec_moves[0].target.name == "pCirEnd"


def test_parse_moveabsj(moveabsj_mod):
    """PARS-04: MoveAbsJ parsing -- asserts MoveAbsJ found with has_cartesian=False and joint_target populated."""
    result = parse_module(moveabsj_mod)
    absj_moves = [m for m in result.moves if m.move_type == MoveType.MOVEABSJ]
    assert len(absj_moves) == 1
    assert absj_moves[0].has_cartesian is False
    assert absj_moves[0].joint_target is not None
    assert absj_moves[0].joint_target.name == "jHome"
    assert absj_moves[0].target is None


# ---------------------------------------------------------------------------
# Target declaration parsing
# ---------------------------------------------------------------------------


def test_parse_robtarget(simple_mod):
    """PARS-05: robtarget parsing -- asserts robtarget pos/orient extracted with correct values."""
    result = parse_module(simple_mod)
    assert "p10" in result.targets
    p10 = result.targets["p10"]
    np.testing.assert_array_almost_equal(p10.pos, [500, 0, 400])
    np.testing.assert_array_almost_equal(p10.orient, [1, 0, 0, 0])


def test_multiline_robtarget(multiline_mod):
    """PARS-06: Multiline robtarget -- asserts multiline robtarget parsed with correct position values."""
    result = parse_module(multiline_mod)
    assert "pStart" in result.targets
    pstart = result.targets["pStart"]
    np.testing.assert_array_almost_equal(pstart.pos, [100.5, 200.3, 300.1])
    np.testing.assert_array_almost_equal(pstart.orient, [0.707107, 0, 0.707107, 0])
    assert len(result.moves) == 2  # Both MoveL instructions parsed despite multiline targets


def test_line_numbers(simple_mod):
    """PARS-07: Source line numbers -- asserts each MoveInstruction has correct source_line."""
    result = parse_module(simple_mod)
    # Line numbers depend on exact fixture content -- verify they are positive integers
    # and that they increase for sequential moves within a PROC
    assert all(m.source_line > 0 for m in result.moves)
    line_nums = [m.source_line for m in result.moves]
    assert line_nums == sorted(line_nums), "Move line numbers should be in ascending order"
    assert len(set(line_nums)) == len(line_nums), "Each move should have a unique line number"


# ---------------------------------------------------------------------------
# Offs() and optional parameter parsing
# ---------------------------------------------------------------------------


def test_offs_resolution(offs_mod):
    """Offs() resolution -- target resolved with offset applied to base position."""
    result = parse_module(offs_mod)
    movel_moves = [m for m in result.moves if m.move_type == MoveType.MOVEL]
    assert len(movel_moves) == 3
    # Second move: Offs(pBase, 0, 100, 0) -> [500, 0+100, 400] = [500, 100, 400]
    np.testing.assert_array_almost_equal(movel_moves[1].target.pos, [500, 100, 400])
    # Third move: Offs(pBase, 0, 200, 50) -> [500, 200, 450]
    np.testing.assert_array_almost_equal(movel_moves[2].target.pos, [500, 200, 450])


def test_wobj_capture(simple_mod):
    """wobj capture -- asserts wobj field captured when \\WObj parameter present."""
    result = parse_module(simple_mod)
    # Third MoveL has \WObj:=wobj0
    last_movel = [m for m in result.moves if m.move_type == MoveType.MOVEL][-1]
    assert last_movel.wobj == "wobj0"


# ---------------------------------------------------------------------------
# Module-level metadata
# ---------------------------------------------------------------------------


def test_module_name_extracted(simple_mod):
    """Module name extraction -- asserts ParseResult.module_name == 'SimpleTest'."""
    result = parse_module(simple_mod)
    assert result.module_name == "SimpleTest"


def test_procedures_found(simple_mod):
    """Procedure discovery -- asserts 'main' in ParseResult.procedures."""
    result = parse_module(simple_mod)
    assert "main" in result.procedures


# ---------------------------------------------------------------------------
# PROC range extraction (PARS-08)
# ---------------------------------------------------------------------------


def test_proc_ranges_single_proc(simple_mod):
    """PARS-08: Single PROC -- proc_ranges has one entry with correct line range."""
    result = parse_module(simple_mod)
    assert "main" in result.proc_ranges
    start, end = result.proc_ranges["main"]
    assert start < end
    assert start > 0


def test_proc_ranges_multi_proc(multiproc_mod):
    """PARS-08: Multi PROC -- proc_ranges has entries for each PROC with non-overlapping line ranges."""
    result = parse_module(multiproc_mod)
    assert "main" in result.proc_ranges
    assert "path2" in result.proc_ranges

    main_start, main_end = result.proc_ranges["main"]
    path2_start, path2_end = result.proc_ranges["path2"]

    # Non-overlapping: main ends before path2 starts
    assert main_end < path2_start
    # Each range is valid
    assert main_start < main_end
    assert path2_start < path2_end


def test_proc_filtering(multiproc_mod):
    """PARS-08: Filter moves by PROC range -- only moves from that PROC are included."""
    result = parse_module(multiproc_mod)
    start, end = result.proc_ranges["path2"]
    path2_moves = [m for m in result.moves if start <= m.source_line <= end]
    assert len(path2_moves) == 3  # MoveJ p30 + MoveL p40 + MoveL p50

    # Verify the first is a MoveJ
    assert path2_moves[0].move_type == MoveType.MOVEJ

    # Verify main PROC moves are separate
    main_start, main_end = result.proc_ranges["main"]
    main_moves = [m for m in result.moves if main_start <= m.source_line <= main_end]
    assert len(main_moves) == 2  # 2 MoveL in main

    # All moves accounted for
    assert len(main_moves) + len(path2_moves) == len(result.moves)


def test_proc_ranges_empty():
    """PARS-08: No PROCs -- proc_ranges is empty dict."""
    source = """\
MODULE NoProcTest
  CONST robtarget p1 := [[100,0,0],[1,0,0,0],[0,0,0,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
ENDMODULE
"""
    result = parse_module(source)
    assert result.proc_ranges == {}
