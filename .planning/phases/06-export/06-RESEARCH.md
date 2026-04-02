# Phase 6: Export - Research

**Researched:** 2026-04-02
**Domain:** Source text patching / .mod file export
**Confidence:** HIGH

## Summary

Phase 6 implements "Save As" (Ctrl+Shift+S) to export a modified .mod file. The locked strategy is **source text patching** -- never regeneration. This means the original `ParseResult.source_text` is the base, and only lines that correspond to edited/deleted/inserted moves are modified. Everything else (comments, IF/WHILE logic, PROC structure, formatting, whitespace) passes through untouched.

The core technical challenge is mapping EditModel mutations back to specific character ranges in the original source text. Each `EditPoint` has an `original.source_line` (1-indexed) that identifies where in the source the move instruction lives. For position changes on **named targets**, the robtarget declaration line (not the move line) must be patched. For **Offs() targets**, new offset values must be computed relative to the base target. For **speed/zone** changes, the move instruction line itself is patched. **Deleted** points have their source lines removed. **Inserted** points require generating new RAPID code lines after the source point's line.

**Primary recommendation:** Build a `ModWriter` class in `src/rapid_viewer/export/mod_writer.py` that takes `ParseResult.source_text` and the `EditModel._points` list, computes a diff of line-level patches (replace, delete, insert-after), and applies them in reverse line order to produce the output text. Keep the writer as a pure function (no Qt dependency) for easy testing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXP-01 | Save modified .mod file as new name, preserving original format/comments via source text patching | ModWriter source-patching architecture, line-level diff approach, all edit type coverage (offset, speed/zone/laser, delete, insert) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech Stack**: Python + PyQt6 + PyOpenGL
- **Platform**: Windows desktop only
- **Scope**: Viewer with editing -- no simulation
- **Conventions**: `from __future__ import annotations` in all modules, ruff line-length 100, frozen dataclasses for immutable data, type hints on all public APIs
- **Testing**: pytest with tests organized by requirement ID, shared fixtures in conftest.py
- **Error handling**: QMessageBox for user-facing errors, minimal try/except
- **Out of scope**: Overwriting original file (Save As only)
- **GSD Workflow**: Must use GSD commands for file changes

## Architecture Patterns

### Recommended Project Structure
```
src/rapid_viewer/
  export/
    __init__.py          # re-export mod_writer public API
    mod_writer.py        # ModWriter: source text patching logic
  ui/
    main_window.py       # Add Save As menu action + handler
```

### Pattern 1: Line-Level Source Text Patching
**What:** Split source_text into lines, compute patches per line, apply patches in reverse order (highest line number first to preserve indices), join back into string.
**When to use:** Always -- this is the locked export strategy.

**Algorithm:**
1. Iterate all `EditPoint`s in `EditModel._points`
2. For each point, compare against `point.original` to detect what changed
3. Build a patch list: `list[Patch]` where Patch = `(line_number, action, new_content)`
   - `action` is one of: REPLACE, DELETE, INSERT_AFTER
4. Sort patches by line_number descending (so line indices remain valid during application)
5. Apply patches to the lines array
6. Join and return

### Pattern 2: Edit Type Detection and Line Patching

There are 6 distinct edit types that need different patching strategies:

**A. Position offset (named target):**
- EditPoint.pos differs from original.target.pos
- Target name is not `<inline>` and not `Offs(...)`
- Action: Find the robtarget declaration line (original.target.source_line), regex-replace the `[x,y,z]` bracket group with new values
- Concern: Multiple moves may reference the same named target. If two moves reference `p10` and only one was offset, we have a conflict. In practice, EditModel applies offset to the EditPoint's pos directly, so each move gets its own copy. For export, if a named target is shared, the writer must decide. The simplest approach: if a named target was modified, update the declaration to match the FIRST reference. If multiple moves reference the same target with DIFFERENT edits, this is a user error the tool does not guard against. Document this limitation.

**B. Position offset (Offs() target):**
- Target name starts with `Offs(`
- The original source line has `Offs(baseName, dx, dy, dz)`
- New offset values = point.pos - base_target.pos (requires access to the base target from ParseResult.targets)
- Action: regex-replace the Offs() arguments on the move instruction line

**C. Position offset (inline target):**
- Target name is `<inline>`
- The original source line has `[[x,y,z],[q1,q2,q3,q4],...]` directly
- Action: regex-replace the first bracket group `[x,y,z]` in the inline data

**D. Speed/zone change:**
- EditPoint.speed != original.speed or EditPoint.zone != original.zone
- Action: regex-replace in the move instruction line. The move line pattern is: `MoveL target, speed, zone, tool`
- Use regex to find and replace the speed/zone tokens

**E. Laser on/off change:**
- EditPoint.laser_on != original.laser_on
- Action: Insert or remove a `SetDO signal, 1/0;` line before the move line
- This is complex because the laser state is tracked as a running state machine in the parser. For simplicity: if laser_on changed, insert a `SetDO` line before the move. If the original had a SetDO before it, modify that line instead.
- Alternative simpler approach: Do NOT patch SetDO lines. Laser on/off is a visual-only property in the viewer and may not map cleanly to SetDO signals. Document this as a limitation and defer SetDO patching to a future version. The exported file preserves original SetDO lines as-is.

**F. Deleted point:**
- EditPoint.deleted == True
- Action: Remove the source line (the move instruction line). Comment it out with `!` prefix for safety, or remove entirely.
- Recommendation: Comment out with `! [DELETED] ` prefix -- safer and preserves original content for reference.

**G. Inserted point:**
- EditPoint where original.source_line matches another point's source_line AND it's a different object (inserted copy)
- Detection: Inserted points share `original` with their source point. We can detect them because they won't be the "first" point for a given source_line.
- Action: Generate a new MoveL/MoveJ line with inline robtarget data and insert after the source line
- Generated line format: `    MoveL [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax]], speed, zone, tool \WObj:=wobj;`

### Pattern 3: Identifying Inserted vs Edited Points

The key challenge is distinguishing "edited existing point" from "inserted new point" because InsertPointCommand sets `original` to the source point's MoveInstruction. Two approaches:

**Approach A (Recommended): Add `is_inserted` flag to EditPoint.**
Add `is_inserted: bool = False` to EditPoint dataclass. Set it True in InsertPointCommand. This is the cleanest and most explicit approach.

**Approach B: Compare identity.**
An inserted point shares the same `original` object as another point. But after undo/redo cycles this identity check may be fragile.

Use Approach A.

### Anti-Patterns to Avoid
- **Full regeneration:** Never regenerate the entire .mod file from parsed data. Comments, formatting, non-move code would be lost.
- **In-place file modification:** Never overwrite the original file. Always use Save As to a new path.
- **String concatenation for line building:** Use f-strings with consistent formatting, but test against real ABB controller expectations.
- **Modifying lines by character offset:** Work at the line level (split by `\n`), not character offset level. Line-level patching is simpler and safer.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Number formatting | Custom float-to-string | Python f-string `f"{val:.6g}"` or `f"{val}"` | ABB RAPID uses standard decimal notation; Python's default float formatting matches |
| File dialog | Custom save dialog | `QFileDialog.getSaveFileName()` | Standard Qt pattern, handles Windows path conventions |
| Encoding | Custom encoder | `Path.write_text(encoding="utf-8")` | UTF-8 is safe for ABB controller import; latin-1 originals can be safely written as UTF-8 |

## Common Pitfalls

### Pitfall 1: Shared Named Target Conflict
**What goes wrong:** Two moves reference the same robtarget (e.g., `p10`). User offsets one but not the other. Export updates the declaration, affecting both moves.
**Why it happens:** Named targets in RAPID are shared references. The EditModel gives each EditPoint its own pos copy, but the source file has a single declaration.
**How to avoid:** Document as a known limitation. The export updates the robtarget declaration based on the first EditPoint that references it. If the user needs different positions, they should use Offs() or inline targets in the original file.
**Warning signs:** Multiple moves in the viewer referencing the same named target with different edited positions.

### Pitfall 2: Line Number Shift After Insert/Delete
**What goes wrong:** Inserting a line shifts all subsequent line numbers. If patches are applied top-to-bottom, line numbers become invalid.
**Why it happens:** Line-based patching modifies the array length.
**How to avoid:** Always apply patches in REVERSE line order (highest line number first). This preserves the validity of lower line numbers.
**Warning signs:** Off-by-one errors in exported output; lines appear in wrong positions.

### Pitfall 3: Offs() with Variable Arguments (zLayer)
**What goes wrong:** Real-world .mod files use `Offs(pWorkStart, -2.7, -8.7, zLayer)` where `zLayer` is a PROC parameter, not a literal. The parser resolves this to 0.0 at parse time. If the user offsets the position, the export must update the numeric arguments but preserve `zLayer` as-is.
**Why it happens:** The parser evaluates `zLayer` as 0.0 (unknown variable fallback). The EditPoint.pos includes the resolved position, but the export needs to write back to the original Offs() format.
**How to avoid:** For Offs() targets, compute the delta between EditPoint.pos and original.target.pos, then ADD this delta to the original Offs() numeric arguments. Preserve variable arguments (non-numeric tokens) unchanged. If the third argument was `zLayer`, it stays `zLayer`.
**Warning signs:** Test with the real `00_CoCr_19.2pi_Shear_Test.mod` file which uses `zLayer` extensively.

### Pitfall 4: Multiline Statements
**What goes wrong:** A robtarget declaration may span multiple lines (e.g., `CONST robtarget p10 := [[500,0,400],\n[1,0,0,0],...]`). The `source_line` points to the first line, but the data extends across multiple lines.
**Why it happens:** RAPID allows line breaks within bracket data.
**How to avoid:** For robtarget declaration patching, find the line at `source_line`, then scan forward until the closing `];` to get the full extent. Replace the entire multi-line span. Use the test fixture `multiline.mod` to verify.
**Warning signs:** Test multiline.mod fixture produces truncated or malformed output.

### Pitfall 5: Encoding Mismatch
**What goes wrong:** Original file loaded as latin-1 (Windows-1252), exported as UTF-8. ABB controller or user expects same encoding.
**Why it happens:** `read_mod_file()` falls back to latin-1 silently.
**How to avoid:** Track the encoding used during load (`utf-8` or `latin-1`) and use the same encoding for export. Store it on ParseResult or MainWindow.
**Warning signs:** Non-ASCII characters in comments appear garbled after export.

## Code Examples

### Example 1: Patching a Named Target Declaration
```python
# Source: project-specific pattern based on existing regex patterns
import re

def patch_robtarget_pos(line: str, new_pos: np.ndarray) -> str:
    """Replace the [x,y,z] position in a robtarget declaration line."""
    # Match the first innermost bracket group (position)
    pattern = r"(\[\[)([^\[\]]+)(\])"
    def replacer(m: re.Match) -> str:
        return f"{m.group(1)}{new_pos[0]},{new_pos[1]},{new_pos[2]}{m.group(3)}"
    return re.sub(pattern, replacer, line, count=1)
```

### Example 2: Patching Speed/Zone in a Move Line
```python
# Source: project-specific pattern based on RE_MOVEL/RE_MOVEJ patterns
def patch_move_speed_zone(
    line: str, new_speed: str | None, new_zone: str | None
) -> str:
    """Replace speed and/or zone in a MoveL/MoveJ/MoveC line."""
    # Pattern: MoveX target, speed, zone, tool
    # After target (which may contain commas in brackets), find speed,zone,tool
    pattern = r"(Move\w+\s+.+?,\s*)(\w+)(\s*,\s*)(\w+)(\s*,\s*\w+)"
    m = re.search(pattern, line, re.IGNORECASE)
    if m:
        speed = new_speed if new_speed else m.group(2)
        zone = new_zone if new_zone else m.group(4)
        return line[:m.start(2)] + speed + m.group(3) + zone + line[m.end(4):]
    return line
```

### Example 3: Generating an Inserted Move Line
```python
# Source: project-specific, follows existing RAPID formatting conventions
def generate_move_line(point: EditPoint, indent: str = "    ") -> str:
    """Generate a RAPID move instruction line for an inserted point."""
    move = point.original
    pos = point.pos
    orient = move.target.orient if move.target else np.array([1, 0, 0, 0])
    confdata = move.target.confdata if move.target else (0, 0, 0, 0)
    extjoint = move.target.extjoint if move.target else (9e9,) * 6

    target_str = (
        f"[[{pos[0]},{pos[1]},{pos[2]}],"
        f"[{','.join(str(v) for v in orient)}],"
        f"[{','.join(str(v) for v in confdata)}],"
        f"[{','.join(str(v) for v in extjoint)}]]"
    )
    wobj_str = f" \\WObj:={move.wobj}" if move.wobj != "wobj0" else ""
    move_kw = move.move_type.name.capitalize()  # "MoveL", "MoveJ", etc.
    # MoveType enum: MOVEL -> "Movel" -- need proper casing
    kw_map = {"MOVEL": "MoveL", "MOVEJ": "MoveJ", "MOVEC": "MoveC", "MOVEABSJ": "MoveAbsJ"}
    move_kw = kw_map.get(move.move_type.name, "MoveL")

    return f"{indent}{move_kw} {target_str},{point.speed},{point.zone},{move.tool}{wobj_str};"
```

### Example 4: Save As Menu Action (Qt pattern)
```python
# Source: standard PyQt6 QFileDialog pattern
def _save_as(self) -> None:
    """Export modified .mod file via Save As dialog."""
    if self._parse_result is None:
        return
    default_name = str(self._current_file_path.with_stem(
        self._current_file_path.stem + "_modified"
    )) if self._current_file_path else ""
    file_path, _ = QFileDialog.getSaveFileName(
        self, "Save As", default_name,
        "RAPID Module (*.mod);;All Files (*)",
    )
    if not file_path:
        return
    # Prevent overwriting the original
    if Path(file_path).resolve() == self._current_file_path.resolve():
        QMessageBox.warning(self, "Warning", "Cannot overwrite the original file.")
        return
    # ... call mod_writer and write
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ with pytest-qt 4.4+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_mod_writer.py -x` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXP-01a | Named target position patching preserves format | unit | `uv run pytest tests/test_mod_writer.py::test_patch_named_target -x` | Wave 0 |
| EXP-01b | Offs() target position patching with variable args | unit | `uv run pytest tests/test_mod_writer.py::test_patch_offs_target -x` | Wave 0 |
| EXP-01c | Speed/zone patching on move line | unit | `uv run pytest tests/test_mod_writer.py::test_patch_speed_zone -x` | Wave 0 |
| EXP-01d | Deleted point commented out in export | unit | `uv run pytest tests/test_mod_writer.py::test_delete_comments_out -x` | Wave 0 |
| EXP-01e | Inserted point generates valid RAPID line | unit | `uv run pytest tests/test_mod_writer.py::test_insert_generates_line -x` | Wave 0 |
| EXP-01f | Full round-trip: load -> edit -> export -> reload matches | integration | `uv run pytest tests/test_mod_writer.py::test_round_trip -x` | Wave 0 |
| EXP-01g | Comments and non-move code preserved verbatim | unit | `uv run pytest tests/test_mod_writer.py::test_preserves_comments -x` | Wave 0 |
| EXP-01h | Save As dialog prevents original overwrite | unit (Qt) | `uv run pytest tests/test_main_window.py::test_save_as_prevents_overwrite -x` | Wave 0 |
| EXP-01i | Multiline robtarget declaration patching | unit | `uv run pytest tests/test_mod_writer.py::test_multiline_robtarget -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_mod_writer.py -x`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_mod_writer.py` -- all EXP-01 test cases
- [ ] `src/rapid_viewer/export/__init__.py` -- module init
- [ ] `src/rapid_viewer/export/mod_writer.py` -- core export logic

## Data Flow for Export

```
User clicks "Save As" (Ctrl+Shift+S)
  -> MainWindow._save_as()
    -> QFileDialog.getSaveFileName()
    -> Validate not overwriting original
    -> mod_writer.export_mod(
         source_text=self._parse_result.source_text,
         points=self._edit_model._points,
         targets=self._parse_result.targets,
       ) -> str (patched source text)
    -> Path(file_path).write_text(result, encoding=self._file_encoding)
    -> Mark undo stack as clean (optional: resets dirty indicator)
```

## Key Design Decisions for Planner

1. **EditPoint.is_inserted flag:** Must be added to EditPoint dataclass and set by InsertPointCommand. This is the only reliable way to distinguish inserted points from edited originals.

2. **ModWriter is pure Python (no Qt):** Place in `src/rapid_viewer/export/mod_writer.py`. Takes source_text (str), points (list[EditPoint]), targets dict. Returns patched string. This enables headless testing.

3. **Patch application order:** Always reverse (highest line number first) to preserve line index validity.

4. **Laser state (SetDO) patching -- DEFER:** Laser on/off changes are reflected in the viewer but NOT exported as SetDO modifications. The original SetDO lines are preserved as-is. Reason: SetDO signal names are file-specific and the viewer's laser_on is a simplified model. Document this limitation in the UI (tooltip or export dialog).

5. **Encoding preservation:** Store the encoding used during `read_mod_file()` and use the same for export. Add `_file_encoding: str` to MainWindow.

6. **File path tracking:** Add `self._current_file_path: Path | None = None` to MainWindow, set during `load_file()`.

7. **Original overwrite prevention:** Compare resolved paths. If match, show QMessageBox.warning and abort.

## Open Questions

1. **Shared named target with divergent edits**
   - What we know: EditModel gives each EditPoint its own pos copy, but the .mod file has one declaration
   - What's unclear: Should we warn the user if two moves reference the same target with different edits?
   - Recommendation: Use first-encountered edit. Low priority edge case -- document as known limitation.

2. **Inserted point move type for MoveC**
   - What we know: MoveC has a circle_point + endpoint. InsertPointCommand copies the original, which may be MoveC
   - What's unclear: Should inserted points always be MoveL regardless of source?
   - Recommendation: Generate inserted points as MoveL always. MoveC requires a circle point which makes no sense for an arbitrary inserted point.

## Sources

### Primary (HIGH confidence)
- Project codebase: `src/rapid_viewer/parser/rapid_parser.py` -- parser architecture and target resolution
- Project codebase: `src/rapid_viewer/ui/edit_model.py` -- EditModel/EditPoint API
- Project codebase: `src/rapid_viewer/ui/commands.py` -- QUndoCommand implementations
- Project codebase: `tests/fixtures/*.mod` -- test fixture .mod files
- Project codebase: `00_CoCr_19.2pi_Shear_Test.mod` -- real-world .mod file with Offs()+variable args

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` Decisions section -- source text patching strategy locked
- `.planning/ROADMAP.md` -- Phase 6 success criteria

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies needed, pure Python string manipulation
- Architecture: HIGH - source text patching is well-understood; EditModel API is clear
- Pitfalls: HIGH - identified from actual codebase analysis (Offs variable args, multiline, shared targets)

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable -- no external dependency changes expected)
