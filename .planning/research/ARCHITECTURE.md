# Architecture Patterns: Toolpath Editing Integration

**Domain:** Toolpath editing for ABB RAPID viewer (read-only viewer -> read-write editor)
**Researched:** 2026-04-01
**Confidence:** HIGH (based on direct codebase analysis + established Qt/MVC patterns)

## Current Architecture (Read-Only)

```
.mod file --> rapid_parser.parse_module() --> ParseResult (frozen items)
                                                  |
                                                  v
                                        geometry_builder.build_geometry()
                                                  |
                                                  v
                                          GeometryBuffers (numpy arrays)
                                                  |
                                                  v
                                    ToolpathGLWidget (VBO upload + render)
                                                  |
                                          PlaybackState (index tracking)
                                                  |
                                          MainWindow (signal routing)
                                                  |
                                          CodePanel (read-only display)
```

### Key Architectural Characteristics

| Characteristic | Current State | Editing Impact |
|----------------|---------------|----------------|
| `MoveInstruction` | `frozen=True` dataclass | Cannot mutate in place -- need mutable edit model |
| `RobTarget` | `frozen=True` dataclass | Cannot modify pos/orient in place |
| `ParseResult` | Non-frozen, but holds frozen items | Holds immutable move list items |
| Data flow | One-way: parse -> build -> render | Must become bidirectional: edit -> rebuild -> re-render |
| Source text | Stored as `source_text` string in ParseResult | Export requires patching original source, not regenerating |
| GL geometry | Rebuilt entirely on each `update_scene()` call | Acceptable for edit workflow (not real-time animation) |
| PlaybackState | Owns `_moves: list[MoveInstruction]` + current index | Must coordinate with EditModel on deletions/modifications |

## Recommended Architecture (Read-Write)

```
.mod file --> rapid_parser.parse_module() --> ParseResult (immutable snapshot)
                                                  |
                                                  v
                                          EditModel (mutable working copy)
                                           /    |    \
                                          /     |     \
                            PropertyPanel  PlaybackState  EditController
                            (inspect/edit) (index only)  (command dispatch)
                                          \     |     /
                                           \    |    /
                                          EditModel mutation
                                                  |
                                            to_parse_result()
                                                  |
                                          build_geometry() --> GL buffers
                                          
                          EditModel + source_text --> ModWriter --> new .mod file
```

### New Components Needed

| Component | Module Path | Responsibility |
|-----------|-------------|----------------|
| `EditModel` | `src/rapid_viewer/model/edit_model.py` | Mutable working copy of ParseResult with change tracking and selection state |
| `EditableMove` | `src/rapid_viewer/model/edit_model.py` | Mutable wrapper around MoveInstruction fields (inner class or same module) |
| `EditController` | `src/rapid_viewer/model/edit_controller.py` | Command dispatch: modify, delete, scene rebuild trigger |
| `PropertyPanel` | `src/rapid_viewer/ui/property_panel.py` | QWidget showing/editing waypoint properties (pos, speed, zone, laser) |
| `ModWriter` | `src/rapid_viewer/export/mod_writer.py` | Generate .mod source by patching original source text with edits |

### Existing Components to Modify

| Component | File | Changes Needed |
|-----------|------|----------------|
| `MainWindow` | `ui/main_window.py` | Add PropertyPanel to layout (3-way splitter), wire EditModel signals, add File > Save As menu action, instantiate EditController |
| `ToolpathGLWidget` | `renderer/toolpath_gl_widget.py` | Multi-select support (Ctrl+click), visual feedback for selected set, emit modifier key state with waypoint_clicked |
| `PlaybackState` | `ui/playback_state.py` | No structural changes -- continues to track index. MainWindow updates its move list when EditModel changes. |
| `geometry_builder` | `renderer/geometry_builder.py` | No changes. Already accepts ParseResult; EditModel produces compatible output via `to_parse_result()`. |
| `CodePanel` | `ui/code_panel.py` | Optional: highlight modified/deleted lines with different background color |

## Component Design Details

### 1. EditModel -- The Central Mutable State

The core architectural addition. `MoveInstruction` is `frozen=True`, so mutations require a mutable wrapper.

```python
# src/rapid_viewer/model/edit_model.py

@dataclass
class EditableMove:
    """Mutable wrapper around MoveInstruction fields.
    
    Stores original MoveInstruction for diff tracking and export patching.
    Mutable copies of all user-editable fields.
    """
    original: MoveInstruction
    index: int                          # Position in original move list
    # Mutable editable copies
    pos: np.ndarray | None              # shape (3,), from original.target.pos
    orient: np.ndarray | None           # shape (4,), from original.target.orient
    speed: str                          # e.g. "v100"
    zone: str                           # e.g. "z10", "fine"
    laser_on: bool
    deleted: bool = False
    
    @property
    def is_modified(self) -> bool:
        """True if any field differs from original."""
        ...
    
    def to_move_instruction(self) -> MoveInstruction:
        """Reconstruct frozen MoveInstruction from current mutable state.
        
        Creates new RobTarget with modified pos if needed, then builds
        new MoveInstruction with all current field values.
        """
        ...


class EditModel(QObject):
    """Mutable working copy of parsed toolpath data.
    
    Single source of truth for:
    - Which moves exist (including deletions)
    - Current field values for each move
    - Which moves are selected
    
    Signals:
        move_modified(int)       -- A single move at index was edited
        move_deleted(int)        -- A move at index was marked deleted
        model_changed()          -- Any structural change requiring full rebuild
        selection_changed(list)  -- Selected indices changed
    """
    move_modified = pyqtSignal(int)
    move_deleted = pyqtSignal(int)
    model_changed = pyqtSignal()
    selection_changed = pyqtSignal(list)
    
    def __init__(self, parse_result: ParseResult):
        self._original = parse_result
        self._moves: list[EditableMove] = [
            EditableMove(m, i, ...) for i, m in enumerate(parse_result.moves)
        ]
        self._selected_indices: list[int] = []
    
    # -- Read API (consumed by PropertyPanel, PlaybackState, ModWriter) --
    
    def active_moves(self) -> list[MoveInstruction]:
        """Return non-deleted moves as frozen MoveInstructions."""
        return [m.to_move_instruction() for m in self._moves if not m.deleted]
    
    def to_parse_result(self) -> ParseResult:
        """Build ParseResult-compatible object for geometry_builder.
        
        Uses dataclasses.replace() on original ParseResult with
        moves=self.active_moves(). Preserves targets dict, source_text, etc.
        """
        ...
    
    def get_move(self, index: int) -> EditableMove | None:
        """Get EditableMove by index for PropertyPanel display."""
        ...
    
    def selected_moves(self) -> list[EditableMove]:
        """Return currently selected EditableMoves."""
        ...
    
    # -- Write API (called by EditController) --
    
    def modify_position(self, index: int, offset: np.ndarray) -> None: ...
    def set_speed(self, index: int, speed: str) -> None: ...
    def set_zone(self, index: int, zone: str) -> None: ...
    def set_laser(self, index: int, on: bool) -> None: ...
    def delete_move(self, index: int) -> None: ...
    def select(self, indices: list[int]) -> None: ...
    def toggle_select(self, index: int) -> None:
        """Add/remove index from selection (for Ctrl+click)."""
        ...
```

**Design rationale:**
- Keeps existing frozen dataclasses untouched -- zero risk of breaking parser or renderer
- `to_parse_result()` produces input compatible with existing `build_geometry()` -- zero renderer changes needed
- Change tracking is per-move via `is_modified` property, enabling surgical export patching
- Signal-based notification matches the existing Qt signal pattern throughout the codebase

### 2. EditController -- Command Dispatch and Scene Rebuild

Thin layer between UI actions and EditModel mutations. Owns the "edit -> rebuild -> render" cycle.

```python
# src/rapid_viewer/model/edit_controller.py

class EditController(QObject):
    """Dispatches edit commands to EditModel and triggers scene rebuild.
    
    All edit operations flow through here:
    PropertyPanel -> EditController -> EditModel -> signal -> scene rebuild
    
    This indirection enables:
    - Future undo/redo stack (record commands before executing)
    - Debounced scene rebuild (batch rapid edits)
    - Consistent validation before mutation
    """
    
    def __init__(self, edit_model: EditModel, gl_widget, playback_state):
        self._model = edit_model
        self._gl_widget = gl_widget
        self._playback_state = playback_state
        self._model.model_changed.connect(self._rebuild_scene)
        self._model.move_modified.connect(self._on_move_modified)
    
    def apply_offset(self, indices: list[int], dx: float, dy: float, dz: float):
        """Apply position offset to selected moves. Emits model_changed."""
        offset = np.array([dx, dy, dz], dtype=np.float64)
        for idx in indices:
            self._model.modify_position(idx, offset)
        self._model.model_changed.emit()
    
    def change_speed(self, indices: list[int], speed: str): ...
    def change_zone(self, indices: list[int], zone: str): ...
    def toggle_laser(self, indices: list[int], on: bool): ...
    
    def delete_moves(self, indices: list[int]):
        """Mark moves as deleted. Geometry reconnects automatically."""
        for idx in sorted(indices, reverse=True):
            self._model.delete_move(idx)
        self._model.model_changed.emit()
    
    def _rebuild_scene(self):
        """Regenerate geometry from edited model and update GL + playback."""
        result = self._model.to_parse_result()
        self._gl_widget.update_scene(result)
        self._playback_state.set_moves(result.moves)
    
    def _on_move_modified(self, index: int):
        """Single move changed -- still do full rebuild (fast enough)."""
        self._rebuild_scene()
```

### 3. PropertyPanel -- Waypoint Inspector/Editor

```
+--------------------------------------------------+
| Property Panel                                    |
|--------------------------------------------------|
| Move Type: MoveL          Source: Line 42         |
|--------------------------------------------------|
| Position                                          |
|  X:  150.000  mm                                  |
|  Y:  200.500  mm                                  |
|  Z:   50.250  mm                                  |
|--------------------------------------------------|
| Offset (additive)                                 |
|  dX: [________]  dY: [________]  dZ: [________]  |
|  [Apply Offset]  [Apply Offset to All Selected]   |
|--------------------------------------------------|
| Orientation (read-only)                           |
|  q1: 0.707  q2: 0.000  q3: 0.707  q4: 0.000    |
|--------------------------------------------------|
| Speed: [v100     v]   Zone: [z10      v]         |
|--------------------------------------------------|
| Laser: [x] ON                                    |
|--------------------------------------------------|
| [Delete Waypoint(s)]                             |
+--------------------------------------------------+
```

Key design decisions:
- **Offset input, not absolute position editing.** Robot engineers think in offsets ("move this 2mm in Z"). Direct position editing risks typos that could send the robot into a table. Offset input is safer and matches the domain mental model.
- **"Apply to All Selected" button** enables batch offset operations. Select 10 waypoints, apply Z+5mm to all at once.
- **Speed/Zone as QComboBox** with common RAPID values (v5, v10, v50, v100, v500, v1000, v2000, v5000 for speed; fine, z0, z1, z5, z10, z50, z100, z200 for zone). Also allow free text entry for custom speed data.
- **Orientation is read-only.** Quaternion editing is error-prone and rarely needed in toolpath correction. Out of scope for v1.1.

### 4. ModWriter -- .mod File Export

**Critical design decision: Patch original source, do not regenerate.**

```python
# src/rapid_viewer/export/mod_writer.py

class ModWriter:
    """Generate .mod file by patching original source with edits.
    
    Strategy:
    - Start with ParseResult.source_text (original file content)
    - For each EditableMove where is_modified==True:
        - If position changed: patch the robtarget declaration line
        - If speed/zone changed: patch the MoveL/MoveJ instruction line
        - If laser changed: insert/modify SetDO before the move line
    - For each deleted move: remove or comment out the line
    - Write patched source to output file
    
    Line patching order: process from bottom of file upward so that
    line number references remain valid as earlier lines are modified.
    """
    
    def export(self, edit_model: EditModel, output_path: Path) -> None: ...
    
    def _build_patches(self, edit_model: EditModel) -> list[Patch]: ...
    
    def _patch_robtarget_pos(self, line: str, new_pos: np.ndarray) -> str:
        """Replace [x,y,z] in a robtarget declaration line."""
        ...
    
    def _patch_move_speed_zone(self, line: str, speed: str, zone: str) -> str:
        """Replace speed and zone tokens in a move instruction line."""
        ...
    
    def _delete_line(self, line: str) -> str:
        """Comment out a line: prepend '! [DELETED] '."""
        ...
```

**Why patching, not regeneration:**
- Original .mod files contain comments, formatting, non-move statements (variable declarations, IF/ELSE logic, custom PROC structure, header comments) that the parser intentionally skips
- Regenerating would lose all non-parsed content
- Robot engineers need to see their original code structure preserved
- `MoveInstruction.source_line` and `RobTarget.source_line` already track positions in original source
- Apply patches bottom-to-top so earlier patches do not shift line numbers of later patches

**Handling position edits -- Offs() vs. named robtarget:**
- If the original target was a named robtarget (e.g., `p10`), patch the robtarget declaration line
- If the original target was `Offs(base, dx, dy, dz)`, update the offset values in the move instruction line
- If the original target was inline `[[x,y,z],...]`, patch the inline bracket data

### 5. MainWindow Layout Changes

Current layout:
```
+-------------------+----------------------+
|  GL Widget (60%)  |  Code Panel (40%)    |
+-------------------+----------------------+
|  Playback Toolbar                        |
+------------------------------------------+
```

Proposed layout:
```
+-------------------+-----------+----------+
|  GL Widget (55%)  | Property  | Code     |
|                   | Panel     | Panel    |
|                   | (20%)     | (25%)    |
+-------------------+-----------+----------+
|  Playback Toolbar                        |
+------------------------------------------+
```

**Implementation:** The current QSplitter is 2-way horizontal. Change to 3-way by inserting PropertyPanel between GL widget and CodePanel. Splitter sizes: `[550, 200, 250]`.

## Integration Points with Existing Modules

### Integration 1: EditModel replaces PlaybackState as data owner

**Current flow:**
```
ParseResult.moves --> PlaybackState._moves (owns the list)
                      PlaybackState._current_index (owns the index)
```

**New flow:**
```
ParseResult --> EditModel._moves (owns the editable data)
                    |
                    v
                EditModel.active_moves() --> PlaybackState._moves (receives filtered list)
                                             PlaybackState._current_index (still owns index)
```

PlaybackState does NOT change structurally. It still receives a `list[MoveInstruction]` via `set_moves()`. The difference is that MainWindow calls `set_moves(edit_model.active_moves())` instead of `set_moves(parse_result.moves)`. PlaybackState only tracks the index.

### Integration 2: EditModel <-> geometry_builder (no changes needed)

The existing `build_geometry(result: ParseResult) -> GeometryBuffers` API is unchanged. EditModel produces a compatible ParseResult via `to_parse_result()`. This is the key architectural win: the entire rendering pipeline is reused without modification.

### Integration 3: ToolpathGLWidget selection enhancement

**Current:** `waypoint_clicked` signal emits `int` (single index). Used for playback navigation.

**Addition for editing:**
- Ctrl+click: toggle selection (add/remove from selected set)
- Plain click: replace selection (single select, same as current behavior)
- Shift+click: range select (optional, lower priority)

Implementation in `mouseReleaseEvent`:
```python
# Check Qt.KeyboardModifier.ControlModifier
if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
    self.waypoint_ctrl_clicked.emit(picked_index)  # new signal
else:
    self.waypoint_clicked.emit(picked_index)  # existing signal
```

MainWindow routes:
- `waypoint_clicked` -> `edit_model.select([index])` + `playback_state.set_index(index)`
- `waypoint_ctrl_clicked` -> `edit_model.toggle_select(index)`

### Integration 4: PropertyPanel <-> EditModel (bidirectional)

```
EditModel.selection_changed --> PropertyPanel.update_display()
PropertyPanel.offset_applied --> EditController.apply_offset() --> EditModel.modify_position()
PropertyPanel.speed_changed  --> EditController.change_speed()  --> EditModel.set_speed()
PropertyPanel.zone_changed   --> EditController.change_zone()   --> EditModel.set_zone()
PropertyPanel.laser_toggled  --> EditController.toggle_laser()  --> EditModel.set_laser()
PropertyPanel.delete_requested --> EditController.delete_moves() --> EditModel.delete_move()
```

### Integration 5: ModWriter uses original source_text + EditModel diffs

```
ParseResult.source_text (original file)  +  EditModel._moves (with is_modified flags)
    |                                            |
    v                                            v
ModWriter._build_patches() --> list of (line_number, old_text, new_text)
    |
    v (apply patches bottom-to-top)
Patched source text --> write to file
```

### Integration 6: MainWindow menu for Save As

New menu action in `_setup_menu()`:
```python
save_as_action = QAction("Save &As...", self)
save_as_action.setShortcut("Ctrl+Shift+S")
save_as_action.triggered.connect(self._save_as)
# Disabled until a file is loaded and EditModel exists
save_as_action.setEnabled(False)
```

`_save_as()` calls `QFileDialog.getSaveFileName()` then `ModWriter().export(self._edit_model, path)`.

**Always "Save As", never overwrite.** Robot engineers must keep the original file intact. The original .mod may be on a network share connected to a live robot controller.

## Data Flow Changes Summary

### v1.0 Read-Only Flow (unchanged, still works)
```
.mod --> parse_module() --> ParseResult --> build_geometry() --> GL buffers
                                       \-> PlaybackState (index)
                                       \-> CodePanel (source_text)
```

### v1.1 Read-Write Flow (new)
```
.mod --> parse_module() --> ParseResult --> EditModel (mutable copy)
                                               |
                          +--------------------+-----------------------+
                          |                    |                       |
                    PropertyPanel        PlaybackState           EditController
                    (inspect/edit)      (index tracking)        (command dispatch)
                          |                                           |
                          +---------> EditModel mutation <------------+
                                           |
                                     to_parse_result()
                                           |
                                     build_geometry()
                                           |
                                     update_scene() --> GL buffers
                                           
                          EditModel + source_text --> ModWriter --> new .mod file
```

## Patterns to Follow

### Pattern 1: Immutable Core, Mutable Wrapper
Keep parser output (`MoveInstruction`, `RobTarget`) frozen. Wrap with mutable `EditableMove` for editing. Parser correctness is proven; editing bugs must not corrupt the parse layer.

### Pattern 2: Signal-Driven UI Updates
All state changes emit Qt signals. UI components react to signals, never poll. Existing codebase uses this pattern consistently (`PlaybackState.current_changed`, `waypoint_clicked`).

### Pattern 3: Source Patching for Export
Modify original .mod source text at known line positions rather than regenerating. Preserves comments, formatting, non-move code. Apply patches bottom-to-top to maintain line number validity.

### Pattern 4: Full Scene Rebuild on Edit
Call `build_geometry()` + `update_scene()` after every edit. Toolpath files have hundreds to low-thousands of moves; full rebuild is <50ms. Incremental VBO patching adds complexity for negligible gain.

### Pattern 5: Controller Mediates All Mutations
PropertyPanel never calls EditModel directly. All mutations go through EditController, which handles validation, batching, and scene rebuild triggering. This keeps the door open for undo/redo.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Making Parser Dataclasses Mutable
Removing `frozen=True` from `MoveInstruction` or `RobTarget` would break parser tests, hash-based `targets` dict lookups, and risk editing bugs corrupting parse state. Use `EditableMove` wrapper instead.

### Anti-Pattern 2: In-Place Source Text Mutation During Editing
Mutating `source_text` string as edits happen (before export) causes line numbers to shift after insertions/deletions, invalidating all `source_line` references. Collect patches and apply at export time only.

### Anti-Pattern 3: Dual Source of Truth for Move List
Both `PlaybackState._moves` and `EditModel._moves` holding separate copies leads to desynchronization on edits. EditModel is the single source; PlaybackState receives filtered lists from it.

### Anti-Pattern 4: Direct GL Widget Mutation from PropertyPanel
PropertyPanel calling `gl_widget.update_scene()` directly bypasses EditModel, loses change tracking, and breaks undo possibility. Always go through EditController.

### Anti-Pattern 5: Absolute Position Editing in UI
Exposing raw X/Y/Z input fields for absolute position invites dangerous typos. Robot engineers think in offsets. Use offset-only input with clear "Apply" action.

## Suggested Build Order (Phase Dependencies)

```
Phase 1: EditModel + EditableMove           [NO dependencies on new code]
  - Unit-testable in isolation
  - Depends only on existing parser tokens
  - Deliverables: edit_model.py with full test coverage

Phase 2: PropertyPanel (read-only first)     [Depends on Phase 1]
  - Display selected waypoint properties
  - Wire to EditModel.selection_changed
  - MainWindow layout change: 3-way splitter
  - Deliverables: property_panel.py (display only), main_window.py changes

Phase 3: Editing + Selection                 [Depends on Phases 1 & 2]
  - EditController with offset/speed/zone/laser/delete commands
  - PropertyPanel edit widgets (offset input, speed/zone combos, delete button)
  - Multi-select in ToolpathGLWidget (Ctrl+click)
  - Deliverables: edit_controller.py, property_panel.py (full), gl_widget changes

Phase 4: ModWriter (export)                  [Depends on Phase 1]
  - Source text patching engine
  - Save As menu action in MainWindow
  - Can be built in parallel with Phase 3 (only depends on EditModel)
  - Deliverables: mod_writer.py, main_window.py Save As action
```

**Phase ordering rationale:**
1. EditModel first because PropertyPanel, EditController, and ModWriter all depend on it
2. PropertyPanel read-only validates the EditModel-to-UI signal wiring without mutation complexity
3. Editing features need both EditModel and PropertyPanel in place
4. Export only reads final state; no other component depends on it. Can parallelize with Phase 3.

## Scalability Considerations

| Concern | 200 moves (typical) | 5000 moves (large) | Mitigation |
|---------|---------------------|---------------------|------------|
| Full rebuild time | <10ms | ~50ms | Acceptable. No incremental updates needed. |
| EditableMove memory | ~50KB | ~1.2MB | Negligible |
| Source patching (export) | <5ms | ~20ms | Line-by-line scan is fast for text |
| Multi-select highlight | Trivial | Build batch highlight VBO | Upload all selected positions in single VBO, not one-at-a-time |

## Sources

- Direct codebase analysis of all existing modules (HIGH confidence)
- Qt6 signal/slot pattern: consistent with existing codebase patterns (HIGH confidence)
- `dataclasses.replace()` for creating modified frozen instances: Python stdlib (HIGH confidence)
- Source patching approach: standard technique for editors that must preserve formatting (HIGH confidence)

---
*Architecture research for: ABB RAPID Toolpath Viewer v1.1 Toolpath Editing*
*Researched: 2026-04-01*
