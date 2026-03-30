# Project Research Summary

**Project:** ABB RAPID Toolpath Viewer
**Domain:** Desktop 3D toolpath visualization / robot program verification
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

This is a Windows desktop application for verifying ABB RAPID robot programs before deployment. The core workflow is: open a `.mod` file, see the 3D toolpath instantly, and navigate bidirectionally between waypoints in the 3D view and corresponding lines in the RAPID source code. The closest analog in the broader tooling landscape is NC Viewer for G-code — instant, zero-config, focused on visual verification. The primary differentiator over RobotStudio and other OLP tools is zero setup time: no robot model import, no station creation, no license management.

The recommended approach is a clean four-layer architecture (Parser -> Model -> Renderer -> UI) built strictly in dependency order. The parser is a pure Python regex-based two-pass parser with no Qt or OpenGL dependencies, testable in isolation. The model holds parsed data and broadcasts changes via Qt signals. The OpenGL renderer consumes data from the model through a VBO-based pipeline using OpenGL 3.3 Core Profile shaders. Bidirectional code-to-3D linking is implemented through index maps built at parse time, not maintained separately at runtime.

The dominant risk is parser fragility: real-world `.mod` files split declarations across multiple lines and use inconsistent whitespace. A naive line-by-line parser produces silent data loss (points disappear with no error). The second-highest risk is building the OpenGL renderer with immediate mode (`glBegin`/`glEnd`) instead of VBOs — this performs fine on small test files and requires a complete rewrite when tested against production files with 2,000–10,000 points. Both risks must be addressed in Phase 1 and Phase 2 respectively, as retrofitting either requires architectural changes, not localized fixes.

## Key Findings

### Recommended Stack

The stack is defined by the user's explicit choices: Python 3.11+, PyQt6, and PyOpenGL. These are well-supported and integrate naturally. PyQt6's `QOpenGLWidget` provides the OpenGL surface; PyOpenGL 3.1.10 provides direct API access. The critical constraint is that PyQt6 on Windows creates an OpenGL Core Profile context by default, which means the fixed-function pipeline (glBegin/glEnd, glVertex, glLoadIdentity) will silently fail or crash. All rendering must use modern shaders, VBOs, and VAOs targeting OpenGL 3.3 Core Profile. There is no official ABB Python SDK for parsing `.mod` files from disk; a custom regex-based parser is the correct approach. `pyrr` provides 3D math (matrices, quaternions) and integrates natively with NumPy.

**Core technologies:**
- Python 3.11+: runtime — 3.11 provides significant performance gains; avoid 3.13 until C-extension deps confirm compatibility
- PyQt6 6.10.x: GUI framework — QOpenGLWidget for OpenGL surface, Qt signals for component coordination
- PyOpenGL 3.1.10: OpenGL bindings — direct API access; must use modern shader pipeline, not fixed-function
- PyOpenGL-accelerate 3.1.10: C-accelerated PyOpenGL — always install alongside; 2–5x speedup for array operations
- NumPy >=1.26: math and arrays — vertex buffers, coordinate transforms, robtarget data storage
- pyrr 0.10.3: 3D math — view/projection matrices, arcball camera, quaternion operations; NumPy-native
- uv: dependency management — faster than pip, lockfile support, reproducible builds

### Expected Features

All ten table-stakes features must ship in v1. The dependency chain dictates order: file loading and parsing must come first, then 3D rendering with camera controls, then step-through playback, and finally bidirectional code-to-3D linking. Code-to-3D linking is the highest-dependency feature and must come last among the table-stakes items. It is also the core value proposition per PROJECT.md.

**Must have (table stakes):**
- `.mod` file loading via file dialog — entry point to the application
- RAPID parser: MoveL, MoveJ, MoveC, MoveAbsJ extraction — covers 95%+ of real programs
- robtarget / jointtarget data parsing — raw material for visualization
- 3D path rendering with move-type distinction (MoveL=solid, MoveJ=dashed, MoveC=arc) — every competitor does this
- Waypoint markers at each robtarget — position identification
- Mouse camera controls (orbit, zoom, pan) — without these the 3D view is unusable
- XYZ coordinate axes indicator — spatial orientation reference
- Step forward/back through waypoints — sequential verification workflow
- RAPID code panel with syntax highlighting — code context alongside 3D view
- Bidirectional code-to-3D linking — the killer feature; click point to see code, click code to see point

**Should have (v1.x after validation):**
- TCP orientation frames at waypoints — catches orientation errors invisible in position-only views
- Playback animation with speed control — when step-through feels too slow for long programs
- Speed/zone data overlay — "why is this segment slow?"
- Multi-procedure support (PROC selection) — real files contain multiple routines
- Path statistics panel (length, point count, move breakdown) — low effort, high info value
- Search in code panel — when files exceed ~200 lines

**Defer (v2+):**
- Wobj frame visualization and coordinate transform — important but complex; data model must support it from day one even if rendering is deferred
- Export path as CSV/point cloud
- Simple STL workpiece overlay
- Multi-module loading
- Robot arm 3D model / kinematic simulation — explicit out-of-scope per PROJECT.md

### Architecture Approach

The application follows a strict four-layer MVP architecture: Parser (pure Python, no Qt) -> Model (Qt QObject with signals, no OpenGL) -> Renderer (OpenGL only, reads from model) -> UI (Qt widgets, no OpenGL). All cross-component communication flows through the ToolpathModel via Qt signals — views never talk to each other directly. Bidirectional code-to-3D linking is implemented through two dictionaries built at parse time (`line_to_waypoint` and `waypoint_to_line`), stored in the model, and queried by the controller when either a 3D point or a code line is clicked. The playback state machine is an enum-based FSM driven by QTimer, providing four states: IDLE, STOPPED, PLAYING, PAUSED.

**Major components:**
1. RapidParser (`parser/`) — pure Python regex two-pass parser; produces immutable ParseResult; testable without GUI
2. ToolpathModel (`model/toolpath_model.py`) — central data model; emits Qt signals on change; stores waypoints, segments, source text, line maps
3. PlaybackStateMachine (`model/playback.py`) — enum FSM with QTimer; drives step/play/pause; emits `index_changed`
4. GLViewport (`viewer/gl_viewport.py`) — QOpenGLWidget subclass; owns the OpenGL context; delegates to sub-renderers
5. SceneRenderer (`viewer/scene_renderer.py`) — VBO-based batch rendering; separate draw methods per visual type
6. PickingEngine (`viewer/picking.py`) — color-based offscreen picking; encodes waypoint index as RGB, reads pixel on click
7. Camera (`viewer/camera.py`) — arcball orbit, pan, zoom; maintains view matrix; updates on mouse events
8. AppController (`controller.py`) — wires model signals to views; translates view events to model mutations
9. CodePanel (`ui/code_panel.py`) — QPlainTextEdit with line highlighting; emits `line_clicked` signal
10. MainWindow (`ui/main_window.py`) — QMainWindow layout; splitter with code panel and 3D viewport

### Critical Pitfalls

1. **Multiline robtarget declarations** — parse the entire file as a single string; use semicolons as statement terminators; never parse line-by-line. Real `.mod` files split declarations arbitrarily. Silent data loss (points disappear with no error) is the failure mode.

2. **Immediate mode OpenGL** — use VBOs from the first line of rendering code; never use `glBegin`/`glEnd`. Works on 50-point test files, becomes unusably slow (sub-10 FPS) at 500+ points, requires complete rewrite to fix.

3. **QOpenGLWidget context not current outside paintGL** — call `self.makeCurrent()` before any GL operation outside `initializeGL`/`paintGL`/`resizeGL`, or use the deferred update pattern (set dirty flag, call `self.update()`, do GL work in paintGL). Crashes on second file load are the failure mode.

4. **ABB quaternion convention** — ABB uses `[q1, q2, q3, q4]` = `[w, x, y, z]` (scalar-first). scipy and many libraries expect `[x, y, z, w]` (scalar-last). Define internal convention once, add an explicit conversion function at every library boundary. Wrong orientations that look "almost right" are the failure mode.

5. **Step-to-line desync** — bind source line numbers to each MoveInstruction in the parser output, not as a parallel list. Never assume `point_index == line_number`. Highlighting that drifts progressively as files grow is the failure mode.

## Implications for Roadmap

Based on research, the architecture's build-order dependencies and the pitfall-to-phase mapping both point to a six-phase structure that mirrors the component dependency graph from ARCHITECTURE.md.

### Phase 1: Parser Foundation

**Rationale:** Every other component depends on parsed data. The parser must be correct before any UI or rendering work begins. The two most severe pitfalls (multiline declarations, step-to-line desync) must be addressed here. The parser is pure Python with no Qt/OpenGL deps and can be fully tested immediately.

**Delivers:** Working `parse_module()` function that accepts a `.mod` file path and returns a `ParseResult` with waypoints, path segments, bidirectional line maps, and source text. Parser handles multiline declarations, all three storage classes (CONST/VAR/PERS), all four move types (MoveL, MoveJ, MoveC, MoveAbsJ), Offs() expressions, and stores wobj references for future use.

**Features addressed:** RAPID parser (MoveL/MoveJ/MoveC/MoveAbsJ), robtarget/jointtarget extraction

**Pitfalls to avoid:** Multiline robtarget declarations (Pitfall 1), step-to-line desync (Pitfall 7), MoveC structure capture (Pitfall 5), wobj reference storage (Pitfall 6)

---

### Phase 2: 3D Viewer Foundation

**Rationale:** The 3D view is the primary output of the application. Camera controls are a prerequisite for any useful 3D rendering. VBO architecture must be established here — retrofitting it later requires a complete rewrite. OpenGL context management patterns must be established in the first QOpenGLWidget implementation.

**Delivers:** QOpenGLWidget with arcball camera (orbit/zoom/pan), VBO-based path rendering with move-type color distinction (MoveL=solid, MoveJ=dashed, MoveC=arc), waypoint markers, XYZ coordinate axes indicator, auto-fit camera to bounding box on file load.

**Features addressed:** 3D path rendering with move-type distinction, waypoint markers, camera controls, coordinate axes indicator

**Pitfalls to avoid:** Immediate mode rendering (Pitfall 3), QOpenGLWidget context management (Pitfall 4), MoveC arc rendering (Pitfall 5), quaternion convention (Pitfall 2)

**Stack elements:** QOpenGLWidget, PyOpenGL 3.1.10 with VBOs/VAOs/shaders, GLSL vertex+fragment shaders, pyrr for camera math, NumPy float32 arrays

---

### Phase 3: Model and Data Integration

**Rationale:** With parser (Phase 1) and renderer (Phase 2) independently working, the model layer ties them together. ToolpathModel becomes the single source of truth. This phase wires file loading through the full pipeline: file dialog -> parser -> model -> renderer + code panel update.

**Delivers:** ToolpathModel with Qt signals, AppController wiring model to viewer, file load end-to-end (open `.mod` file and see 3D path), CodePanel displaying raw RAPID source, basic syntax highlighting for RAPID keywords.

**Features addressed:** `.mod` file loading, RAPID code panel with syntax highlighting

**Architecture component:** ToolpathModel, AppController, CodePanel, MainWindow layout

---

### Phase 4: Playback and Code Sync

**Rationale:** Step-through playback and bidirectional code-to-3D linking are the core value proposition. Both depend on all previous phases. The PlaybackStateMachine drives index changes; the bidirectional line maps built in Phase 1 make code sync possible.

**Delivers:** Step forward/back through waypoints with 3D highlight of current point, code panel auto-scroll and line highlight synchronized with 3D selection, click-on-3D-point highlights code line, click-on-code-line highlights 3D point. Play/pause auto-playback with QTimer.

**Features addressed:** Step-through playback, bidirectional code-to-3D linking

**Pitfalls to avoid:** Step-to-line desync (Pitfall 7 — depends on Phase 1 storing line numbers correctly), QTextEdit/3D selection feedback loops (blockSignals guard needed)

**Architecture component:** PlaybackStateMachine, PickingEngine (color-based picking)

---

### Phase 5: Polish and UX Completeness

**Rationale:** After the core loop (open file -> see path -> verify) works end-to-end, UX gaps that affect daily usability are addressed. These are low-to-medium complexity improvements with high user impact.

**Delivers:** Parse error feedback with line number and partial results, coordinate readout (x, y, z displayed on point selection), drag-and-drop file loading, camera fit-to-view hotkey, window title showing loaded filename, graceful handling of files with only MoveAbsJ instructions.

**Features addressed:** UX pitfalls from PITFALLS.md (no error feedback, no coordinate readout, camera at origin)

---

### Phase 6: v1.x Enhancements

**Rationale:** After the tool is validated with real users, add the differentiating features that require the core to be stable first. TCP orientation frames require confirmed quaternion convention. Multi-procedure support requires parser to handle PROC boundaries. Speed/zone overlay requires speeddata extraction (parseable but deferred in v1).

**Delivers:** TCP orientation frames (RGB axis triads at each waypoint), multi-procedure PROC selection, speed/zone data text overlay, path statistics panel (length, point count, move type breakdown), search in code panel.

**Features addressed:** TCP orientation frames, multi-procedure support, speed/zone overlay, path statistics, code search

**Pitfalls to avoid:** Quaternion convention must be verified before orientation frame rendering (Pitfall 2)

---

### Phase Ordering Rationale

- Parser before renderer: the renderer needs correctly typed data structures to build VBOs; building renderer first would require replacing placeholder data later
- VBOs before any real data: retrofitting VBO architecture into immediate-mode code requires complete rewrite; this is the highest-cost mistake to make late
- Model layer after both parser and renderer have working data contracts: the model's signal interface can be designed knowing what both consumers need
- Playback after model: the PlaybackStateMachine owns a QTimer and calls `model.set_selection()`; it cannot be built without the model
- Code sync last among core features: requires parser line numbers (Phase 1), 3D highlighting (Phase 2), model signals (Phase 3), and step playback (Phase 4) all working
- UX polish after core loop: error handling is not meaningful until all the paths that can produce errors exist

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (3D Viewer):** Dashed line rendering in OpenGL Core Profile is non-trivial (no `glLineStipple` in core profile); fragment shader discard approach needs a concrete implementation; MoveC arc geometry (circumcenter of three points) needs a verified implementation
- **Phase 4 (Playback + Code Sync):** QTextEdit signal feedback loops when programmatically setting selection are a known Qt issue; the `blockSignals` pattern needs careful implementation to avoid double-highlight bugs
- **Phase 6 (TCP Orientation):** Quaternion-to-rotation-matrix pipeline must be verified against known ABB test cases before shipping; orientation frame scale relative to bounding box needs tuning

Phases with standard patterns (skip research-phase):
- **Phase 1 (Parser):** Regex-based statement tokenizer with semicolon delimiters is a well-understood pattern; ABB RAPID syntax is fully documented in the Technical Reference Manual
- **Phase 3 (Model + Integration):** Qt Model-View-Presenter with signals/slots is extensively documented; QSplitter layout, QFileDialog, QPlainTextEdit syntax highlighting are all standard Qt patterns
- **Phase 5 (UX Polish):** Standard Qt patterns throughout; no novel technical challenges

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | PyQt6, PyOpenGL, pyrr, NumPy are all verified on PyPI with confirmed version numbers; QOpenGLWidget Core Profile behavior on Windows confirmed via Qt forum sources; ABB RAPID robtarget format confirmed against official ABB Technical Reference Manual |
| Features | MEDIUM-HIGH | Table-stakes features derived from competitor analysis (RobotStudio, NC Viewer, RoboDK) and PROJECT.md requirements; v1.x and v2+ features are reasoned from user workflow patterns, not validated with real users |
| Architecture | HIGH | MVP via Qt signals is the standard PyQt architecture; build order derived from strict data dependency analysis; code examples verified against PyQt6 API; color-based picking is a well-established OpenGL pattern |
| Pitfalls | HIGH | Parser pitfalls verified against ABB documentation and community forum discussion; OpenGL performance characteristics confirmed against PyOpenGL documentation; Qt context management rules confirmed against Qt 6 official docs |

**Overall confidence:** HIGH

### Gaps to Address

- **MoveAbsJ handling:** jointtargets contain joint angles, not Cartesian positions; v1 behavior is undefined — options are skip gracefully, show as "no position" marker, or estimate using forward kinematics (not recommended for v1). Decide before Phase 1 parser design is finalized.

- **wobj coordinate frame resolution:** Phase 1 must capture wobj references in the data model even if full transform resolution is deferred to v2. The exact data structure for storing wobjdata (user frame + object frame transform chain) needs to be designed before parser implementation.

- **MoveC arc rendering edge case:** Three collinear points (degenerate circle) must fall back to a straight line without crashing. This edge case needs a specific test fixture.

- **File encoding:** Real `.mod` files from older RobotStudio versions may use Windows-1252 or other non-UTF-8 encodings. The file loader should detect and handle encoding gracefully (try UTF-8, fall back to cp1252).

- **User validation:** No real users have tested any assumptions about features beyond the stated PROJECT.md requirements. v1.x feature prioritization (TCP orientation vs. multi-procedure vs. speed overlay) should be validated with at least one robot engineer before Phase 6 planning.

## Sources

### Primary (HIGH confidence)
- [ABB RAPID Technical Reference Manual](https://library.e.abb.com/public/688894b98123f87bc1257cc50044e809/Technical%20reference%20manual_RAPID_3HAC16581-1_revJ_en.pdf) — robtarget data type, quaternion convention, MoveL/MoveJ/MoveC/MoveAbsJ specifications
- [ABB RAPID Instructions Reference](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf) — Move instruction syntax, argument structure
- [Qt 6 QOpenGLWidget Documentation](https://doc.qt.io/qt-6/qopenglwidget.html) — context management, FBO handling, cleanup patterns
- [PyQt6 on PyPI](https://pypi.org/project/PyQt6/) — version 6.10.2 confirmed
- [PyOpenGL on PyPI](https://pypi.org/project/PyOpenGL/) — version 3.1.10 confirmed
- [Qt Forum: Shader-based OpenGL in PyQt6](https://forum.qt.io/topic/137468/a-few-basic-changes-in-pyqt6-and-pyside6-regarding-shader-based-opengl-graphics) — Core Profile requirements confirmed

### Secondary (MEDIUM confidence)
- [NC Viewer](https://ncviewer.com/) — G-code viewer as closest analog; feature comparison basis
- [PyQt6 ModelView Architecture Tutorial](https://www.pythonguis.com/tutorials/pyqt6-modelview-architecture/) — MVP pattern implementation reference
- [ABB RobotStudio Desktop](https://www.abb.com/global/en/areas/robotics/products/software/robotstudio-suite/robotstudio-desktop) — competitor feature set reference
- [ABB Quaternion Convention Forum](https://forums.robotstudio.com/discussion/9435/quaternion-orientation) — ABB `[q1=w, q2=x, q3=y, q4=z]` convention confirmed
- [GERTY RobTarget documentation](https://batpartners.github.io/en/datatype/DataType-RobTarget/) — robtarget structure reference

### Tertiary (LOW confidence)
- [500 Lines: A 3D Modeller](https://aosabook.org/en/500L/a-3d-modeller.html) — scene graph and picking architecture patterns (general, not RAPID-specific)
- [PyOpenGL VBO dtype issue](https://github.com/mcfletch/pyopengl/issues/5) — float64 vs float32 performance trap

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
