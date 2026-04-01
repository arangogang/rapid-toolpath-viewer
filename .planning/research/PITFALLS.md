# Domain Pitfalls: Adding Editing to an Existing Viewer

**Domain:** ABB RAPID Toolpath Viewer -- Milestone v1.1 (Toolpath Editing)
**Researched:** 2026-04-01
**Confidence:** HIGH (analyzed against actual codebase architecture)

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Frozen Dataclasses Block In-Place Mutation

**What goes wrong:**
The existing data model uses `@dataclass(frozen=True)` for `RobTarget`, `MoveInstruction`, and `JointTarget`. Frozen dataclasses raise `FrozenInstanceError` on attribute assignment. A developer attempts `move.target.pos[0] = 100.0` or `move.speed = "v500"` and gets a runtime crash. The "fix" of unfreezing everything cascades into broken `__hash__` implementations (both `RobTarget` and `JointTarget` have custom `__hash__` using frozen fields), broken dict lookups in `targets: dict[str, RobTarget]`, and bugs everywhere frozen objects were relied upon as dict keys or set members.

**Why it happens:**
The v1.0 architecture correctly chose frozen dataclasses for a read-only viewer -- immutability prevents accidental corruption and enables hashing. But editing fundamentally requires mutability. The naive fix (remove `frozen=True`) breaks the existing code in subtle ways.

**Consequences:**
- Unfreezing `RobTarget` breaks `targets` dict lookups if a target is mutated after being used as a key.
- Unfreezing `MoveInstruction` breaks any code that relies on identity stability.
- Hash values change after mutation, causing "ghost" entries in dicts/sets.

**Prevention:**
- Keep existing frozen dataclasses as-is for the parsed representation.
- Introduce a separate mutable editing layer: `EditableMoveInstruction` wrapping a `MoveInstruction` with editable fields, or use `dataclasses.replace()` to produce new immutable instances on each edit.
- The `dataclasses.replace()` pattern is already used in `main_window.py` line 166 (`replace(self._parse_result, moves=filtered_moves)`), so the codebase already has this pattern.
- After editing, rebuild the relevant frozen instances. This is the "immutable state + replace" pattern used by Redux, Elm, and other edit-state architectures.

**Detection:**
- `FrozenInstanceError` at runtime when first implementing coordinate editing.
- Test: try `move_instruction.speed = "v500"` -- if it raises, the model is still frozen.

**Phase to address:** First editing phase (data model). Must be resolved before any edit feature is implemented.

---

### Pitfall 2: Round-Trip .mod Serialization Destroys Formatting, Comments, and Non-Parsed Sections

**What goes wrong:**
The current parser (`parse_module`) extracts move instructions and robtarget declarations but discards everything else: comments (stripped by `code = line.split("!", 1)[0]`), blank lines, indentation, non-move statements (IF/WHILE/FOR blocks, PROC/FUNC definitions, variable declarations beyond robtargets, TPWrite, WaitTime, etc.). If the "Save As" feature reconstructs the .mod file from `ParseResult` data alone, the output file will be a skeleton containing only the edited targets and moves -- all program logic, comments, and formatting are gone. A robot engineer who opens the saved file and sees their program gutted will never trust the tool again.

**Why it happens:**
The parser was designed for rendering, not round-tripping. It extracts what it needs and discards the rest. The `source_text` field in `ParseResult` preserves the original text but there is no mechanism to map edits back into specific character ranges of that text.

**Consequences:**
- Saved .mod files are missing all non-move content (IF/ELSE, loops, custom procedures, comments).
- File is syntactically valid RAPID but semantically incomplete -- running it on a robot would fail or behave unexpectedly.
- Users lose trust in the tool and refuse to use the export feature.

**Prevention:**
- Do NOT reconstruct the file from parsed data. Instead, use a text-patching approach:
  1. Keep the original `source_text` as the base document.
  2. When a robtarget coordinate is edited, locate the exact character range of the value in the original text (using `source_line` + regex match position) and perform a surgical string replacement.
  3. When a move instruction property is changed (speed, zone), locate the exact parameter in the original text and replace just that token.
  4. When a move is deleted, remove the line range and optionally the associated robtarget declaration.
- Store character offsets (start, end) for each parsed entity during parsing, not just line numbers. This is the key architectural change needed.
- Alternative: use the existing line-number mapping. Since `RobTarget.source_line` and `MoveInstruction.source_line` track the 1-indexed line, find the line in `source_text.splitlines()`, regex-match the specific value, and replace it.

**Detection:**
- Save a file with comments and re-open it. If comments are gone, the serializer is reconstructing instead of patching.
- Diff the saved file against the original -- only edited values should differ.

**Phase to address:** Must be designed before implementing "Save As". The serialization architecture determines whether editing is viable.

---

### Pitfall 3: Undo/Redo Complexity Explodes Without a Command Pattern from Day One

**What goes wrong:**
Developers add editing features one at a time: first coordinate editing, then speed changes, then deletion. Each feature directly mutates the data model. When undo/redo is requested later, there is no record of what changed. Retrofitting undo requires wrapping every mutation site, which means rewriting every edit feature. Worse, compound operations (e.g., "delete waypoint and reconnect path") require transactional undo -- undoing the reconnection without restoring the deletion leaves the data in an impossible state.

**Why it happens:**
Undo/redo feels like a "nice to have" that can be added later. In reality, the edit architecture must be designed around undoable operations from the start, or the retrofit cost is proportional to the number of edit features already built.

**Consequences:**
- Every edit feature must be rewritten to use commands.
- Partial undo (undoing one part of a compound operation) corrupts the data model.
- Users make accidental edits with no way to recover, especially dangerous for robot programs.

**Prevention:**
- Use Qt's `QUndoStack` + `QUndoCommand` pattern. PyQt6 provides `QUndoStack` in `PyQt6.QtGui`.
- Define one `QUndoCommand` subclass per edit operation: `EditCoordinateCommand`, `EditSpeedCommand`, `DeleteWaypointCommand`, `EditZoneCommand`.
- Each command stores the old value and new value. `redo()` applies the new value, `undo()` restores the old value.
- For compound operations, use `QUndoCommand` macro grouping (`beginMacro`/`endMacro`).
- Set `QUndoStack.setUndoLimit()` to prevent unbounded memory growth (100-200 commands is reasonable).
- Wire `QUndoStack.cleanChanged` to the window title (show asterisk for unsaved changes).
- Implement undo/redo BEFORE implementing any edit feature. The command pattern is the edit architecture, not a feature layered on top.

**Detection:**
- If any edit feature directly mutates data without going through a command, undo is broken.
- Test: edit a coordinate, undo, verify the coordinate reverts. If this test does not exist, undo is not integrated.

**Phase to address:** First editing phase. QUndoStack must be created before the first edit feature is implemented. Every edit feature must use it.

---

### Pitfall 4: GL Buffer Full Rebuild on Every Edit Kills Interactivity

**What goes wrong:**
The current `update_scene()` flow is: `parse_result -> build_geometry() -> upload all VBOs`. This works for file load (happens once) but is too expensive for interactive editing. When a user drags a waypoint or changes a coordinate, the entire geometry is rebuilt from scratch: `build_geometry()` iterates all moves, builds float lists, converts to numpy arrays, and uploads all VBOs. For a 5000-point toolpath, this takes 50-100ms per edit -- visible lag during interactive dragging.

**Why it happens:**
The v1.0 architecture was designed for load-once-render-many. There was no reason to optimize the upload path because it only runs on file open. The `build_geometry()` function is monolithic -- it builds all buffers in one pass with no way to update a single segment.

**Consequences:**
- Coordinate editing with real-time 3D preview feels sluggish.
- Users expect immediate visual feedback when editing; 100ms delays make the tool feel broken.
- Developers try to optimize by throttling updates, which creates a different problem (stale display).

**Prevention:**
- For v1.1, accept full rebuild for now but optimize the rebuild path:
  1. Move the expensive numpy operations out of the hot path (pre-allocate arrays, use `numpy` vectorized ops instead of Python loops in `build_geometry()`).
  2. Use `glBufferSubData()` for single-point coordinate edits: calculate which vertex indices changed and update only those bytes in the VBO.
  3. Keep the full rebuild path as a fallback for structural changes (add/delete waypoints) that change buffer sizes.
- Separate geometry into per-segment VBOs only if profiling shows the monolithic approach is too slow. Premature segmentation adds complexity.
- For single-coordinate edits (the most common operation), the affected vertices are: the marker point (1 vertex), the line segment ending at this point (2 vertices), and the line segment starting from this point (2 vertices). That is 5 vertices to update via `glBufferSubData()`, regardless of total point count.

**Detection:**
- Profile `update_scene()` with a 5000-point file. If it takes >50ms, interactive editing will feel laggy.
- Test: edit one coordinate, measure time from edit to screen update.

**Phase to address:** Can start with full rebuild and optimize later, but the data model must track which indices changed to enable partial updates. Design the edit commands to carry index information.

---

### Pitfall 5: Selection State Becomes a Tangled Web of Signals

**What goes wrong:**
The current architecture has three components that reflect selection state: `PlaybackState` (owns the index), `ToolpathGLWidget` (highlights the point), and `CodePanel` (highlights the line). Adding editing introduces a fourth participant: the properties/info panel showing editable fields for the selected waypoint. Now there are circular signal chains: user clicks in 3D -> PlaybackState updates -> CodePanel highlights -> CodePanel emits `line_clicked` -> PlaybackState updates again -> infinite loop. The existing code in `_on_code_line_clicked` partially avoids this because `set_index` checks `if index == self._current_index: return`, but editing adds new signals (property changed, coordinate updated) that create new cycles.

**Why it happens:**
Each new UI component adds N new signal connections to the existing N components, creating O(N^2) potential signal paths. Without a clear "single source of truth" discipline, signals bounce between components and either loop infinitely or produce stale state where one panel shows old values.

**Consequences:**
- Infinite signal loops (UI freezes or stack overflow).
- Panel A shows updated value but Panel B shows the old value.
- Editing a property in the info panel triggers a 3D click handler which re-selects a different point.

**Prevention:**
- `PlaybackState` is already the single source of truth for selection. Keep it that way. All selection changes go through `PlaybackState.set_index()`, which already has the `if index == self._current_index: return` guard.
- For editing, add an `EditingModel` (or extend `PlaybackState`) that owns the current edit state. All edit operations go through this model. UI components observe the model and never talk to each other directly.
- Use `blockSignals(True)` when programmatically updating UI controls that emit change signals. The code panel already needs this pattern.
- Establish a clear signal flow diagram: `User action -> Model update -> Signal emission -> All observers update`. No observer should trigger a model update in response to a signal (unless it is a genuinely new user action).

**Detection:**
- Add a `print()` or logging statement in every signal handler. If any handler fires more than once per user action, there is a signal loop.
- Test: select waypoint in 3D, verify the properties panel shows correct data without triggering re-selection.

**Phase to address:** Must be designed before adding the properties panel. The selection architecture must support a fourth observer cleanly.

---

### Pitfall 6: Delete Waypoint Without Handling Adjacent Segment Reconnection

**What goes wrong:**
The project requirements include "toolpath delete with next-path connect/disconnect option." Deleting a waypoint is not just removing it from a list -- it changes the topology of the path. If waypoint B is deleted from sequence A->B->C, the user must choose: (a) reconnect A->C directly (different path!), or (b) leave a gap (A stops, C starts fresh). Simply removing B from `moves` list and rebuilding geometry creates an A->C connection automatically (because `build_geometry` connects consecutive points), which may not be what the user intended. Worse, if B was a MoveC circle point, deleting it invalidates the arc definition entirely.

**Why it happens:**
List-based thinking: "delete = remove from list." But toolpath topology is not a list -- it is a sequence of motion segments where each segment type (MoveL, MoveJ, MoveC) has different implications for what "the previous point" means.

**Consequences:**
- Unintended path connections after deletion (robot takes a shortcut through the workpiece).
- MoveC arc becomes invalid (only 2 of 3 defining points remain).
- Laser-on state transitions get lost (deleting the point where SetDO toggles laser).

**Prevention:**
- Implement deletion as a multi-step operation with user confirmation:
  1. Show a preview of the path after deletion (with and without reconnection).
  2. If the deleted point is a MoveC intermediate or endpoint, warn that the arc will be converted to a MoveL or removed.
  3. If the deleted point has a SetDO (laser toggle) before it, warn that laser state changes will be lost.
- In the undo command, store not just the deleted move but also its index, so it can be re-inserted at the exact position.
- Consider marking moves as "disabled" (soft delete) instead of removing them, making undo trivial.

**Detection:**
- Test: delete a middle waypoint, verify the path visualization matches expectations.
- Test: delete a MoveC endpoint, verify no crash and arc is handled.

**Phase to address:** Delete feature phase. Must be designed with the reconnection logic, not added as an afterthought.

---

## Moderate Pitfalls

### Pitfall 7: Source Line Numbers Become Invalid After Edits

**What goes wrong:**
Every `RobTarget` and `MoveInstruction` stores a `source_line` integer pointing into the original file. When a waypoint is deleted (removing lines from the source text) or added (inserting lines), all subsequent `source_line` values become wrong. The code panel shows the wrong line highlighted, clicking in the code panel selects the wrong waypoint, and saved files have edits applied to the wrong locations.

**Prevention:**
- After any edit that changes line counts, recalculate all `source_line` values by re-parsing or applying a line offset delta to all instructions after the edit point.
- Better: use the immutable `source_line` only for the original file. Track edits as a list of patches (line number, old text, new text) and apply them to `source_text` to produce the current document. The code panel always displays the current patched document.
- For "Save As", apply all patches sequentially to the original source text.

**Detection:**
- Delete a waypoint near the top of the file, then click a waypoint near the bottom. If the code panel highlights the wrong line, `source_line` values are stale.

**Phase to address:** Must be solved alongside the first edit feature that modifies source text.

---

### Pitfall 8: Offs() Target References Create Hidden Dependencies

**What goes wrong:**
The parser resolves `Offs(pBase, dx, dy, dz)` into a new `RobTarget` with computed position. If the user edits `pBase`'s coordinates, all `Offs()` references to `pBase` should update too. But the resolver creates independent `RobTarget` copies -- the `Offs` result has no back-reference to `pBase`. Editing `pBase` leaves all `Offs(pBase, ...)` points at their old positions.

**Prevention:**
- Track `Offs()` dependencies: when resolving `Offs(pBase, dx, dy, dz)`, store the relationship `(base_name="pBase", offset=[dx, dy, dz])` in the resolved target.
- When `pBase` is edited, find all moves whose target was derived via `Offs(pBase, ...)` and recompute their positions.
- Alternatively, for v1.1 simplicity: when editing a point that is an Offs reference, warn the user that only the resolved position is being edited, not the base target. This breaks the Offs relationship but is transparent.

**Detection:**
- Edit a base robtarget, check if Offs-derived points update. If they do not, dependencies are not tracked.

**Phase to address:** Coordinate editing phase. At minimum, display a warning for Offs-derived targets.

---

### Pitfall 9: Code Panel Becomes an Inconsistent Second Source of Truth

**What goes wrong:**
The `CodePanel` currently displays `source_text` from `ParseResult` -- a read-only snapshot of the original file. When edits are made through the properties panel or 3D widget, the code panel still shows the original text. The user sees old coordinates in the code while the 3D view shows new coordinates. If the code panel is updated to show modified text, but the modification is done by string replacement on a separate copy, the code panel and the edit model can drift apart.

**Prevention:**
- Maintain a single mutable document (the patched source text) that the code panel displays.
- Every edit operation updates this document first, then the code panel refreshes from it.
- Never let the code panel hold its own copy of the source text independently of the edit model.
- The `CodePanel.set_source()` method should be called after every edit, or the code panel should observe the document model directly.

**Detection:**
- Edit a coordinate, look at the code panel. If it still shows the old value, the code panel is stale.

**Phase to address:** First edit feature. The code panel update mechanism must be defined before any editing is implemented.

---

### Pitfall 10: Speed/Zone Value Validation Against RAPID Semantics

**What goes wrong:**
RAPID speed data (`v100`, `v500`, `vmax`) and zone data (`fine`, `z10`, `z50`) are not arbitrary strings -- they are predefined RAPID data types with specific meanings. The current parser stores them as plain strings (`speed: str`, `zone: str`). An editing UI that lets the user type freeform text risks invalid values (`v99999`, `zfoo`) that will cause robot controller errors when the file is loaded on an actual ABB controller.

**Prevention:**
- Provide dropdown/combobox selection for speed and zone values, populated with standard RAPID values.
- Allow custom values but validate format: `v[integer]` for speed, `z[integer]` or `fine` for zone.
- Display a warning for non-standard values, not a hard block (some sites define custom speed data).

**Detection:**
- Type a nonsensical speed value and save. If the file is accepted without warning, validation is missing.

**Phase to address:** Properties editing phase.

---

## Minor Pitfalls

### Pitfall 11: Edit Mode vs. View Mode UX Confusion

**What goes wrong:**
Users accidentally edit waypoints while trying to navigate (orbit, pan, zoom). A click intended to start an orbit drag is interpreted as a waypoint selection for editing. Or a scroll intended for zoom triggers a value change in a spinbox.

**Prevention:**
- Add an explicit Edit Mode toggle (toolbar button or keyboard shortcut).
- In View Mode: clicks orbit/pan/zoom, no editing possible.
- In Edit Mode: clicks select waypoints for editing, orbit requires modifier key (e.g., Alt+drag).
- Visual indicator: change cursor or border color when in Edit Mode.

**Phase to address:** UI/UX design phase, before implementing editing interactions.

---

### Pitfall 12: Multiple PROC Filtering + Editing Interaction

**What goes wrong:**
The current PROC filter creates a filtered view of moves. If a user edits a waypoint while a PROC filter is active, the edit must apply to the correct move in the full (unfiltered) list. The filtered view uses `dataclasses.replace(self._parse_result, moves=filtered_moves)` which creates a copy -- edits to the copy do not propagate back to the original `ParseResult`.

**Prevention:**
- Edits must always reference the canonical move list in the original `ParseResult`, not the filtered copy.
- Use indices into the original list, not the filtered list, for edit commands.
- When applying an edit, update the original, then re-apply the current filter to refresh the view.

**Detection:**
- Activate a PROC filter, edit a waypoint, remove the filter. If the edit is lost, the filtered copy was edited instead of the original.

**Phase to address:** Editing architecture phase. The relationship between filtered views and the canonical data must be clear.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Data model for editing | Frozen dataclass mutation (Pitfall 1) | Use `dataclasses.replace()` pattern; keep frozen types |
| .mod serialization / Save As | Destroying comments/formatting (Pitfall 2) | Text-patching on original source, not reconstruction |
| Undo/redo | Retrofitting after edit features exist (Pitfall 3) | Implement QUndoStack before any edit feature |
| GL buffer updates | Full rebuild per edit (Pitfall 4) | Accept full rebuild initially; design for partial update later |
| Selection + properties panel | Signal loops (Pitfall 5) | Single source of truth in PlaybackState |
| Waypoint deletion | Topology corruption (Pitfall 6) | User confirmation with preview; handle MoveC specially |
| Coordinate editing | Stale source_line values (Pitfall 7) | Single mutable document as source of truth |
| Coordinate editing | Offs() dependency blindness (Pitfall 8) | Track or warn about Offs relationships |
| Code panel sync | Stale display (Pitfall 9) | Code panel observes the mutable document |
| Speed/zone editing | Invalid RAPID values (Pitfall 10) | Dropdown selection + validation |
| Edit UX | Accidental edits during navigation (Pitfall 11) | Explicit Edit Mode toggle |
| PROC filter + editing | Edits lost on filter change (Pitfall 12) | Edit canonical data, not filtered view |

## Architecture Risk Summary

The single highest-risk architectural decision for v1.1 is the **serialization strategy** (Pitfall 2). If the team reconstructs .mod files from parsed data, the feature is DOA -- no robot engineer will use a tool that strips their comments and program logic. The text-patching approach requires storing character offsets during parsing, which means the parser needs to be enhanced (not rewritten) to track these positions.

The second highest risk is **undo/redo architecture** (Pitfall 3). If edit features ship without QUndoStack, every feature will need to be rewritten to add undo support. This is a foundational decision that must be made before the first edit line of code.

## Sources

- Codebase analysis: `tokens.py` (frozen dataclasses), `rapid_parser.py` (comment stripping, line tracking), `geometry_builder.py` (monolithic build), `toolpath_gl_widget.py` (full VBO rebuild), `main_window.py` (signal wiring), `playback_state.py` (selection model)
- [Qt 6 QUndoStack Documentation](https://doc.qt.io/qt-6/qundostack.html) -- Command pattern, macro grouping, clean state tracking
- [PySide6/PyQt6 QUndoStack](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QUndoStack.html) -- Python bindings for undo framework
- [Preserving comments when parsing and formatting code](https://jayconrod.com/posts/129/preserving-comments-when-parsing-and-formatting-code) -- Round-trip parsing architecture patterns
- [Lossless Syntax Trees](https://dev.to/cad97/lossless-syntax-trees-280c) -- CST vs AST for round-trip editing
- [OpenGL VBO Best Practices (Khronos Wiki)](https://www.khronos.org/opengl/wiki/Vertex_Specification_Best_Practices) -- glBufferSubData vs glBufferData guidance
- [LearnOpenGL Advanced Data](https://learnopengl.com/Advanced-OpenGL/Advanced-Data) -- Partial buffer updates

---
*Pitfalls research for: ABB RAPID Toolpath Viewer v1.1 (Editing Milestone)*
*Researched: 2026-04-01*
