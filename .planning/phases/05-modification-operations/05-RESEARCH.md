# Phase 5: Modification Operations - Research

**Researched:** 2026-04-01
**Domain:** PyQt6 QUndoCommand mutation patterns, EditModel modification API, PropertyPanel editable conversion
**Confidence:** HIGH

## Summary

Phase 5 adds four modification operations to the existing EditModel/SelectionState infrastructure built in Phase 4: coordinate offset (MOD-01), property edit (MOD-02), delete with topology options (MOD-03), and continuous insertion (MOD-04). All operations must be undoable via QUndoStack.

The codebase already has the exact infrastructure needed: EditModel with QUndoStack, EditPoint with mutable fields (pos, speed, zone, laser_on, deleted), SelectionState for batch operations, and a full geometry rebuild pattern via `build_geometry()`. The primary work is (1) creating QUndoCommand subclasses for each operation type, (2) adding mutation methods to EditModel, (3) converting PropertyPanel from read-only QLabels to editable QLineEdit/QComboBox widgets, and (4) wiring signals through MainWindow.

**Primary recommendation:** Implement mutation methods on EditModel that each create and push a QUndoCommand. Use explicit parent-child QUndoCommand pattern (not beginMacro/endMacro) for compound multi-select operations. After each mutation, emit a signal that MainWindow routes to `ToolpathGLWidget.update_scene()` for full geometry rebuild.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Convert PropertyPanel from read-only to inline editable. Position X/Y/Z remain read-only (display current values). Add dX/dY/dZ offset input fields (QLineEdit) below position, with an "Apply Offset" button.
- **D-02:** Speed and zone fields become free-text QLineEdit inputs (not dropdowns). Users type RAPID speeddata/zonedata names directly (v500, vmax, z10, fine, etc.). Supports custom names without validation.
- **D-03:** Laser state becomes a QComboBox toggle (ON/OFF).
- **D-04:** Property changes (speed, zone, laser) commit immediately on Enter key press or dropdown change. Each change creates one QUndoCommand. No "Apply" button needed for property edits -- undo is the safety net.
- **D-05:** Offset fields retain their values after Apply (not reset to zero). Enables rapid repeated offsets at uniform spacing.
- **D-06:** Delete button placed at the bottom of PropertyPanel, styled red, enabled only when points are selected. Keyboard shortcut: Del key.
- **D-07:** Delete triggers a confirmation dialog: "Delete N point(s)?" with three buttons: [Reconnect] [Break] [Cancel]. One dialog for all selected points -- same topology choice applies to all.
- **D-08:** Reconnect = next move after deleted segment connects to the last move before it. Break = deleted segment becomes a laser-off gap (MoveJ or equivalent non-cutting move).
- **D-09:** "Insert After" button in PropertyPanel, enabled when exactly one point is selected. Click opens/reuses the offset input section (dX/dY/dZ).
- **D-10:** Apply creates a new point after the selected point, with position = selected.pos + offset, properties copied from source point. New point becomes selected automatically, enabling chained insertion.
- **D-11:** Offset fields keep values between insertions (per D-05). User clicks Apply repeatedly for uniform spacing. Click elsewhere or select another point to stop inserting.
- **D-12:** Offset Apply with multi-select: same dX/dY/dZ delta applied to ALL selected points. One compound QUndoCommand wrapping all individual moves.
- **D-13:** Speed/zone/laser change with multi-select: new value overwrites ALL selected points. One compound QUndoCommand.
- **D-14:** Delete with multi-select: one dialog for all selected points. Same reconnect/break choice applies to all. One compound QUndoCommand.
- **D-15:** Insert After is disabled during multi-select (only works with single selection per D-09).

### Claude's Discretion
- QUndoCommand subclass naming and internal structure for each operation type
- Exact layout/spacing of new offset input fields within PropertyPanel
- How "reconnect" is implemented internally (whether to modify the next move's target or remap references)
- How "break" inserts a laser-off gap (implementation detail of the gap move)
- Signal names for edit operations (e.g., point_modified, points_deleted)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOD-01 | Coordinate offset modification -- X,Y,Z delta input to move selected waypoints | EditPoint.pos is mutable np.ndarray; QUndoCommand stores old/new pos; full geometry rebuild after mutation |
| MOD-02 | Property modification -- speed, zone, laser_on changes | EditPoint fields already mutable; QLineEdit for speed/zone, QComboBox for laser; immediate commit on Enter/change |
| MOD-03 | Waypoint deletion with reconnect/break topology options | EditPoint.deleted flag exists; "reconnect" skips deleted in geometry build; "break" sets laser_on=False on next point |
| MOD-04 | Continuous insertion -- new points by offset from selected, properties copied | EditModel._points list insert; new EditPoint with computed pos; auto-select new point for chaining |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech Stack**: Python + PyQt6 + PyOpenGL only
- **Platform**: Windows desktop only
- **Scope**: Viewer with editing -- no simulation
- **Style**: Ruff formatting, line length 100, `from __future__ import annotations` in all modules
- **Qt Patterns**: PyQt6 fully-qualified enums, pyqtSignal for state changes, blockSignals() for programmatic updates
- **Testing**: pytest + pytest-qt, tests organized by requirement ID, shared fixtures in conftest.py
- **Data Flow**: Qt signals only between components; no direct method calls between UI elements
- **OpenGL**: Full geometry rebuild (not incremental) via build_geometry() after any data change

## Standard Stack

### Core (already installed, no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | >=6.10 | QUndoCommand, QLineEdit, QComboBox, QDoubleValidator, QMessageBox | Already in stack; provides all needed widgets |
| NumPy | >=1.26 | np.ndarray pos manipulation for offset operations | Already in stack; EditPoint.pos is np.ndarray |

### No New Dependencies Required
This phase adds no new libraries. All functionality is built from PyQt6 widgets and existing EditModel/EditPoint infrastructure.

## Architecture Patterns

### Recommended Project Structure (new/modified files)
```
src/rapid_viewer/ui/
    commands.py          # NEW: QUndoCommand subclasses for all 4 operation types
    edit_model.py        # MODIFY: add mutation methods (apply_offset, set_speed, set_zone, set_laser, delete_points, insert_after)
    property_panel.py    # MODIFY: convert to editable; add offset group, action buttons, signals
    main_window.py       # MODIFY: wire PropertyPanel edit signals to EditModel; refresh GL after mutations
src/rapid_viewer/renderer/
    geometry_builder.py  # MODIFY: skip deleted points in build_geometry()
    toolpath_gl_widget.py # MINOR: may need adjusted index mapping after insert/delete
tests/
    test_commands.py     # NEW: unit tests for each QUndoCommand subclass
    test_property_panel.py # MODIFY: add tests for editable behavior
    test_edit_model.py   # MODIFY: add tests for mutation methods
```

### Pattern 1: QUndoCommand Subclass per Operation
**What:** Each edit operation type gets its own QUndoCommand subclass. The command stores the EditModel reference, target indices, old values, and new values. undo() restores old values; redo() applies new values.
**When to use:** Every mutation to EditPoint data.
**Example:**
```python
# Source: Qt 6 QUndoCommand docs + project conventions
from PyQt6.QtGui import QUndoCommand
import numpy as np

class OffsetPointsCommand(QUndoCommand):
    """Apply XYZ offset to one or more EditPoints."""

    def __init__(
        self,
        model: EditModel,
        indices: list[int],
        delta: np.ndarray,
        parent: QUndoCommand | None = None,
    ) -> None:
        super().__init__("Offset points", parent)
        self._model = model
        self._indices = indices
        self._delta = delta.copy()
        # Capture old positions for undo
        self._old_positions = [model.point_at(i).pos.copy() for i in indices]

    def redo(self) -> None:
        for idx in self._indices:
            self._model.point_at(idx).pos += self._delta
        self._model.points_changed.emit()

    def undo(self) -> None:
        for i, idx in enumerate(self._indices):
            self._model.point_at(idx).pos[:] = self._old_positions[i]
        self._model.points_changed.emit()
```

### Pattern 2: Compound Commands via Parent Constructor
**What:** For batch operations (multi-select), create a parent QUndoCommand with child commands. Qt automatically calls undo/redo on all children in correct order.
**When to use:** When a single user action modifies multiple points (D-12, D-13, D-14).
**Recommended approach:** Use a single command class that internally handles a list of indices, rather than parent-child nesting. This is simpler and avoids the complexity of child command ordering.
**Example:**
```python
class SetSpeedCommand(QUndoCommand):
    """Set speed on one or more EditPoints."""

    def __init__(self, model: EditModel, indices: list[int], new_speed: str) -> None:
        count = len(indices)
        super().__init__(f"Set speed ({count} point{'s' if count > 1 else ''})")
        self._model = model
        self._indices = indices
        self._new_speed = new_speed
        self._old_speeds = [model.point_at(i).speed for i in indices]

    def redo(self) -> None:
        for idx in self._indices:
            self._model.point_at(idx).speed = self._new_speed
        self._model.points_changed.emit()

    def undo(self) -> None:
        for i, idx in enumerate(self._indices):
            self._model.point_at(idx).speed = self._old_speeds[i]
        self._model.points_changed.emit()
```

### Pattern 3: EditModel as Mutation Gateway
**What:** All mutations go through EditModel methods. Each method creates and pushes a QUndoCommand. The command's redo() executes immediately on push. EditModel emits a `points_changed` signal after mutation.
**When to use:** Always -- no direct EditPoint mutation from UI code.
**Example:**
```python
class EditModel(QObject):
    points_changed = pyqtSignal()  # NEW: emitted after any point data changes

    def apply_offset(self, indices: list[int], delta: np.ndarray) -> None:
        cmd = OffsetPointsCommand(self, indices, delta)
        self._undo_stack.push(cmd)  # push calls redo() automatically
```

### Pattern 4: Geometry Rebuild After Mutation
**What:** MainWindow connects `EditModel.points_changed` to a handler that rebuilds geometry from EditModel data and uploads to GPU.
**When to use:** After every edit operation.
**Key detail:** Currently `build_geometry()` takes a `ParseResult`. After Phase 5, it needs to also accept EditModel state (modified positions, deleted flags, inserted points). Options:
1. Build a synthetic ParseResult from EditModel data (adapts existing API)
2. Add a `build_geometry_from_edit_model()` variant
3. Modify build_geometry to accept a list of EditPoints

**Recommendation:** Option 1 -- create a helper method on EditModel that produces a list of synthetic `MoveInstruction` objects reflecting current state (modified pos, deleted skipped, inserted included). This preserves the existing geometry builder API.

### Pattern 5: Delete Implementation (Reconnect vs Break)
**What:** Deletion uses the `EditPoint.deleted` soft-delete flag. When building geometry:
- **Reconnect:** Skip deleted points entirely. The line from the last non-deleted point connects to the next non-deleted point automatically (because build_geometry iterates in order and tracks prev_pos).
- **Break:** Mark deleted points AND set `laser_on=False` on the next non-deleted point (so the connecting segment renders as a dim/non-cutting path), OR insert a synthetic MoveJ gap.
**Recommendation:** Reconnect is handled naturally by skipping deleted points in geometry build. For Break, set the `laser_on=False` flag on the first non-deleted point after the gap. This uses existing color logic (dim red for laser-off MoveL).

### Pattern 6: Insert Implementation
**What:** Insertion adds a new EditPoint to `EditModel._points` list at a specific index position. The new point has:
- `pos = source_point.pos + offset`
- `speed`, `zone`, `laser_on`, `tool`, `wobj` copied from source
- A synthetic `MoveInstruction` as `original` (for consistency)
- `move_type` same as source
**Key concern:** Inserting changes all indices after the insertion point. SelectionState, PlaybackState, and GL widget waypoint positions all use indices. After insert, the new point's index is `source_index + 1`, and all subsequent indices shift by +1.
**Mitigation:** The InsertCommand's redo() inserts the point and updates SelectionState to select the new point. The undo() removes it and restores previous selection. Full geometry rebuild handles rendering.

### Anti-Patterns to Avoid
- **Direct EditPoint mutation from PropertyPanel:** Always go through EditModel methods that create QUndoCommands. Never modify `point.pos` directly from UI code.
- **Incremental VBO updates:** The codebase uses full rebuild. Do not try to patch individual vertices -- it would be fragile and inconsistent with the established pattern.
- **beginMacro/endMacro for compound commands:** While Qt supports this, it is more complex to manage in signal-driven architecture. A single command handling a list of indices is simpler and equally functional.
- **Forgetting to blockSignals on programmatic widget updates:** When undo/redo changes data and the property panel refreshes, the QLineEdit/QComboBox value changes should not trigger new QUndoCommands. Use `blockSignals(True)` during `update_from_point()`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Undo/redo stack | Custom undo list | QUndoStack + QUndoCommand | Qt handles command ordering, clean state, menu action text, memory management |
| Float input validation | Manual text parsing | QDoubleValidator | Handles locale, negative numbers, decimal precision |
| Delete confirmation | Custom dialog widget | QMessageBox with custom buttons | Standard OS-native dialog, keyboard handling (Escape=Cancel) |
| Input commit on Enter | Key event filter | QLineEdit.editingFinished signal | Built-in signal, handles Enter key and focus-out |

## Common Pitfalls

### Pitfall 1: Signal Cascade on Undo/Redo
**What goes wrong:** Undo restores a value, which triggers PropertyPanel to update, which triggers the QLineEdit editingFinished signal, which creates a NEW QUndoCommand for the "change" that was actually an undo restoration.
**Why it happens:** QLineEdit.editingFinished fires when text changes programmatically too.
**How to avoid:** Use `blockSignals(True)` on all editable widgets in `update_from_point()`. Or use a `_updating` guard flag on PropertyPanel.
**Warning signs:** Undo appears to do nothing, or creates an infinite loop of undo/redo.

### Pitfall 2: Index Invalidation After Insert/Delete
**What goes wrong:** After inserting or deleting a point, stored indices in SelectionState, PlaybackState, and GL widget become stale. A selected index of 5 might now refer to a different point.
**Why it happens:** Insert shifts all subsequent indices +1; delete (if removing from list) shifts all subsequent indices -1.
**How to avoid:** After insert/delete, clear and re-establish SelectionState. For delete with soft-delete flag, indices don't shift (point remains in list but marked deleted). For insert, the command must adjust SelectionState to reflect the new point.
**Warning signs:** Wrong point highlighted after undo, property panel shows wrong data.

### Pitfall 3: QUndoCommand.redo() Called on Push
**What goes wrong:** Developer implements redo() but also manually applies the edit before pushing. The edit gets applied twice.
**Why it happens:** `QUndoStack.push(cmd)` automatically calls `cmd.redo()`. This is by Qt design.
**How to avoid:** Never apply the edit manually. Let push() -> redo() handle it. The command's constructor only captures state; redo() applies the change.
**Warning signs:** Values doubled (e.g., offset applied twice).

### Pitfall 4: Geometry Build Must Reflect EditModel State
**What goes wrong:** After edits, the 3D view still shows original positions because build_geometry() reads from ParseResult (frozen data), not EditModel (mutable data).
**Why it happens:** The existing code path is `ParseResult -> build_geometry() -> GPU`. Edits modify EditModel but ParseResult is unchanged.
**How to avoid:** Create a method that generates geometry-ready data from EditModel state. Either synthesize a modified ParseResult or pass EditModel data directly to a geometry builder variant.
**Warning signs:** 3D view doesn't update after edits, or reverts to original on any refresh.

### Pitfall 5: MoveC Delete Breaks Arc Geometry
**What goes wrong:** Deleting a MoveC endpoint leaves its circle_point orphaned. Deleting the point before a MoveC removes the arc's start position.
**Why it happens:** MoveC requires 3 points (prev_pos, circle_point, target). Removing any of these makes the arc impossible to render.
**How to avoid:** When deleting near MoveC segments, the "reconnect" path naturally skips the arc (it becomes a straight line from prev non-deleted to next non-deleted). Document this as expected behavior.
**Warning signs:** Crash in tessellate_arc() or degenerate geometry.

### Pitfall 6: editingFinished Fires on Focus Loss
**What goes wrong:** QLineEdit.editingFinished fires when the user clicks away from the field, even without pressing Enter. This creates unexpected QUndoCommands when the user is just browsing.
**Why it happens:** editingFinished fires on Enter AND on focus-out.
**How to avoid:** Compare old and new values before creating a command. Only create a QUndoCommand if the value actually changed.
**Warning signs:** Spurious undo commands that don't change anything.

## Code Examples

### QDoubleValidator for Offset Fields
```python
# Source: Qt 6 QDoubleValidator docs
from PyQt6.QtGui import QDoubleValidator

validator = QDoubleValidator()
validator.setDecimals(3)
# No range restriction -- any float value allowed
self._dx_input = QLineEdit()
self._dx_input.setValidator(validator)
self._dx_input.setPlaceholderText("0.0")
```

### QMessageBox with Custom Buttons (Delete Dialog)
```python
# Source: Qt 6 QMessageBox docs + D-07
from PyQt6.QtWidgets import QMessageBox, QPushButton

def _show_delete_dialog(self, count: int) -> str | None:
    dlg = QMessageBox(self)
    dlg.setWindowTitle("Delete Point(s)")
    dlg.setText(f"Delete {count} point(s)?")
    dlg.setIcon(QMessageBox.Icon.Warning)

    reconnect_btn = dlg.addButton("Reconnect", QMessageBox.ButtonRole.AcceptRole)
    break_btn = dlg.addButton("Break", QMessageBox.ButtonRole.DestructiveRole)
    cancel_btn = dlg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    dlg.setDefaultButton(cancel_btn)
    dlg.setEscapeButton(cancel_btn)

    dlg.exec()
    clicked = dlg.clickedButton()
    if clicked is reconnect_btn:
        return "reconnect"
    elif clicked is break_btn:
        return "break"
    return None
```

### Synthesizing Geometry Data from EditModel
```python
# Pattern for building geometry from edited state
def _build_edited_moves(self) -> list[MoveInstruction]:
    """Create synthetic MoveInstruction list reflecting current edit state."""
    from dataclasses import replace
    result = []
    for point in self._points:
        if point.deleted:
            continue
        if point.original.target is None:
            result.append(point.original)
            continue
        # Create modified RobTarget with updated pos
        new_target = RobTarget(
            name=point.original.target.name,
            pos=point.pos.copy(),
            orient=point.original.target.orient,
            confdata=point.original.target.confdata,
            extjoint=point.original.target.extjoint,
            source_line=point.original.target.source_line,
        )
        new_move = MoveInstruction(
            move_type=point.original.move_type,
            target=new_target,
            circle_point=point.original.circle_point,
            joint_target=point.original.joint_target,
            speed=point.speed,
            zone=point.zone,
            tool=point.original.tool,
            wobj=point.original.wobj,
            source_line=point.original.source_line,
            has_cartesian=point.original.has_cartesian,
            laser_on=point.laser_on,
        )
        result.append(new_move)
    return result
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| QUndoCommand in QtWidgets | QUndoCommand in QtGui | PyQt6 6.0+ | Import from PyQt6.QtGui, not QtWidgets |
| beginMacro/endMacro for batch | Single command with index list | Project convention | Simpler, avoids signal timing issues |

**Deprecated/outdated:**
- `QUndoCommand` was in `QtWidgets` in PyQt5. In PyQt6, it moved to `QtGui` (already correct in Phase 4 code).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0+ with pytest-qt 4.4+ |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/test_commands.py tests/test_edit_model.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOD-01 | Offset apply modifies pos, undo restores | unit | `python -m pytest tests/test_commands.py::TestOffsetCommand -x` | Wave 0 |
| MOD-01 | Multi-select offset applies delta to all | unit | `python -m pytest tests/test_commands.py::TestOffsetCommandMulti -x` | Wave 0 |
| MOD-02 | Speed/zone/laser set on single point | unit | `python -m pytest tests/test_commands.py::TestSetSpeedCommand -x` | Wave 0 |
| MOD-02 | Multi-select property change overwrites all | unit | `python -m pytest tests/test_commands.py::TestSetSpeedCommandMulti -x` | Wave 0 |
| MOD-03 | Delete with reconnect skips point, path continuous | unit | `python -m pytest tests/test_commands.py::TestDeleteCommand -x` | Wave 0 |
| MOD-03 | Delete with break inserts laser-off gap | unit | `python -m pytest tests/test_commands.py::TestDeleteCommandBreak -x` | Wave 0 |
| MOD-03 | Delete undo restores points | unit | `python -m pytest tests/test_commands.py::TestDeleteCommandUndo -x` | Wave 0 |
| MOD-04 | Insert creates new point at offset from source | unit | `python -m pytest tests/test_commands.py::TestInsertCommand -x` | Wave 0 |
| MOD-04 | Insert + auto-select enables chaining | unit | `python -m pytest tests/test_commands.py::TestInsertCommandChain -x` | Wave 0 |
| ALL | PropertyPanel editable widgets display and commit | unit | `python -m pytest tests/test_property_panel.py -x` | Existing (needs extension) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_commands.py tests/test_edit_model.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_commands.py` -- covers MOD-01, MOD-02, MOD-03, MOD-04 (all command undo/redo)
- [ ] `tests/test_property_panel.py` -- extend with editable widget tests (offset fields, speed/zone inputs, laser combo, action buttons)
- [ ] `tests/test_edit_model.py` -- extend with mutation method tests (apply_offset, set_speed, delete_points, insert_after)

## Open Questions

1. **Geometry builder adaptation for edited data**
   - What we know: build_geometry() takes ParseResult with frozen MoveInstructions. EditModel has mutable EditPoints.
   - What's unclear: Whether to modify build_geometry() signature or create an adapter.
   - Recommendation: Create `EditModel.build_edited_moves() -> list[MoveInstruction]` that synthesizes frozen instructions from current state, then wrap in a synthetic ParseResult. This preserves the existing geometry builder API untouched.

2. **Insert point's original MoveInstruction**
   - What we know: EditPoint requires an `original` MoveInstruction for diff/export (Phase 6).
   - What's unclear: What source_line to assign to inserted points (they don't exist in original source).
   - Recommendation: Use source_line=-1 for inserted points. Phase 6 export will need to generate new RAPID source lines for these.

3. **PlaybackState index management after insert/delete**
   - What we know: PlaybackState stores a flat index into the moves list. Insert/delete changes list length.
   - What's unclear: Whether PlaybackState should track by index or by identity.
   - Recommendation: After any structural change (insert/delete), rebuild PlaybackState moves list from EditModel and reset to safe index.

## Sources

### Primary (HIGH confidence)
- Project codebase: edit_model.py, property_panel.py, selection_state.py, main_window.py, geometry_builder.py, toolpath_gl_widget.py, tokens.py -- direct code reading
- [Qt 6 QUndoCommand docs](https://doc.qt.io/qt-6/qundocommand.html) -- constructor with parent, redo/undo behavior, push() auto-calls redo()
- [Qt 6 QUndoStack docs](https://doc.qt.io/qt-6/qundostack.html) -- beginMacro/endMacro, clean state

### Secondary (MEDIUM confidence)
- [Qt Undo Framework overview](https://doc.qt.io/qt-6/qundo.html) -- macro vs compression patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all PyQt6 native
- Architecture: HIGH -- patterns directly derived from existing codebase (Phase 4 EditModel, build_geometry, signal wiring)
- Pitfalls: HIGH -- derived from direct code reading and Qt documentation

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable stack, no fast-moving dependencies)
