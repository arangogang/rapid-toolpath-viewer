# Architecture Research

**Domain:** Desktop 3D toolpath viewer (ABB RAPID .mod parser + OpenGL renderer)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
+-----------------------------------------------------------------------+
|                         UI Layer (PyQt6)                               |
|  +----------------+  +-------------------+  +-----------------------+ |
|  | Menu / Toolbar |  | Code Panel        |  | Playback Controls     | |
|  | (File open)    |  | (QPlainTextEdit)  |  | (Step/Play/Pause)     | |
|  +-------+--------+  +--------+----------+  +----------+------------+ |
|          |                     |                        |              |
+----------+---------------------+------------------------+-------------+
|                       Controller Layer                                 |
|  +------------------------------------------------------------------+ |
|  |                    AppController                                  | |
|  |  - Coordinates file load, selection sync, playback commands       | |
|  +-------+------------------+---------------------+-----------------+ |
|          |                  |                     |                    |
+----------+------------------+---------------------+-------------------+
|                        Model Layer                                     |
|  +--------------+  +------------------+  +------------------------+   |
|  | RapidParser   |  | ToolpathModel    |  | PlaybackStateMachine   |   |
|  | (.mod -> AST) |  | (points, paths,  |  | (idle/playing/paused/  |   |
|  |               |  |  line mappings)  |  |  stepping)             |   |
|  +------+-------+  +--------+---------+  +-----------+------------+   |
|         |                   |                         |                |
+---------+-------------------+-------------------------+---------------+
|                       Rendering Layer                                  |
|  +------------------------------------------------------------------+ |
|  |              GLViewport (QOpenGLWidget subclass)                   | |
|  |  +-------------+  +----------------+  +------------------------+  | |
|  |  | Camera       |  | SceneRenderer  |  | PickingEngine          |  | |
|  |  | (orbit/pan/  |  | (paths, points |  | (color-based or ray    |  | |
|  |  |  zoom)       |  |  axes, grid)   |  |  cast selection)       |  | |
|  |  +-------------+  +----------------+  +------------------------+  | |
|  +------------------------------------------------------------------+ |
+-----------------------------------------------------------------------+
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| RapidParser | Parse .mod file into structured data: robtargets, move instructions, procedures | Regex-based line parser with state tracking for MODULE/PROC blocks |
| ToolpathModel | Central data model holding parsed points, path segments, line number mappings | Plain Python dataclasses; emits Qt signals on change |
| PlaybackStateMachine | Manage step-through state: current index, play/pause, speed, direction | Enum-based FSM with QTimer for auto-play ticking |
| AppController | Wire user actions to model mutations and view updates | Single coordinator class connecting signals/slots |
| GLViewport | QOpenGLWidget subclass owning the OpenGL context and render loop | Override initializeGL, paintGL, resizeGL; delegate to sub-renderers |
| Camera | Arcball orbit, pan, zoom from mouse input | Maintains view matrix; updates on mouse drag events |
| SceneRenderer | Draw path lines, point markers, coordinate axes, grid | VBO-based batch rendering; separate draw calls per visual type |
| PickingEngine | Map mouse clicks to waypoint indices | Color-based picking (render unique color per point, read pixel) |
| CodePanel | Display .mod source with line highlighting | QPlainTextEdit with QTextCursor-based highlighting |
| PlaybackControls | Step forward/back, play/pause buttons, speed slider | QToolBar with QPushButtons wired to PlaybackStateMachine |

## Recommended Project Structure

```
src/
  rapid_viewer/
    __init__.py
    main.py                    # Application entry point, QApplication setup
    controller.py              # AppController: wires model <-> views

    parser/
      __init__.py
      rapid_parser.py          # Top-level parse_module() function
      tokens.py                # Data types: RobTarget, MoveInstruction, Procedure, etc.
      patterns.py              # Compiled regex patterns for RAPID syntax

    model/
      __init__.py
      toolpath_model.py        # ToolpathModel: holds parsed data + selection state
      playback.py              # PlaybackStateMachine: step/play state management

    viewer/
      __init__.py
      gl_viewport.py           # GLViewport: QOpenGLWidget subclass
      camera.py                # Camera: arcball orbit, pan, zoom
      scene_renderer.py        # SceneRenderer: draws paths, points, axes
      picking.py               # PickingEngine: color-based object picking
      shaders/                 # GLSL vertex/fragment shaders (optional, can use fixed pipeline)
        basic.vert
        basic.frag
        picking.vert
        picking.frag

    ui/
      __init__.py
      main_window.py           # QMainWindow layout: splitter with code + 3D
      code_panel.py            # CodePanel: source display with line highlighting
      playback_controls.py     # PlaybackControls: toolbar buttons

    utils/
      __init__.py
      math_utils.py            # Quaternion to rotation matrix, vector ops
```

### Structure Rationale

- **parser/:** Isolated from Qt entirely. Pure Python, testable without GUI. The parser should work as a standalone library.
- **model/:** Qt-dependent only for QObject signals. No rendering or UI knowledge. This is the single source of truth.
- **viewer/:** All OpenGL code lives here. Nothing in viewer/ touches parser logic directly -- it reads from ToolpathModel.
- **ui/:** Standard Qt widgets. No OpenGL code. Communicates through the controller.
- **Separation principle:** parser/ and model/ can be tested in pure Python unit tests. viewer/ requires an OpenGL context but no file I/O. ui/ can be tested with QTest.

## Architectural Patterns

### Pattern 1: Model-View-Presenter (MVP) via Qt Signals

**What:** The ToolpathModel emits signals when data changes. Views (GLViewport, CodePanel) connect to these signals and update themselves. User actions in views emit signals that the AppController receives and translates into model operations.

**When to use:** Always -- this is the primary coordination pattern for the entire application.

**Trade-offs:** Slightly more boilerplate than direct calls, but decouples components cleanly. Views never talk to each other directly.

```python
# model/toolpath_model.py
from PyQt6.QtCore import QObject, pyqtSignal

class ToolpathModel(QObject):
    data_loaded = pyqtSignal()              # New .mod parsed
    selection_changed = pyqtSignal(int)      # Selected waypoint index (-1 = none)
    playback_index_changed = pyqtSignal(int) # Current playback position

    def __init__(self):
        super().__init__()
        self.waypoints: list[WayPoint] = []
        self.path_segments: list[PathSegment] = []
        self.source_lines: list[str] = []
        self._selected_index: int = -1

    def set_selection(self, index: int):
        if index != self._selected_index:
            self._selected_index = index
            self.selection_changed.emit(index)
```

```python
# controller.py
class AppController:
    def __init__(self, model, gl_viewport, code_panel, playback_controls):
        # Model -> Views
        model.selection_changed.connect(gl_viewport.highlight_point)
        model.selection_changed.connect(code_panel.highlight_line)
        model.data_loaded.connect(gl_viewport.rebuild_scene)
        model.data_loaded.connect(code_panel.load_source)

        # Views -> Controller -> Model
        gl_viewport.point_picked.connect(self._on_point_picked)
        code_panel.line_clicked.connect(self._on_line_clicked)
        playback_controls.step_forward.connect(self._on_step_forward)

    def _on_point_picked(self, waypoint_index: int):
        self.model.set_selection(waypoint_index)

    def _on_line_clicked(self, line_number: int):
        index = self.model.line_to_waypoint(line_number)
        if index is not None:
            self.model.set_selection(index)
```

### Pattern 2: Bidirectional Code-Line Linking via Index Maps

**What:** The parser builds two lookup dictionaries during parse time: `waypoint_index -> source_line_number` and `source_line_number -> waypoint_index`. These are stored in ToolpathModel and queried by both GLViewport (on pick) and CodePanel (on click).

**When to use:** Every time a .mod file is loaded. The mapping is immutable after parse -- no need for dynamic updates.

**Trade-offs:** Simple O(1) lookup in both directions. Only works for Move instruction lines, not arbitrary code. This is fine because only Move instructions produce waypoints.

```python
# parser/tokens.py
from dataclasses import dataclass
import numpy as np

@dataclass
class WayPoint:
    position: np.ndarray       # [x, y, z] in mm
    orientation: np.ndarray    # [q1, q2, q3, q4] quaternion
    config: tuple[int, ...]    # Robot configuration
    source_line: int           # 0-indexed line number in .mod file
    name: str                  # robtarget variable name (e.g. "p10")

@dataclass
class PathSegment:
    start_index: int           # Index into waypoints list
    end_index: int             # Index into waypoints list
    move_type: str             # "MoveL", "MoveJ", "MoveC", "MoveAbsJ"
    speed: str                 # Speed data name (e.g. "v100")
    zone: str                  # Zone data name (e.g. "z10", "fine")
    source_line: int           # Line of the Move instruction

@dataclass
class ParseResult:
    module_name: str
    waypoints: list[WayPoint]
    segments: list[PathSegment]
    source_text: str
    line_to_waypoint: dict[int, int]      # source_line -> waypoint_index
    waypoint_to_line: dict[int, int]      # waypoint_index -> source_line
```

### Pattern 3: Enum-Based Playback State Machine

**What:** A finite state machine with four states (IDLE, PLAYING, PAUSED, STEPPING) that governs step-through behavior. Uses QTimer for auto-play ticking. Transitions are explicit methods, not string-based.

**When to use:** All playback control logic flows through this FSM. The UI buttons map directly to transition methods.

**Trade-offs:** Simple and predictable. No external library needed (no `transitions` or `python-statemachine` dependency). A plain enum + if/elif is sufficient for four states.

```python
# model/playback.py
from enum import Enum, auto
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class PlaybackState(Enum):
    IDLE = auto()       # No file loaded
    STOPPED = auto()    # File loaded, at start or end
    PLAYING = auto()    # Auto-advancing
    PAUSED = auto()     # Auto-play paused at some index

class PlaybackStateMachine(QObject):
    index_changed = pyqtSignal(int)
    state_changed = pyqtSignal(PlaybackState)

    def __init__(self):
        super().__init__()
        self._state = PlaybackState.IDLE
        self._index = 0
        self._max_index = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._speed_ms = 500  # ms between steps

    def load(self, num_waypoints: int):
        self._max_index = num_waypoints - 1
        self._index = 0
        self._set_state(PlaybackState.STOPPED)

    def play(self):
        if self._state in (PlaybackState.STOPPED, PlaybackState.PAUSED):
            self._set_state(PlaybackState.PLAYING)
            self._timer.start(self._speed_ms)

    def pause(self):
        if self._state == PlaybackState.PLAYING:
            self._timer.stop()
            self._set_state(PlaybackState.PAUSED)

    def step_forward(self):
        if self._state != PlaybackState.IDLE:
            self._timer.stop()
            self._advance(1)
            self._set_state(PlaybackState.PAUSED)

    def step_backward(self):
        if self._state != PlaybackState.IDLE:
            self._timer.stop()
            self._advance(-1)
            self._set_state(PlaybackState.PAUSED)

    def _tick(self):
        if self._index >= self._max_index:
            self._timer.stop()
            self._set_state(PlaybackState.STOPPED)
        else:
            self._advance(1)

    def _advance(self, delta: int):
        new_index = max(0, min(self._max_index, self._index + delta))
        if new_index != self._index:
            self._index = new_index
            self.index_changed.emit(self._index)

    def _set_state(self, state: PlaybackState):
        if state != self._state:
            self._state = state
            self.state_changed.emit(state)
```

### Pattern 4: Color-Based Picking Over Ray Casting

**What:** To determine which waypoint was clicked, render the scene to an offscreen framebuffer with each waypoint drawn in a unique color (index encoded as RGB). Read the pixel at the click position and decode back to waypoint index.

**When to use:** For mouse click selection of waypoints in the 3D viewport.

**Trade-offs:** Simpler to implement than ray casting (no matrix math, no intersection tests). Pixel-perfect accuracy. Slight performance cost for the second render pass, but negligible for toolpath scenes with hundreds or low thousands of points. Ray casting would be preferable only if we needed hover/proximity detection without clicking.

```python
# viewer/picking.py  (conceptual)
def pick_at(self, x: int, y: int) -> int:
    """Returns waypoint index at screen position, or -1 if nothing."""
    self._fbo.bind()
    glClearColor(0, 0, 0, 0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    for i, wp in enumerate(self._waypoints):
        # Encode index as color: i+1 so that 0 = background
        r = ((i + 1) & 0xFF) / 255.0
        g = (((i + 1) >> 8) & 0xFF) / 255.0
        b = (((i + 1) >> 16) & 0xFF) / 255.0
        self._draw_point_marker(wp.position, (r, g, b))

    pixel = glReadPixels(x, self._height - y, 1, 1, GL_RGB, GL_UNSIGNED_BYTE)
    index = pixel[0] + (pixel[1] << 8) + (pixel[2] << 16) - 1
    self._fbo.release()
    return index  # -1 if background was clicked
```

## Data Flow

### File Load Flow

```
User clicks File > Open
    |
    v
QFileDialog returns .mod path
    |
    v
AppController.load_file(path)
    |
    v
RapidParser.parse_module(path) --> ParseResult
    |                                  |
    |                   (waypoints, segments, line maps, source text)
    v
ToolpathModel.set_data(parse_result)
    |
    +--[data_loaded signal]--> GLViewport.rebuild_scene()
    |                              |
    |                              v
    |                          SceneRenderer builds VBOs from waypoints/segments
    |                          Camera.fit_to_bounds(bounding_box)
    |
    +--[data_loaded signal]--> CodePanel.load_source(source_text)
    |
    +--[data_loaded signal]--> PlaybackStateMachine.load(num_waypoints)
```

### Selection Flow (Bidirectional)

```
Direction 1: 3D Click -> Code Highlight
==============================================
Mouse click on GLViewport
    |
    v
PickingEngine.pick_at(x, y) --> waypoint_index
    |
    v
GLViewport emits point_picked(waypoint_index) signal
    |
    v
AppController._on_point_picked(index)
    |
    v
ToolpathModel.set_selection(index)
    |
    +--[selection_changed signal]--> GLViewport.highlight_point(index)
    +--[selection_changed signal]--> CodePanel.highlight_line(waypoint_to_line[index])


Direction 2: Code Click -> 3D Highlight
==============================================
Mouse click on CodePanel line
    |
    v
CodePanel emits line_clicked(line_number) signal
    |
    v
AppController._on_line_clicked(line_number)
    |
    v
ToolpathModel.line_to_waypoint(line_number) --> waypoint_index (or None)
    |
    v
ToolpathModel.set_selection(waypoint_index)
    |
    +--[selection_changed signal]--> GLViewport.highlight_point(index)
    +--[selection_changed signal]--> CodePanel.highlight_line(line_number)
```

### Playback Flow

```
User clicks Play button
    |
    v
PlaybackControls emits play_clicked signal
    |
    v
AppController calls PlaybackStateMachine.play()
    |
    v
QTimer starts ticking at configured interval
    |
    v (on each tick)
PlaybackStateMachine._advance(+1)
    |
    v
PlaybackStateMachine emits index_changed(new_index)
    |
    v
AppController receives index_changed
    |
    v
ToolpathModel.set_selection(new_index)
    |
    +--[selection_changed]--> GLViewport highlights current point, draws "traveled" path
    +--[selection_changed]--> CodePanel scrolls to and highlights current line
```

### Key Data Flows

1. **Parse -> Model (one-time):** Parser produces immutable ParseResult. Model stores it and builds internal index maps. This happens once per file load.
2. **Selection sync (continuous):** Every selection change flows through ToolpathModel, which broadcasts to all views via signals. Views never communicate directly.
3. **Playback tick (periodic):** QTimer drives index advancement. The playback FSM owns the timer; the model owns the current index. Playback just calls set_selection repeatedly.

## Scaling Considerations

| Concern | Small files (<100 points) | Medium files (100-5000 points) | Large files (5000+ points) |
|---------|---------------------------|-------------------------------|---------------------------|
| Parse time | Negligible | Negligible (regex is fast) | Still fast (<1s), but validate |
| VBO rebuild | Instant | Instant | Batch into single VBO per type |
| Picking render | No concern | No concern | May need spatial culling |
| Code panel | No concern | No concern | Lazy line rendering |

### Scaling Priorities

1. **First bottleneck:** VBO construction on large files. Mitigation: batch all path line segments into one VBO (not one draw call per segment). Use `GL_LINES` or `GL_LINE_STRIP` with index buffers.
2. **Second bottleneck:** Picking pass on files with 10,000+ points. Mitigation: only render pick-able points (not lines) in the pick pass. Increase marker size slightly for easier clicking.

## Anti-Patterns

### Anti-Pattern 1: OpenGL Calls Outside GLViewport

**What people do:** Scatter glBindBuffer, glDrawArrays calls across controller or model code.
**Why it's wrong:** OpenGL calls require the correct GL context to be current. Calling GL outside the widget's paintGL chain causes silent failures or crashes. Makes code impossible to test without a live window.
**Do this instead:** All GL calls live inside GLViewport, SceneRenderer, PickingEngine, or Camera. The model provides plain Python data (numpy arrays). The renderer consumes it.

### Anti-Pattern 2: Direct View-to-View Communication

**What people do:** GLViewport directly calls CodePanel.highlight_line() when a point is picked.
**Why it's wrong:** Creates tight coupling. Adding a third view (e.g., properties panel) requires modifying the GL viewport. Breaks testability.
**Do this instead:** All cross-view communication goes through ToolpathModel signals. Views only know about the model, never about each other.

### Anti-Pattern 3: Parsing Inside the UI Thread Without Feedback

**What people do:** Call the parser synchronously in the main thread, freezing the UI.
**Why it's wrong:** For large .mod files, parsing could take noticeable time. The UI becomes unresponsive.
**Do this instead:** For v1 with typical file sizes (<5000 lines), synchronous parsing is acceptable. Add a QApplication.processEvents() call or move to QThread only if profiling shows >200ms parse times.

### Anti-Pattern 4: Storing GL State in the Model

**What people do:** Put VBO IDs, shader programs, or texture handles in the ToolpathModel.
**Why it's wrong:** Mixes data ownership with rendering state. Model cannot be tested without OpenGL. Breaks if GL context is recreated.
**Do this instead:** Model stores numpy arrays and plain Python data. Renderer creates and owns all GL resources, rebuilding them when model data changes.

### Anti-Pattern 5: Monolithic paintGL

**What people do:** Put all rendering code (grid, axes, paths, points, selection highlight) in a single 200-line paintGL method.
**Why it's wrong:** Impossible to maintain, test, or extend. Adding new visual elements means editing one massive function.
**Do this instead:** SceneRenderer with separate draw methods: draw_grid(), draw_axes(), draw_paths(), draw_waypoints(), draw_selection(). Each method is independent and testable.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Parser -> Model | Function call returning ParseResult dataclass | Parser is stateless. No signals. Called once per file load. |
| Model -> GLViewport | Qt signals (data_loaded, selection_changed) | GLViewport reads numpy arrays from model on signal receipt |
| Model -> CodePanel | Qt signals (data_loaded, selection_changed) | CodePanel reads source text and line numbers from model |
| Model -> PlaybackFSM | Direct method calls (load, play, step) | FSM is owned by model or sits alongside it |
| PlaybackFSM -> Model | Signal (index_changed) -> model.set_selection() | Timer-driven index advancement |
| GLViewport -> Controller | Signal (point_picked) | Controller translates to model.set_selection() |
| CodePanel -> Controller | Signal (line_clicked) | Controller looks up line->waypoint mapping |

### RAPID Parser Internal Design

The parser handles ABB RAPID .mod files with this structure:

```
MODULE ModuleName
    CONST robtarget p10 := [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax_a,...eax_f]];
    PERS robtarget p20 := [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax_a,...eax_f]];

    PROC main()
        MoveJ p10, v1000, z50, tool0;
        MoveL p20, v100, fine, tool0;
        MoveL Offs(p10, 0, 100, 0), v100, z10, tool0;
        MoveC p_circle, p_end, v100, z10, tool0;
    ENDPROC
ENDMODULE
```

Parser strategy (regex-based, two-pass):

1. **Pass 1 -- Data declarations:** Scan all lines for `CONST|PERS|VAR` + `robtarget` + name + `:=` + bracketed data. Build a name->WayPoint dictionary. Parse the nested bracket structure `[[x,y,z],[q1,q2,q3,q4],...]`.
2. **Pass 2 -- Move instructions:** Scan all lines within PROC blocks for `MoveL|MoveJ|MoveC|MoveAbsJ`. Extract the target reference (variable name or inline `Offs()` expression), speed, zone, tool. Resolve target name to a WayPoint from the dictionary. For `Offs()`, compute the offset position.
3. **Output:** Return ParseResult with ordered waypoints list (in execution order), path segments, and bidirectional line mappings.

Key parsing challenges:
- **Inline Offs():** `MoveL Offs(p10, 0, 100, 0)` means "p10 but shifted by (0, 100, 0)". Must evaluate at parse time.
- **MoveC (circular):** Takes two robtargets (circle point + end point). Need to handle the extra argument.
- **MoveAbsJ:** Uses jointtarget, not robtarget. For v1, can skip or represent as a special "unknown position" waypoint.
- **Multi-PROC modules:** A module may contain multiple procedures. v1 can parse all PROCs sequentially or let the user select which PROC to visualize.

## Build Order (Dependencies)

Build order is dictated by data dependencies. Components lower in the list depend on components above.

```
Phase 1: Foundation (no dependencies)
  1. parser/tokens.py         -- Data classes, no external deps
  2. parser/patterns.py       -- Regex patterns, no external deps
  3. utils/math_utils.py      -- Quaternion math, numpy only

Phase 2: Parser (depends on Phase 1)
  4. parser/rapid_parser.py   -- Uses tokens + patterns, testable standalone

Phase 3: Model (depends on Phase 2 output types)
  5. model/toolpath_model.py  -- Uses tokens, emits Qt signals
  6. model/playback.py        -- Uses QTimer, emits Qt signals

Phase 4: Rendering (depends on Phase 3 for data)
  7. viewer/camera.py         -- Math only, no model dependency
  8. viewer/scene_renderer.py -- Reads from ToolpathModel
  9. viewer/gl_viewport.py    -- Composes Camera + SceneRenderer
  10. viewer/picking.py        -- Extends GLViewport render pass

Phase 5: UI Shell (depends on Phase 4 for GLViewport widget)
  11. ui/code_panel.py         -- QPlainTextEdit with highlight logic
  12. ui/playback_controls.py  -- QToolBar with buttons
  13. ui/main_window.py        -- Composes all UI widgets

Phase 6: Integration (depends on everything)
  14. controller.py            -- Wires model <-> views
  15. main.py                  -- Application entry point
```

**Rationale:** The parser can be built and fully tested with zero UI. The model can be tested with mock data. The renderer needs the model's data types but not the parser. The UI shell needs the GL widget. The controller is last because it wires everything together. This ordering minimizes blocked work and enables testing at every phase.

## Sources

- [500 Lines - A 3D Modeller (Architecture of OpenGL Scene Graph + Picking)](https://aosabook.org/en/500L/a-3d-modeller.html)
- [Qt QOpenGLWidget Documentation](https://doc.qt.io/qtforpython-6/PySide6/QtOpenGLWidgets/QOpenGLWidget.html)
- [PyQt6 ModelView Architecture Tutorial](https://www.pythonguis.com/tutorials/pyqt6-modelview-architecture/)
- [Clean Architecture for PyQt GUI using MVP Pattern](https://medium.com/@mark_huber/a-clean-architecture-for-a-pyqt-gui-using-the-mvp-pattern-78ecbc8321c0)
- [OpenGL Ray Casting for Mouse Picking](https://antongerdelan.net/opengl/raycasting.html)
- [ABB RAPID Technical Reference Manual](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf)
- [ABB RAPID Introduction to RAPID](http://rovart.cimr.pub.ro/docs/OpIntroRAPID.pdf)
- [Python transitions (state machine library)](https://github.com/pytransitions/transitions)

---
*Architecture research for: ABB RAPID Toolpath Viewer (Python + PyQt6 + PyOpenGL)*
*Researched: 2026-03-30*
