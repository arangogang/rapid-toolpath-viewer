"""Source text patching engine for .mod export.

Transforms EditModel mutations back into valid RAPID source text
while preserving all original formatting, comments, and non-move code.

Public API:
    export_mod(source_text, points, targets) -> str
"""

from __future__ import annotations

import re
from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from rapid_viewer.parser.tokens import RobTarget
    from rapid_viewer.ui.edit_model import EditPoint


class _PatchAction(Enum):
    """Type of line-level patch."""

    REPLACE = auto()
    DELETE = auto()
    INSERT_AFTER = auto()


def _fmt(val: float) -> str:
    """Format a float for RAPID output."""
    return f"{val:.6g}"


def _patch_robtarget_pos(
    lines: list[str], start_line_idx: int, new_pos: np.ndarray
) -> None:
    """Patch a (possibly multiline) robtarget declaration's position bracket group.

    Finds the extent by scanning forward from start_line_idx until a line
    containing ';' is found. Joins the extent into one string, regex-replaces
    the first [[x,y,z] bracket group with new values, then splits back.
    """
    # Find extent: from start_line_idx to the first line containing ';'
    end_idx = start_line_idx
    for i in range(start_line_idx, len(lines)):
        if ";" in lines[i]:
            end_idx = i
            break

    # Join the extent into one string
    extent_lines = lines[start_line_idx : end_idx + 1]
    joined = "\n".join(extent_lines)

    # Replace the first [[x,y,z] group
    # Pattern matches [[ then numbers separated by commas, then ]
    pattern = r"(\[\[)\s*" + r"[^\]]+?" + r"(\])"
    new_vals = f"{_fmt(new_pos[0])},{_fmt(new_pos[1])},{_fmt(new_pos[2])}"

    def _replacer(m: re.Match) -> str:
        return f"{m.group(1)}{new_vals}{m.group(2)}"

    patched = re.sub(pattern, _replacer, joined, count=1)

    # Split back and replace in lines
    new_extent = patched.split("\n")
    lines[start_line_idx : end_idx + 1] = new_extent


def _patch_offs_args(line: str, delta: np.ndarray, original_line: str) -> str:
    """Parse the Offs() call, add delta to numeric args, return patched line.

    Preserves variable args (like zLayer) unchanged.
    """
    # Find Offs(...) in the line
    offs_pattern = r"(Offs\s*\(\s*\w+\s*,\s*)([^)]+)(\))"
    m = re.search(offs_pattern, line, re.IGNORECASE)
    if m is None:
        return line

    # Also find the original Offs() args from original_line
    m_orig = re.search(offs_pattern, original_line, re.IGNORECASE)
    if m_orig is None:
        return line

    orig_args_str = m_orig.group(2)
    orig_args = [a.strip() for a in orig_args_str.split(",")]

    # Apply delta to numeric args, preserve variable args
    new_args = []
    for i, arg in enumerate(orig_args):
        if i < 3:  # x, y, z offsets
            try:
                val = float(arg)
                val += delta[i]
                new_args.append(_fmt(val))
            except ValueError:
                # Variable arg (e.g., zLayer) -- preserve as-is
                new_args.append(arg)
        else:
            new_args.append(arg)

    new_args_str = ", ".join(new_args)
    return line[: m.start(2)] + new_args_str + line[m.end(2) :]


def _patch_inline_pos(line: str, new_pos: np.ndarray) -> str:
    """Regex-replace the first [[x,y,z] in a move line with inline target data."""
    pattern = r"(\[\[)\s*[^\]]+?(\])"
    new_vals = f"{_fmt(new_pos[0])},{_fmt(new_pos[1])},{_fmt(new_pos[2])}"

    def _replacer(m: re.Match) -> str:
        return f"{m.group(1)}{new_vals}{m.group(2)}"

    return re.sub(pattern, _replacer, line, count=1)


def _patch_speed_zone(
    line: str, new_speed: str | None, new_zone: str | None
) -> str:
    """Replace speed and/or zone tokens in a move instruction line.

    The move line pattern is: MoveX target, speed, zone, tool [\\WObj:=wobj];
    The target may contain commas inside brackets, so we need to handle that.
    """
    # Strategy: find the move keyword, then work backwards from the semicolon
    # or end of line to find tool, zone, speed, target
    # Pattern: find the last three comma-separated tokens before optional \WObj and ;
    # Use a greedy approach: MoveX <target>, <speed>, <zone>, <tool> [\WObj:=...]
    # Where target can contain brackets with commas inside

    # Find the Move keyword position
    move_match = re.search(r"(Move\w+)\s+", line, re.IGNORECASE)
    if move_match is None:
        return line

    # Get everything after the Move keyword
    after_move = line[move_match.end() :]

    # We need to find the target (which may have brackets with commas),
    # then speed, zone, tool
    # Strategy: track bracket depth to skip commas inside brackets
    depth = 0
    comma_positions = []
    for i, ch in enumerate(after_move):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        elif ch == "," and depth == 0:
            comma_positions.append(i)
        elif ch == "\\" or ch == ";":
            # Stop before optional params or semicolon
            break

    # We expect at least 3 commas: target,speed,zone,tool
    if len(comma_positions) < 3:
        return line

    # Extract token positions relative to after_move
    # speed is between comma_positions[0] and comma_positions[1]
    # zone is between comma_positions[1] and comma_positions[2]
    speed_start = comma_positions[-3] + 1
    speed_end = comma_positions[-2]
    zone_start = comma_positions[-2] + 1
    zone_end = comma_positions[-1]

    speed_token = after_move[speed_start:speed_end].strip()
    zone_token = after_move[zone_start:zone_end].strip()

    result = line
    offset = move_match.end()

    if new_zone is not None and new_zone != zone_token:
        # Replace zone
        abs_start = offset + zone_start
        abs_end = offset + zone_end
        # Preserve whitespace around the token
        orig_segment = result[abs_start:abs_end]
        new_segment = orig_segment.replace(zone_token, new_zone, 1)
        result = result[:abs_start] + new_segment + result[abs_end:]

    if new_speed is not None and new_speed != speed_token:
        # Replace speed
        abs_start = offset + speed_start
        abs_end = offset + speed_end
        orig_segment = result[abs_start:abs_end]
        new_segment = orig_segment.replace(speed_token, new_speed, 1)
        result = result[:abs_start] + new_segment + result[abs_end:]

    return result


def _generate_move_line(point: EditPoint, indent: str = "    ") -> str:
    """Generate a RAPID MoveL line with inline robtarget for inserted points."""
    move = point.original
    pos = point.pos
    orient = move.target.orient if move.target else np.array([1, 0, 0, 0], dtype=np.float64)
    confdata = move.target.confdata if move.target else (0, 0, 0, 0)
    extjoint = move.target.extjoint if move.target else (9e9,) * 6

    pos_str = f"{_fmt(pos[0])},{_fmt(pos[1])},{_fmt(pos[2])}"
    orient_str = ",".join(_fmt(v) for v in orient)
    conf_str = ",".join(str(v) for v in confdata)
    ext_str = ",".join(_fmt(v) for v in extjoint)

    target_str = f"[[{pos_str}],[{orient_str}],[{conf_str}],[{ext_str}]]"

    wobj_str = f" \\WObj:={move.wobj}" if move.wobj != "wobj0" else ""

    return f"{indent}MoveL {target_str},{point.speed},{point.zone},{move.tool}{wobj_str};"


def export_mod(
    source_text: str,
    points: list[EditPoint],
    targets: dict[str, RobTarget],
) -> str:
    """Patch source text with EditModel changes and return the result.

    Algorithm:
    1. Split source_text into lines
    2. Build patch list by comparing each EditPoint against its original
    3. Sort patches by line number descending (reverse order)
    4. Apply patches to lines array
    5. Join and return

    Args:
        source_text: Original .mod file source text.
        points: List of EditPoints from EditModel (may include inserted/deleted).
        targets: Dict of named RobTargets from ParseResult.

    Returns:
        Patched source text string.
    """
    lines = source_text.split("\n")
    # Track trailing newline
    has_trailing_newline = source_text.endswith("\n")
    if has_trailing_newline and lines and lines[-1] == "":
        lines = lines[:-1]

    # Build patch list: (line_index, action, content_or_callback)
    # line_index is 0-based
    patches: list[tuple[int, _PatchAction, str | None]] = []
    patched_target_lines: set[int] = set()  # track already-patched robtarget declarations

    for point in points:
        orig = point.original
        source_line_idx = orig.source_line - 1  # convert 1-indexed to 0-indexed

        if point.is_inserted:
            # Generate a new MoveL line and insert after the source line
            # Detect indentation from the source line
            if 0 <= source_line_idx < len(lines):
                src_line = lines[source_line_idx]
                indent = src_line[: len(src_line) - len(src_line.lstrip())]
            else:
                indent = "    "
            new_line = _generate_move_line(point, indent)
            patches.append((source_line_idx, _PatchAction.INSERT_AFTER, new_line))
            continue

        if point.deleted:
            # Comment out the move instruction line
            if 0 <= source_line_idx < len(lines):
                original_line = lines[source_line_idx]
                indent = original_line[: len(original_line) - len(original_line.lstrip())]
                commented = f"{indent}! [DELETED] {original_line.strip()}"
                patches.append(
                    (source_line_idx, _PatchAction.REPLACE, commented)
                )
            continue

        if orig.target is None:
            # MoveAbsJ -- no Cartesian target to patch
            continue

        # Check position changes
        pos_changed = not np.array_equal(point.pos, orig.target.pos)
        speed_changed = point.speed != orig.speed
        zone_changed = point.zone != orig.zone

        if pos_changed:
            target_name = orig.target.name

            if target_name == "<inline>":
                # Inline target: patch the move line
                if 0 <= source_line_idx < len(lines):
                    patched_line = _patch_inline_pos(
                        lines[source_line_idx], point.pos
                    )
                    patches.append(
                        (source_line_idx, _PatchAction.REPLACE, patched_line)
                    )

            elif target_name.startswith("Offs("):
                # Offs() target: compute delta and patch the move line
                delta = point.pos - orig.target.pos
                if 0 <= source_line_idx < len(lines):
                    patched_line = _patch_offs_args(
                        lines[source_line_idx], delta, lines[source_line_idx]
                    )
                    patches.append(
                        (source_line_idx, _PatchAction.REPLACE, patched_line)
                    )

            else:
                # Named target: patch the robtarget declaration line
                if target_name in targets:
                    decl_line = targets[target_name].source_line
                    decl_line_idx = decl_line - 1  # 0-indexed
                    if decl_line_idx not in patched_target_lines:
                        patched_target_lines.add(decl_line_idx)
                        # Will apply as a special multiline patch
                        # Use a sentinel to mark this as a robtarget pos patch
                        patches.append(
                            (
                                decl_line_idx,
                                _PatchAction.REPLACE,
                                f"__ROBTARGET_POS__{point.pos[0]},{point.pos[1]},{point.pos[2]}",
                            )
                        )

        if speed_changed or zone_changed:
            new_speed = point.speed if speed_changed else None
            new_zone = point.zone if zone_changed else None
            if 0 <= source_line_idx < len(lines):
                # Check if we already have a REPLACE patch for this line
                existing = [
                    i for i, (li, _, _) in enumerate(patches) if li == source_line_idx
                ]
                if existing:
                    # Apply speed/zone patch to the already-patched content
                    idx = existing[-1]
                    _, act, content = patches[idx]
                    if act == _PatchAction.REPLACE and content is not None:
                        if not content.startswith("__ROBTARGET_POS__"):
                            patched = _patch_speed_zone(content, new_speed, new_zone)
                            patches[idx] = (source_line_idx, act, patched)
                        else:
                            # Target declaration patch + speed/zone on move line
                            # Need a separate patch for the move line
                            patched_move = _patch_speed_zone(
                                lines[source_line_idx], new_speed, new_zone
                            )
                            patches.append(
                                (
                                    source_line_idx,
                                    _PatchAction.REPLACE,
                                    patched_move,
                                )
                            )
                else:
                    patched_line = _patch_speed_zone(
                        lines[source_line_idx], new_speed, new_zone
                    )
                    patches.append(
                        (source_line_idx, _PatchAction.REPLACE, patched_line)
                    )

    # Sort patches by line index DESCENDING so that applying them
    # from bottom to top preserves line indices
    patches.sort(key=lambda p: p[0], reverse=True)

    # Apply patches
    for line_idx, action, content in patches:
        if action == _PatchAction.REPLACE:
            if content is not None and content.startswith("__ROBTARGET_POS__"):
                # Special robtarget position patch
                vals_str = content[len("__ROBTARGET_POS__") :]
                vals = [float(v) for v in vals_str.split(",")]
                new_pos = np.array(vals, dtype=np.float64)
                _patch_robtarget_pos(lines, line_idx, new_pos)
            elif content is not None:
                lines[line_idx] = content

        elif action == _PatchAction.DELETE:
            # Remove the line
            del lines[line_idx]

        elif action == _PatchAction.INSERT_AFTER:
            if content is not None:
                lines.insert(line_idx + 1, content)

    result = "\n".join(lines)
    if has_trailing_newline:
        result += "\n"
    return result
