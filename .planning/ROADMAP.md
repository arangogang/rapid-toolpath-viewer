# Roadmap: ABB RAPID Toolpath Viewer

## Overview

This project delivers a Windows desktop application that opens ABB RAPID .mod files and renders 3D toolpaths with bidirectional code-to-3D linking. The build follows the data dependency chain: parser first (all other components consume parsed data), then 3D rendering with camera controls, then the interactive features (playback, code panel, linking) that tie everything together into the core verification workflow.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Parser and File Loading** - Parse .mod files into structured data with all move types, robtargets, and source line tracking (completed 2026-03-30)
- [x] **Phase 2: 3D Viewer and Camera** - Render toolpaths in 3D with VBO pipeline and mouse-driven camera controls
- [x] **Phase 3: Playback, Code Panel, and Linking** - Step through waypoints, view RAPID code, and navigate bidirectionally between 3D view and source (completed 2026-03-30)

## Phase Details

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
- [x] 01-01-PLAN.md — Project skeleton, data model contracts, regex patterns, test infrastructure
- [x] 01-02-PLAN.md — RAPID parser implementation (TDD: tokenizer, two-pass parser, all move types)
- [x] 01-03-PLAN.md — PyQt6 MainWindow with file dialog and title bar update

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
- [x] 02-01-PLAN.md — Dependencies, geometry builder (ParseResult->vertex arrays, arc tessellation), shader source constants
- [x] 02-02-PLAN.md — ArcballCamera (orbit/pan/zoom math, view/projection/mvp matrices, unit tests)
- [x] 02-03-PLAN.md — ToolpathGLWidget (QOpenGLWidget VBO/VAO pipeline, mouse events, axes indicator, MainWindow wiring)
- [x] 02-04-PLAN.md — Visual verification checkpoint (human confirms render quality and camera interaction)

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
- [x] 03-01-PLAN.md — PlaybackState model + parser PROC range extraction
- [x] 03-02-PLAN.md — RapidHighlighter syntax highlighter + CodePanel widget
- [x] 03-03-PLAN.md — PlaybackToolbar + GL widget highlight/picking/triads
- [x] 03-04-PLAN.md — MainWindow integration (QSplitter, signal wiring, PROC selector, linking)
- [x] 03-05-PLAN.md — Visual verification checkpoint

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Parser and File Loading | 3/3 | Complete   | 2026-03-30 |
| 2. 3D Viewer and Camera | 4/4 | Complete | 2026-03-30 |
| 3. Playback, Code Panel, and Linking | 5/5 | Complete | 2026-03-30 |
