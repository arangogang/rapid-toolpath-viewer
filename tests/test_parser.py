"""Test stubs for the RAPID .mod file parser.

All tests are skipped (red state) until the parser is implemented in Plan 02.
Each stub documents its requirement ID and expected behavior contract.
"""

import pytest

from rapid_viewer.parser.tokens import MoveType, RobTarget, MoveInstruction, ParseResult


# ---------------------------------------------------------------------------
# Move instruction parsing
# ---------------------------------------------------------------------------


def test_parse_movel(simple_mod):
    """PARS-01: MoveL parsing -- asserts MoveL instructions found with correct target refs."""
    pytest.skip("Parser not implemented yet")
    # Expected: ParseResult.moves contains MoveInstruction(move_type=MoveType.MOVEL)
    # with target.name == "p20" and speed == "v100" and zone == "fine"


def test_parse_movej(simple_mod):
    """PARS-02: MoveJ parsing -- asserts MoveJ instruction found."""
    pytest.skip("Parser not implemented yet")
    # Expected: ParseResult.moves contains MoveInstruction(move_type=MoveType.MOVEJ)
    # with target.name == "p10" and speed == "v1000" and zone == "z50"


def test_parse_movec(movec_mod):
    """PARS-03: MoveC parsing -- asserts MoveC found with both circle_point and target populated."""
    pytest.skip("Parser not implemented yet")
    # Expected: MoveInstruction with move_type=MoveType.MOVEC,
    # circle_point.name == "pCirPoint", target.name == "pCirEnd"


def test_parse_moveabsj(moveabsj_mod):
    """PARS-04: MoveAbsJ parsing -- asserts MoveAbsJ found with has_cartesian=False and joint_target populated."""
    pytest.skip("Parser not implemented yet")
    # Expected: MoveInstruction with move_type=MoveType.MOVEABSJ,
    # has_cartesian=False, joint_target.name == "jHome", target is None


# ---------------------------------------------------------------------------
# Target declaration parsing
# ---------------------------------------------------------------------------


def test_parse_robtarget(simple_mod):
    """PARS-05: robtarget parsing -- asserts robtarget pos/orient extracted with correct values."""
    pytest.skip("Parser not implemented yet")
    # Expected: ParseResult.targets["p10"].pos == [500, 0, 400]
    # and ParseResult.targets["p10"].orient == [1, 0, 0, 0]


def test_multiline_robtarget(multiline_mod):
    """PARS-06: Multiline robtarget -- asserts multiline robtarget parsed with correct position values."""
    pytest.skip("Parser not implemented yet")
    # Expected: ParseResult.targets["pStart"].pos == [100.5, 200.3, 300.1]
    # Declaration spans 5 lines; semicolon-based tokenizer must handle this


def test_line_numbers(simple_mod):
    """PARS-07: Source line numbers -- asserts each MoveInstruction has correct source_line."""
    pytest.skip("Parser not implemented yet")
    # Expected: MoveJ on line 7, MoveL p20 on line 8, MoveL p30 on line 9
    # (1-indexed, matching text editor line display)


# ---------------------------------------------------------------------------
# Offs() and optional parameter parsing
# ---------------------------------------------------------------------------


def test_offs_resolution(offs_mod):
    """Offs() resolution -- target resolved with offset applied to base position."""
    pytest.skip("Parser not implemented yet")
    # Expected: Second MoveL has target with pos == [500, 100, 400]  (pBase + [0, 100, 0])
    # Third MoveL has target with pos == [500, 200, 450]  (pBase + [0, 200, 50])
    # Orientation must remain unchanged from pBase


def test_wobj_capture(simple_mod):
    """wobj capture -- asserts wobj field captured when \\WObj parameter present."""
    pytest.skip("Parser not implemented yet")
    # Expected: Third MoveL (MoveL p30 ... \WObj:=wobj0) has move.wobj == "wobj0"
    # First two MoveL/MoveJ have move.wobj == "wobj0" (default)


# ---------------------------------------------------------------------------
# Module-level metadata
# ---------------------------------------------------------------------------


def test_module_name_extracted(simple_mod):
    """Module name extraction -- asserts ParseResult.module_name == 'SimpleTest'."""
    pytest.skip("Parser not implemented yet")
    # Expected: ParseResult.module_name == "SimpleTest"


def test_procedures_found(simple_mod):
    """Procedure discovery -- asserts 'main' in ParseResult.procedures."""
    pytest.skip("Parser not implemented yet")
    # Expected: "main" in ParseResult.procedures
    # Parser must track all PROC names encountered during parsing
