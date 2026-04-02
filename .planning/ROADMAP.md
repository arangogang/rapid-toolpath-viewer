# Roadmap: ABB RAPID Toolpath Viewer

## Milestones

- v1.0 MVP - Phases 1-3 (shipped 2026-03-30)
- v1.1 Toolpath Editing - Phases 4-6 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

<details>
<summary>v1.0 MVP (Phases 1-3) - SHIPPED 2026-03-30</summary>

- [x] **Phase 1: Parser and File Loading** - Parse .mod files into structured data with all move types, robtargets, and source line tracking (completed 2026-03-30)
- [x] **Phase 2: 3D Viewer and Camera** - Render toolpaths in 3D with VBO pipeline and mouse-driven camera controls (completed 2026-03-30)
- [x] **Phase 3: Playback, Code Panel, and Linking** - Step through waypoints, view RAPID code, and navigate bidirectionally between 3D view and source (completed 2026-03-30)

</details>

### v1.1 Toolpath Editing (In Progress)

**Milestone Goal:** Add toolpath selection, inspection, modification, and .mod export so engineers can make surgical corrections before uploading to ABB controllers.

- [ ] **Phase 4: Edit Infrastructure, Selection, and Inspection** - Mutable edit model with undo/redo, waypoint selection with multi-select, and read-only property panel
- [ ] **Phase 5: Modification Operations** - Coordinate offset, speed/zone/laser editing, waypoint deletion, and point insertion via QUndoCommands
- [ ] **Phase 6: Export** - Save modified .mod file via source text patching that preserves original formatting and comments

## Phase Details

<details>
<summary>v1.0 MVP Phase Details (Phases 1-3)</summary>

### Phase 1: Parser and File Loading
**Goal**: User can open a .mod file and the application correctly extracts all move instructions, robtarget positions, and source line mappings into a structured data model
**Depends on**: Nothing (first phase)
**Requirements**: FILE-01, FILE-02, PARS-01, PARS-02, PARS-03, PARS-04, PARS-05, PARS-06, PARS-07
**Success Criteria** (what must be TRUE):
  1. User can open a .mod file via file dialog and the filename appears in the title bar
  2. All four move types (MoveL, MoveJ, MoveC, MoveAbsJ) are parsed from a test .mod file with correct robtarget extraction
  3. Multiline robtarget declarations (split across lines with semicolon termination) parse correctly without data loss
  4. Each parsed move instruction carries its source line number, enabling downstream code linking
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md -- Project skeleton, data model contracts, regex patterns, test infrastructure
- [x] 01-02-PLAN.md -- RAPID parser implementation (TDD: tokenizer, two-pass parser, all move types)
- [x] 01-03-PLAN.md -- PyQt6 MainWindow with file dialog and title bar update

### Phase 2: 3D Viewer and Camera
**Goal**: User sees the parsed toolpath rendered in 3D with move-type visual distinction, waypoint markers, and can freely navigate the view with mouse controls
**Depends on**: Phase 1
**Requirements**: REND-01, REND-02, REND-03, REND-05, CAM-01, CAM-02, CAM-03
**Success Criteria** (what must be TRUE):
  1. Toolpath renders in 3D with visual distinction between move types (MoveL solid lines, MoveJ dashed lines, MoveC arc segments)
  2. Each waypoint (robtarget) is visible as a marker in the 3D view
  3. User can orbit (left-drag), zoom (scroll), and pan (middle-drag) the 3D view with responsive mouse controls
  4. XYZ coordinate axes indicator is visible in the viewport corner for spatial orientation
  5. Rendering uses OpenGL 3.3 Core Profile with VBO/VAO architecture (no immediate mode)
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md -- Dependencies, geometry builder (ParseResult->vertex arrays, arc tessellation), shader source constants
- [x] 02-02-PLAN.md -- ArcballCamera (orbit/pan/zoom math, view/projection/mvp matrices, unit tests)
- [x] 02-03-PLAN.md -- ToolpathGLWidget (QOpenGLWidget VBO/VAO pipeline, mouse events, axes indicator, MainWindow wiring)
- [x] 02-04-PLAN.md -- Visual verification checkpoint (human confirms render quality and camera interaction)

### Phase 3: Playback, Code Panel, and Linking
**Goal**: User can step through waypoints, view syntax-highlighted RAPID code, and click in either the 3D view or code panel to navigate bidirectionally -- completing the core verification workflow
**Depends on**: Phase 2
**Requirements**: PLAY-01, PLAY-02, PLAY-03, PLAY-04, PLAY-05, PLAY-06, PLAY-07, CODE-01, CODE-02, CODE-03, LINK-01, LINK-02, PARS-08, REND-04
**Success Criteria** (what must be TRUE):
  1. User can step forward/backward through waypoints and the current point is visually highlighted in the 3D view with position indicator (N/M)
  2. User can press Play to auto-advance through waypoints sequentially
  3. RAPID source code is displayed in a side panel with syntax highlighting for keywords (MoveL, MoveJ, PROC, etc.)
  4. Clicking a waypoint in the 3D view scrolls the code panel to the corresponding source line, and clicking a Move line in the code panel selects the corresponding 3D waypoint
  5. User can select which PROC to display when a .mod file contains multiple procedures
  6. User can adjust playback speed (0.5x ~ 10x) via slider during auto-play
  7. User can drag a scrubber slider to instantly jump to any position in the path
**Plans**: 5 plans

Plans:
- [x] 03-01-PLAN.md -- PlaybackState model + parser PROC range extraction
- [x] 03-02-PLAN.md -- RapidHighlighter syntax highlighter + CodePanel widget
- [x] 03-03-PLAN.md -- PlaybackToolbar + GL widget highlight/picking/triads
- [x] 03-04-PLAN.md -- MainWindow integration (QSplitter, signal wiring, PROC selector, linking)
- [x] 03-05-PLAN.md -- Visual verification checkpoint

</details>

### Phase 4: Edit Infrastructure, Selection, and Inspection
**Goal**: User can select single or multiple waypoints in the 3D viewer (with Shift/Ctrl modifiers) and see their properties displayed in a read-only inspection panel, backed by a mutable edit model with undo/redo wired from day one
**Depends on**: Phase 3
**Requirements**: EDIT-01, EDIT-02, SEL-01, SEL-02, INSP-01
**Success Criteria** (what must be TRUE):
  1. User can click a waypoint in the 3D viewer to select it, and the selection is visually distinct from unselected points with corresponding RAPID code line highlighted
  2. User can Shift+click or Ctrl+click to select multiple waypoints, with all selected points visually distinguished in the 3D view
  3. Selected waypoint's properties (X/Y/Z coordinates, speed, zone value, laser on/off state) are displayed in a property panel alongside the 3D viewer
  4. Undo (Ctrl+Z) and Redo (Ctrl+Y) actions are available in the Edit menu (disabled until edits are made in Phase 5)
  5. Title bar shows dirty-state indicator (asterisk) when the edit model has uncommitted changes
**Plans**: 3 plans

Plans:
- [x] 04-01-PLAN.md -- SelectionState + EditModel/EditPoint data models with TDD tests
- [x] 04-02-PLAN.md -- PropertyPanel read-only inspection widget with tests
- [ ] 04-03-PLAN.md -- GL widget multi-select rendering + MainWindow integration + visual verification

### Phase 5: Modification Operations
**Goal**: User can modify selected waypoints -- adjust coordinates via offset input, change speed/zone/laser properties, delete waypoints with topology options, and insert new points by offset -- with all operations undoable
**Depends on**: Phase 4
**Requirements**: MOD-01, MOD-02, MOD-03, MOD-04
**Success Criteria** (what must be TRUE):
  1. User can enter X/Y/Z offset values to move a selected waypoint, and the 3D view updates immediately to show the new position
  2. User can change speed, zone value, and laser on/off state of a selected waypoint via the property panel
  3. User can delete a waypoint and choose whether to reconnect the path (maintain continuity) or break it (insert laser-off gap), with the 3D view updating accordingly
  4. User can continuously add new waypoints by specifying offset from the last point, with properties copied from the source point
  5. Every modification can be undone with Ctrl+Z and redone with Ctrl+Y, restoring both the data and the 3D view
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md -- QUndoCommand subclasses + EditModel mutation methods + tests
- [x] 05-02-PLAN.md -- PropertyPanel editable conversion (offset inputs, speed/zone/laser, delete/insert buttons)
- [ ] 05-03-PLAN.md -- MainWindow wiring + geometry rebuild + visual verification

### Phase 6: Export
**Goal**: User can save the modified toolpath as a new .mod file that preserves the original file's formatting, comments, and non-move RAPID code
**Depends on**: Phase 5
**Requirements**: EXP-01
**Success Criteria** (what must be TRUE):
  1. User can use File > Save As (Ctrl+Shift+S) to export the modified .mod file to a new location (never overwrites the original)
  2. The exported .mod file preserves all original comments, IF/WHILE logic, custom PROC structure, and formatting -- only edited values differ from the original
  3. The exported .mod file can be reloaded in the viewer and shows the modifications correctly

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Parser and File Loading | v1.0 | 3/3 | Complete | 2026-03-30 |
| 2. 3D Viewer and Camera | v1.0 | 4/4 | Complete | 2026-03-30 |
| 3. Playback, Code Panel, and Linking | v1.0 | 5/5 | Complete | 2026-03-30 |
| 4. Edit Infrastructure, Selection, and Inspection | v1.1 | 1/3 | In Progress|  |
| 5. Modification Operations | v1.1 | 2/3 | In Progress|  |
| 6. Export | v1.1 | 0/0 | Not started | - |
