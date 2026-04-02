"""Tests for ModWriter export_mod() -- source text patching engine.

Covers: EXP-01 (all sub-requirements)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rapid_viewer.parser.rapid_parser import parse_module
from rapid_viewer.parser.tokens import MoveInstruction, MoveType, RobTarget
from rapid_viewer.ui.edit_model import EditPoint


FIXTURES = Path(__file__).parent / "fixtures"


def _make_points(source_text: str) -> tuple[str, list[EditPoint], dict[str, RobTarget]]:
    """Parse source text and return (source_text, points, targets)."""
    result = parse_module(source_text)
    points = [EditPoint.from_move(m) for m in result.moves]
    return result.source_text, points, result.targets


class TestUnmodifiedRoundtrip:
    """EXP-01g: Unmodified points produce identical source text."""

    def test_simple_mod(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)
        output = export_mod(source_text, points, targets)
        assert output == source

    def test_offs_mod(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "offs_inline.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)
        output = export_mod(source_text, points, targets)
        assert output == source


class TestNamedTargetPatch:
    """EXP-01a: Named target position patching."""

    def test_patch_named_target_pos(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Modify p10's position (first move uses p10)
        points[0].pos = np.array([999.0, 888.0, 777.0], dtype=np.float64)

        output = export_mod(source_text, points, targets)
        # The robtarget declaration line for p10 should have new values
        assert "999" in output
        assert "888" in output
        assert "777" in output
        # The move line itself should be unchanged
        assert "MoveJ p10" in output


class TestOffsTargetPatch:
    """EXP-01b: Offs() target position patching."""

    def test_patch_offs_target(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "offs_inline.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # points[1] is Offs(pBase, 0, 100, 0) with resolved pos [500, 100, 400]
        # Offset it by (10, 20, 30) -> new pos [510, 120, 430]
        # Delta = [10, 20, 30], so new Offs args = (0+10, 100+20, 0+30) = (10, 120, 30)
        points[1].pos = np.array([510.0, 120.0, 430.0], dtype=np.float64)

        output = export_mod(source_text, points, targets)
        # The Offs() call should have updated numeric args
        assert "Offs(pBase" in output
        # Check that the offset values changed (10, 120, 30)
        assert "10" in output
        assert "120" in output


class TestInlineTargetPatch:
    """EXP-01c: Inline target position patching."""

    def test_patch_inline_target(self):
        from rapid_viewer.export import export_mod

        source = (
            "MODULE InlineTest\n"
            "  PROC main()\n"
            "    MoveL [[100,200,300],[1,0,0,0],[0,0,0,0],"
            "[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]],v100,fine,tool0;\n"
            "  ENDPROC\n"
            "ENDMODULE\n"
        )
        source_text, points, targets = _make_points(source)

        points[0].pos = np.array([999.0, 888.0, 777.0], dtype=np.float64)

        output = export_mod(source_text, points, targets)
        assert "999" in output
        assert "888" in output
        assert "777" in output


class TestSpeedZonePatch:
    """EXP-01c: Speed and zone patching on move lines."""

    def test_patch_speed(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Change speed on second move (MoveL p20, v100, fine, tool0)
        points[1].speed = "v500"

        output = export_mod(source_text, points, targets)
        lines = output.splitlines()
        # Find the MoveL p20 line
        p20_line = [l for l in lines if "p20" in l and "MoveL" in l][0]
        assert "v500" in p20_line
        assert "v100" not in p20_line

    def test_patch_zone(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Change zone on first move (MoveJ p10, v1000, z50, tool0)
        points[0].zone = "z10"

        output = export_mod(source_text, points, targets)
        lines = output.splitlines()
        p10_line = [l for l in lines if "p10" in l and "MoveJ" in l][0]
        assert "z10" in p10_line
        assert "z50" not in p10_line


class TestDeletePatch:
    """EXP-01d: Deleted point commented out."""

    def test_delete_comments_out(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Delete the second point
        points[1].deleted = True

        output = export_mod(source_text, points, targets)
        lines = output.splitlines()
        # The MoveL p20 line should be commented out
        deleted_lines = [l for l in lines if "DELETED" in l]
        assert len(deleted_lines) == 1
        assert "p20" in deleted_lines[0]
        assert deleted_lines[0].strip().startswith("!")


class TestInsertPatch:
    """EXP-01e: Inserted point generates valid RAPID line."""

    def test_insert_generates_line(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Create an inserted point after the first move
        inserted = EditPoint(
            original=points[0].original,
            pos=np.array([550.0, 50.0, 450.0], dtype=np.float64),
            speed="v100",
            zone="fine",
            laser_on=False,
            is_inserted=True,
        )
        # Insert after points[0]
        points.insert(1, inserted)

        output = export_mod(source_text, points, targets)
        lines = output.splitlines()
        # Find the generated MoveL line
        generated = [l for l in lines if "550" in l and "MoveL" in l]
        assert len(generated) == 1
        assert "MoveL" in generated[0]
        assert "v100" in generated[0]
        assert "fine" in generated[0]


class TestPreserveComments:
    """EXP-01g: Comments and non-move lines preserved verbatim."""

    def test_preserves_comments(self):
        from rapid_viewer.export import export_mod

        source = (
            "MODULE CommentTest\n"
            "  ! This is a comment line\n"
            "  CONST robtarget p10 := [[500,0,400],[1,0,0,0],[0,0,0,0],"
            "[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];\n"
            "  PROC main()\n"
            "    ! Another comment\n"
            "    MoveL p10, v100, fine, tool0;\n"
            "  ENDPROC\n"
            "ENDMODULE\n"
        )
        source_text, points, targets = _make_points(source)

        output = export_mod(source_text, points, targets)
        assert "! This is a comment line" in output
        assert "! Another comment" in output


class TestMultilineRobtarget:
    """EXP-01i: Multiline robtarget declaration patching."""

    def test_multiline_robtarget(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "multiline.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Modify pStart's position
        points[0].pos = np.array([999.0, 888.0, 777.0], dtype=np.float64)

        output = export_mod(source_text, points, targets)
        assert "999" in output
        assert "888" in output
        assert "777" in output
        # Other data should be preserved
        assert "0.707107" in output


class TestRoundTrip:
    """EXP-01f: Round-trip parse -> edit -> export -> re-parse."""

    def test_round_trip(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Apply edits: offset first point, change speed on second
        points[0].pos = np.array([510.0, 10.0, 410.0], dtype=np.float64)
        points[1].speed = "v500"

        output = export_mod(source_text, points, targets)

        # Re-parse the output
        result2 = parse_module(output)
        points2 = [EditPoint.from_move(m) for m in result2.moves]

        # Verify changes persisted
        np.testing.assert_allclose(points2[0].pos, [510.0, 10.0, 410.0], atol=0.01)
        assert points2[1].speed == "v500"
        # Unchanged point should be same
        np.testing.assert_allclose(points2[2].pos, [700.0, 200.0, 400.0], atol=0.01)


class TestReversePatchOrder:
    """Verify patches are applied in reverse order to maintain line indices."""

    def test_reverse_patch_order(self):
        from rapid_viewer.export import export_mod

        source = (FIXTURES / "simple.mod").read_text(encoding="utf-8")
        source_text, points, targets = _make_points(source)

        # Edit multiple points on different lines
        points[0].speed = "v2000"  # MoveJ p10 line
        points[1].speed = "v300"   # MoveL p20 line
        points[2].speed = "v400"   # MoveL p30 line

        output = export_mod(source_text, points, targets)

        lines = output.splitlines()
        p10_line = [l for l in lines if "p10" in l and "Move" in l][0]
        p20_line = [l for l in lines if "p20" in l and "Move" in l][0]
        p30_line = [l for l in lines if "p30" in l and "Move" in l][0]

        assert "v2000" in p10_line
        assert "v300" in p20_line
        assert "v400" in p30_line
