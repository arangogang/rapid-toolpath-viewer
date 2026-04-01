# Phase 4: Edit Infrastructure, Selection, and Inspection - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Mutable edit model with undo/redo infrastructure, waypoint selection (single and multi-select) in the 3D viewer, and a read-only property inspection panel. No actual edit operations yet -- Phase 5 adds modifications that use the infrastructure built here.

</domain>

<decisions>
## Implementation Decisions

### Selection Model Design
- **D-01:** Create a new `SelectionState` class (QObject) separate from `PlaybackState`. PlaybackState continues to manage playback cursor (current_index). SelectionState manages a `set[int]` of selected waypoint indices.
- **D-02:** Plain click on a waypoint: updates both PlaybackState.current_index AND replaces SelectionState to just that point. Shift/Ctrl+click: toggles the clicked point in SelectionState, and moves PlaybackState.current_index to the clicked point. Code panel always follows current_index.

### Property Panel Placement
- **D-03:** Property panel placed below the code panel in the right pane (vertical QSplitter within the existing right side of the horizontal QSplitter). Layout: [3D Viewport | Code Panel / Property Panel].
- **D-04:** When multiple waypoints are selected, property panel shows the last-clicked point's properties (current_index). Header displays selection count (e.g., "3 points selected"). Phase 5 batch edits will apply to all selected points.

### Selection Visual Style
- **D-05:** Selection visual feedback uses color changes only, no size or shape changes. Unselected markers: yellow (existing). Selected markers: cyan or white. Current marker (last clicked): red/magenta (existing highlight color). Path lines remain unchanged.

### EditModel Structure
- **D-06:** EditModel holds a list of mutable `EditPoint` objects, each wrapping one frozen `MoveInstruction`. EditPoint has mutable fields: `pos` (np.ndarray copy), `speed`, `zone`, `laser_on`, `deleted` flag. Original `MoveInstruction` kept as reference for diff/export.
- **D-07:** EditModel owns the `QUndoStack`. All mutations go through EditModel methods that internally create QUndoCommands. MainWindow connects Edit menu Undo/Redo actions to `undo_stack.undo()`/`redo()`.
- **D-08:** Undo/Redo actions visible in Edit menu from Phase 4 (Ctrl+Z/Ctrl+Y), but disabled until edits are made in Phase 5.
- **D-09:** Title bar shows dirty-state indicator (asterisk) when EditModel has uncommitted changes (any EditPoint differs from its original).

### Claude's Discretion
- Signal names for SelectionState (e.g., `selection_changed`, `selection_cleared`)
- Exact color values for selected vs current markers (within the cyan/white and red/magenta guidance)
- Internal EditPoint field layout and helper methods
- QUndoCommand subclass naming and structure (placeholder commands for Phase 4)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Model
- `src/rapid_viewer/parser/tokens.py` -- Frozen dataclasses (MoveInstruction, RobTarget, ParseResult) that EditModel must wrap
- `src/rapid_viewer/ui/playback_state.py` -- Existing PlaybackState pattern; SelectionState should follow similar QObject+signal design

### Rendering
- `src/rapid_viewer/renderer/toolpath_gl_widget.py` -- GL widget with existing waypoint_clicked signal, highlight rendering, and marker color handling
- `src/rapid_viewer/renderer/geometry_builder.py` -- GeometryBuffers vertex layout [x,y,z,r,g,b] float32; marker colors set here

### UI Integration
- `src/rapid_viewer/ui/main_window.py` -- MainWindow signal wiring, QSplitter layout, load_file() distribution
- `src/rapid_viewer/ui/code_panel.py` -- CodePanel highlight_line() integration point

### Architecture
- `.planning/codebase/ARCHITECTURE.md` -- Data flow, signal patterns, layer boundaries
- `.planning/codebase/STRUCTURE.md` -- File locations and module boundaries
- `.planning/REQUIREMENTS.md` -- EDIT-01, EDIT-02, SEL-01, SEL-02, INSP-01 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PlaybackState` (ui/playback_state.py): QObject with pyqtSignal pattern -- SelectionState should mirror this design
- `ToolpathGLWidget.waypoint_clicked(int)` signal: Already emits clicked waypoint index via ray-cast picking (20px threshold)
- `ToolpathGLWidget._highlight_index` and highlight marker draw pass: Pattern for rendering special marker colors
- `MainWindow._on_waypoint_changed()`: Existing handler that updates GL highlight + code panel -- extend for selection

### Established Patterns
- Qt signal/slot for all state changes (no direct method calls between components)
- Lazy import of renderer module inside MainWindow.__init__() to isolate OpenGL from tests
- `_gl_ready` guard flag prevents GL calls before context initialization
- `blockSignals()` to prevent cascading during programmatic updates
- Geometry re-upload is full (not incremental) via build_geometry() pattern

### Integration Points
- MainWindow: New property panel widget added to right-side QSplitter; Edit menu for Undo/Redo actions
- ToolpathGLWidget: Extend mouse click handler for Shift/Ctrl modifiers; add multi-highlight rendering
- CodePanel: May need multi-line highlight support for multi-selected points
- PlaybackToolbar: No changes expected (playback stays independent)

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 04-edit-infrastructure-selection-and-inspection*
*Context gathered: 2026-04-01*
