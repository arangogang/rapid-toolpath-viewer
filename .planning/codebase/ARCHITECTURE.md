# Architecture

**Analysis Date:** 2026-03-31

## Pattern Overview

**Overall:** Three-layer pipeline architecture (Parser -> Geometry Builder -> Renderer) with Qt signal-based UI coordination.

**Key Characteristics:**
- Strict unidirectional data flow: `.mod` file text -> `ParseResult` -> `GeometryBuffers` -> GPU VBOs
- Qt signals for bidirectional UI linking (3D viewport <-> code panel <-> playback state)
- No global state; `PlaybackState` is the single observable source of truth for current waypoint
- Parser layer has zero Qt dependency (pure Python + NumPy), enabling headless testing
- OpenGL 3.3 Core Profile with modern shader pipeline (VBO/VAO, no fixed-function)

## Layers

**Parser Layer:**
- Purpose: Read `.mod` files and extract structured robot program data
- Location: `src/rapid_viewer/parser/`
- Contains: Regex patterns, tokenizer, two-pass parser, frozen dataclass tokens
- Depends on: `numpy` (for coordinate arrays), `re` (stdlib)
- Used by: `MainWindow.load_file()` which calls `parse_module()`

**Renderer Layer:**
- Purpose: Convert parsed data into GPU geometry and render via OpenGL
- Location: `src/rapid_viewer/renderer/`
- Contains: Geometry builder, GLSL shaders, arcball camera, QOpenGLWidget
- Depends on: Parser tokens (`ParseResult`, `MoveInstruction`), PyOpenGL, pyrr, PyQt6
- Used by: `MainWindow` embeds `ToolpathGLWidget`

**UI Layer:**
- Purpose: Application window, code viewer, playback controls, signal wiring
- Location: `src/rapid_viewer/ui/`
- Contains: MainWindow, CodePanel, PlaybackToolbar, PlaybackState, RapidHighlighter
- Depends on: Parser (for `ParseResult`), Renderer (for `ToolpathGLWidget`), PyQt6
- Used by: `main.py` entry point

## Data Flow

**File Load Pipeline:**

1. User opens `.mod` file via `File > Open` or CLI argument
2. `MainWindow.load_file()` calls `read_mod_file(path)` -> raw string (UTF-8 with latin-1 fallback)
3. `parse_module(source)` performs two-pass parsing:
   - Pass 1: Tokenize statements by semicolons, extract all `RobTarget` and `JointTarget` declarations into lookup dicts
   - Pass 2: Extract `MoveInstruction` objects, resolving target references (named, `Offs()`, inline) against Pass 1 dicts
   - Returns `ParseResult` dataclass with moves, targets, source text, procedure ranges
4. `MainWindow` distributes `ParseResult` to three consumers:
   - `CodePanel.set_source(text)` -> displays RAPID source with syntax highlighting
   - `PlaybackState.set_moves(moves)` -> loads move list, resets index to 0
   - `ToolpathGLWidget.update_scene(parse_result)` -> calls `build_geometry()` -> uploads VBOs

**Geometry Build Pipeline (inside `build_geometry`):**

1. Iterates `ParseResult.moves` in order, tracking `prev_pos`
2. For each Cartesian move: creates line segment vertices (solid for MoveL/MoveC, dashed for MoveJ)
3. MoveC arcs are tessellated via `tessellate_arc()` (3-point circle -> polyline)
4. Marker vertex at every Cartesian waypoint position
5. TCP orientation triads built from quaternion orientations
6. Returns `GeometryBuffers` with four float32 arrays, each shaped `(N, 6)` = `[x, y, z, r, g, b]`

**Rendering Pipeline (each frame):**

1. `paintGL()` calls `camera.mvp()` -> combined view-projection matrix (model = identity)
2. Five draw passes: solid lines, dashed lines, markers, highlight marker, TCP triads
3. Axes indicator drawn last in a small viewport (80x80 px, bottom-left) with rotation-only MVP

**State Management:**

- `PlaybackState` (`src/rapid_viewer/ui/playback_state.py`) is the single source of truth for current waypoint index
- Emits `current_changed(int)` signal consumed by:
  - `MainWindow._on_waypoint_changed()` -> updates GL highlight + code panel highlight
  - `PlaybackToolbar._on_index_changed()` -> updates scrubber slider + position label
- Emits `moves_changed()` consumed by `PlaybackToolbar._on_moves_changed()` -> updates scrubber range

**Bidirectional Linking (3D <-> Code):**

1. **3D click -> Code:** `ToolpathGLWidget.waypoint_clicked(int)` -> `PlaybackState.set_index()` -> `current_changed` -> `CodePanel.highlight_line(move.source_line)`
2. **Code click -> 3D:** `CodePanel.line_clicked(int)` -> `MainWindow._on_code_line_clicked()` scans moves for matching `source_line` -> `PlaybackState.set_index()` -> `current_changed` -> `ToolpathGLWidget.set_highlight_index()`

## Key Abstractions

**ParseResult:**
- Purpose: Complete output of parsing a `.mod` file -- the contract between parser and all consumers
- Definition: `src/rapid_viewer/parser/tokens.py` lines 106-121
- Pattern: Mutable dataclass (built incrementally by parser), then treated as read-only by consumers
- Contains: `module_name`, `moves: list[MoveInstruction]`, `targets: dict[str, RobTarget]`, `joint_targets`, `source_text`, `procedures`, `proc_ranges`, `errors`

**GeometryBuffers:**
- Purpose: GPU-ready vertex arrays, the contract between geometry builder and GL widget
- Definition: `src/rapid_viewer/renderer/geometry_builder.py` lines 24-38
- Pattern: Dataclass holding four NumPy arrays: `solid_verts`, `dashed_verts`, `marker_verts`, `triad_verts`
- Each array: shape `(N, 6)`, dtype `float32`, interleaved `[x, y, z, r, g, b]`

**ArcballCamera:**
- Purpose: Interactive 3D camera with orbit/pan/zoom, produces view and projection matrices
- Definition: `src/rapid_viewer/renderer/camera.py`
- Pattern: Stateful object with quaternion-based rotation, consumed by `ToolpathGLWidget.paintGL()`
- Outputs: `mvp()` returns `float32` 4x4 matrix for shader upload

**PlaybackState:**
- Purpose: Observable model for current waypoint index, centralizes navigation logic
- Definition: `src/rapid_viewer/ui/playback_state.py`
- Pattern: QObject with Qt signals (`current_changed`, `moves_changed`), similar to a ViewModel

## Entry Points

**Application Entry:**
- Location: `src/rapid_viewer/main.py`
- Triggers: `python -m rapid_viewer.main [file.mod]`
- Responsibilities: Set OpenGL 3.3 Core Profile surface format, create `QApplication`, create `MainWindow`, optional CLI file load, start event loop

**File Load Entry:**
- Location: `src/rapid_viewer/ui/main_window.py` -> `MainWindow.load_file(file_path)`
- Triggers: Menu action `Ctrl+O`, CLI argument, or programmatic call
- Responsibilities: Parse file, distribute result to GL widget, code panel, playback state, update title bar

**Parser Entry:**
- Location: `src/rapid_viewer/parser/rapid_parser.py` -> `parse_module(source)`
- Triggers: Called by `MainWindow.load_file()`
- Responsibilities: Tokenize, extract targets (Pass 1), extract moves (Pass 2), return `ParseResult`

## Error Handling

**Strategy:** Defensive with graceful degradation at parse level; top-level exception catch in `load_file()`

**Patterns:**
- Parser functions (`try_parse_robtarget_decl`, `try_parse_move`) return `None` on failure rather than raising -- malformed statements are silently skipped
- `ParseResult.errors` field exists for non-fatal warnings but is not currently populated
- `MainWindow.load_file()` wraps everything in `except Exception` and shows `QMessageBox.critical()`
- `read_mod_file()` falls back from UTF-8 to latin-1 encoding on `UnicodeDecodeError`
- `ToolpathGLWidget.update_scene()` guards against missing OpenGL context (defers upload to `initializeGL`)
- `tessellate_arc()` falls back to straight line for degenerate (collinear) 3-point arcs

## Cross-Cutting Concerns

**Logging:** Not implemented. No logging framework configured. Errors are either silently skipped (parser) or shown via `QMessageBox` (UI).

**Validation:** Regex-based pattern matching in parser layer. No schema validation. Malformed data is skipped silently.

**Authentication:** Not applicable (desktop application, no network).

**Coordinate System:** RAPID coordinates in millimeters. ABB quaternion convention `[q1,q2,q3,q4] = [w,x,y,z]` converted to pyrr convention `[x,y,z,w]` in `build_triad_vertices()`.

**PROC Filtering:** `MainWindow._apply_proc_filter()` creates filtered `ParseResult` copies via `dataclasses.replace()` and re-uploads geometry to GPU. This is a full re-upload, not incremental.

---

*Architecture analysis: 2026-03-31*
