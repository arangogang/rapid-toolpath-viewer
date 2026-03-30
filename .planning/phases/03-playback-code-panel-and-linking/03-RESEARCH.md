# Phase 3: Playback, Code Panel, and Linking - Research

**Researched:** 2026-03-30
**Domain:** PyQt6 UI composition, QSyntaxHighlighter, OpenGL picking, playback state management
**Confidence:** HIGH

## Summary

Phase 3 completes the core verification workflow by adding three interconnected features: (1) a playback controller to step through waypoints, (2) a syntax-highlighted RAPID code panel, and (3) bidirectional linking between 3D waypoints and code lines. The existing codebase provides strong foundations: `ParseResult` already stores `source_text`, `procedures` list, and every `MoveInstruction` carries a `source_line` number. The `ToolpathGLWidget` already renders markers at waypoint positions. The key engineering challenges are: wiring a central "current waypoint index" through all three subsystems, implementing waypoint picking in OpenGL 3.3 Core Profile, and restructuring `MainWindow` from single central widget to a `QSplitter`-based layout.

All required PyQt6 widgets (`QPlainTextEdit`, `QSyntaxHighlighter`, `QSplitter`, `QTimer`, `QSlider`, `QToolBar`) are standard Qt6 classes with stable APIs. No new external dependencies are needed. The RAPID keyword set for syntax highlighting is small and well-defined. The TCP orientation triad (REND-04) requires building small line-segment geometry per waypoint using quaternion-to-rotation-matrix conversion already proven in Phase 2 (pyrr).

**Primary recommendation:** Introduce a `PlaybackState` model class that owns the current waypoint index and emits Qt signals on change. All three subsystems (GL widget, code panel, playback toolbar) observe this single source of truth. For waypoint picking, use ray-casting (nearest-point search) rather than FBO color picking -- it is simpler, avoids FBO setup complexity, and is more than sufficient for point-cloud-like data with typically under 10,000 waypoints.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLAY-01 | Step forward to next waypoint | PlaybackState index increment + signal emission |
| PLAY-02 | Step backward to previous waypoint | PlaybackState index decrement + signal emission |
| PLAY-03 | Auto-play through waypoints sequentially | QTimer with configurable interval drives PlaybackState.step_forward() |
| PLAY-04 | Current waypoint visually highlighted in 3D | Separate GL_POINTS draw call with highlight color + larger point size, or uniform-driven highlight index in marker shader |
| PLAY-05 | Position indicator "N / M" display | QLabel in toolbar, updated on PlaybackState.changed signal |
| PLAY-06 | Speed slider 0.5x to 10x | QSlider(Qt.Orientation.Horizontal) mapped to QTimer interval |
| PLAY-07 | Scrubber slider for instant position jump | QSlider with range [0, len(moves)-1], valueChanged -> PlaybackState.set_index() |
| CODE-01 | RAPID code displayed in side panel | QPlainTextEdit (read-only) populated from ParseResult.source_text |
| CODE-02 | Syntax highlighting for RAPID keywords | QSyntaxHighlighter subclass with regex rules for MoveL/MoveJ/PROC/etc. |
| CODE-03 | Current waypoint's code line highlighted | QTextEdit.ExtraSelection with background color on the line matching current move's source_line |
| LINK-01 | 3D click -> code scroll | Mouse click ray-cast -> nearest waypoint -> PlaybackState.set_index() -> code panel scrolls to source_line |
| LINK-02 | Code click -> 3D select | QPlainTextEdit.cursorPositionChanged -> find MoveInstruction at that line -> PlaybackState.set_index() |
| PARS-08 | PROC selector for multi-proc files | QComboBox populated from ParseResult.procedures; selection filters moves list |
| REND-04 | TCP orientation triad per waypoint | Small RGB axis lines at each waypoint position, rotated by quaternion from RobTarget.orient |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech Stack**: Python + PyQt6 + PyOpenGL -- no alternatives
- **OpenGL**: 3.3 Core Profile, modern shader pipeline, VBO/VAO -- no fixed-function
- **Platform**: Windows desktop only
- **Scope**: Read-only viewer -- no editing, no simulation
- **pyrr**: Use `pyrr.matrix44.create_from_quaternion` (module function), NOT `pyrr.Matrix44` class method
- **PyQt6 enum style**: Use fully qualified enums (e.g., `Qt.AlignmentFlag.AlignLeft`)
- **Lazy imports**: GL widget imported lazily inside MainWindow.__init__
- **Testing**: pytest + pytest-qt; GL tests use `_has_gl_context()` guard
- **Tooling**: uv for deps, ruff for linting

## Standard Stack

### Core (already installed -- no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | 6.10.2 | QPlainTextEdit, QSyntaxHighlighter, QSplitter, QTimer, QSlider, QToolBar | Already project dependency; all needed widgets are in QtWidgets/QtGui |
| PyOpenGL | 3.1.10 | FBO for picking (if needed), additional draw calls for highlights | Already installed |
| pyrr | 0.10.3 | Quaternion-to-rotation-matrix for TCP triads | Already installed |
| NumPy | 2.3.5 | Ray-cast math, vertex buffer construction | Already installed |

### Supporting (no additions needed)
No new libraries required. All Phase 3 features use standard PyQt6 widgets and existing OpenGL infrastructure.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Ray-cast picking | FBO color picking | FBO picking is pixel-perfect but requires creating an offscreen FBO, a separate picking shader, and a render pass on each click. Ray-casting is simpler for point data (just unproject mouse ray, find nearest point in marker array). For <10K points, ray-cast is instant. Use ray-cast. |
| QPlainTextEdit | QScintilla | QScintilla provides built-in line numbers, folding, markers. But it is an additional dependency (PyQt6-QScintilla), and RAPID highlighting is simple enough that QSyntaxHighlighter suffices. The code panel is read-only -- no editing features needed. |
| Manual line highlight | QTextEdit.ExtraSelection | ExtraSelection is the Qt-standard way to highlight lines without modifying document content. Use it. |

## Architecture Patterns

### Recommended Project Structure
```
src/rapid_viewer/
  ui/
    main_window.py          # QSplitter layout, toolbar, wiring
    code_panel.py            # QPlainTextEdit + QSyntaxHighlighter (NEW)
    rapid_highlighter.py     # QSyntaxHighlighter subclass (NEW)
    playback_toolbar.py      # Step/Play/Pause/Speed/Scrubber widgets (NEW)
    playback_state.py        # Central state model with Qt signals (NEW)
  renderer/
    toolpath_gl_widget.py    # Add: highlight current waypoint, TCP triads, mouse picking
    camera.py                # Unchanged
    geometry_builder.py      # Add: TCP triad geometry builder
    shaders.py               # Add: triad shader (reuse SOLID or new)
  parser/
    rapid_parser.py          # Add: filter moves by PROC (PARS-08)
    tokens.py                # Unchanged
    patterns.py              # Unchanged (RE_PROC, RE_ENDPROC already exist)
```

### Pattern 1: Central PlaybackState with Qt Signals
**What:** A QObject subclass that owns the current waypoint index, the filtered move list, and emits `current_changed(int)` when the index changes. All UI components connect to this single signal.
**When to use:** Always -- this is the core coordination mechanism.
**Example:**
```python
# Source: Standard Qt signal/slot pattern
from PyQt6.QtCore import QObject, pyqtSignal

class PlaybackState(QObject):
    current_changed = pyqtSignal(int)  # emits new index
    moves_changed = pyqtSignal()       # emits when move list changes (proc switch)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._moves: list[MoveInstruction] = []
        self._current_index: int = -1  # -1 = no selection

    @property
    def current_index(self) -> int:
        return self._current_index

    def set_index(self, index: int) -> None:
        if 0 <= index < len(self._moves):
            self._current_index = index
            self.current_changed.emit(index)

    def step_forward(self) -> None:
        if self._current_index < len(self._moves) - 1:
            self.set_index(self._current_index + 1)

    def step_backward(self) -> None:
        if self._current_index > 0:
            self.set_index(self._current_index - 1)

    def set_moves(self, moves: list[MoveInstruction]) -> None:
        self._moves = moves
        self._current_index = 0 if moves else -1
        self.moves_changed.emit()
        if self._current_index >= 0:
            self.current_changed.emit(self._current_index)

    @property
    def total(self) -> int:
        return len(self._moves)

    @property
    def current_move(self) -> MoveInstruction | None:
        if 0 <= self._current_index < len(self._moves):
            return self._moves[self._current_index]
        return None
```

### Pattern 2: QSyntaxHighlighter for RAPID Keywords
**What:** Subclass QSyntaxHighlighter, define regex rules for RAPID keywords, apply formatting in highlightBlock().
**When to use:** When populating the code panel.
**Example:**
```python
# Source: Qt6 official QSyntaxHighlighter documentation
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont
from PyQt6.QtCore import QRegularExpression

class RapidHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        # Move keywords
        move_fmt = QTextCharFormat()
        move_fmt.setForeground(QColor("#4EC9B0"))  # teal
        move_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in ["MoveL", "MoveJ", "MoveC", "MoveAbsJ"]:
            pattern = QRegularExpression(rf"\b{kw}\b", QRegularExpression.PatternOption.CaseInsensitiveOption)
            self._rules.append((pattern, move_fmt))

        # PROC / ENDPROC
        proc_fmt = QTextCharFormat()
        proc_fmt.setForeground(QColor("#C586C0"))  # purple
        proc_fmt.setFontWeight(QFont.Weight.Bold)
        for kw in ["PROC", "ENDPROC", "MODULE", "ENDMODULE"]:
            pattern = QRegularExpression(rf"\b{kw}\b", QRegularExpression.PatternOption.CaseInsensitiveOption)
            self._rules.append((pattern, proc_fmt))

        # Data types
        type_fmt = QTextCharFormat()
        type_fmt.setForeground(QColor("#569CD6"))  # blue
        for kw in ["CONST", "PERS", "VAR", "LOCAL", "robtarget", "jointtarget", "speeddata", "zonedata"]:
            pattern = QRegularExpression(rf"\b{kw}\b", QRegularExpression.PatternOption.CaseInsensitiveOption)
            self._rules.append((pattern, type_fmt))

        # Comments (! to end of line)
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6A9955"))  # green
        self._rules.append((QRegularExpression(r"!.*$"), comment_fmt))

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)
```

### Pattern 3: Line Highlighting with ExtraSelection
**What:** Use QPlainTextEdit.setExtraSelections() to highlight the current source line with a background color, without modifying the document.
**When to use:** CODE-03 -- when the current waypoint changes, highlight its source line.
**Example:**
```python
# Source: Qt6 QPlainTextEdit documentation
from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtCore import Qt

def highlight_line(editor: QPlainTextEdit, line_number: int) -> None:
    """Highlight a 1-indexed line number in the editor."""
    block = editor.document().findBlockByLineNumber(line_number - 1)  # 0-indexed
    if not block.isValid():
        return
    cursor = QTextCursor(block)
    selection = QPlainTextEdit.ExtraSelection()
    selection.format.setBackground(QColor("#264F78"))  # VS Code-style blue highlight
    selection.format.setProperty(
        QTextCharFormat.Property.FullWidthSelection, True
    )
    selection.cursor = cursor
    editor.setExtraSelections([selection])
    # Scroll to the line
    editor.setTextCursor(cursor)
    editor.centerCursor()
```

### Pattern 4: Ray-Cast Picking for Waypoints
**What:** Unproject the mouse click position into a 3D ray, then find the nearest waypoint to the ray.
**When to use:** LINK-01 -- clicking in the 3D view to select a waypoint.
**Example:**
```python
# Source: Standard OpenGL unprojection math
import numpy as np

def pick_nearest_waypoint(
    mouse_x: float, mouse_y: float,
    width: int, height: int,
    view_matrix: np.ndarray,
    proj_matrix: np.ndarray,
    waypoint_positions: np.ndarray,  # shape (N, 3)
    max_distance: float = 20.0,  # pixel threshold
) -> int | None:
    """Return index of nearest waypoint to mouse click, or None."""
    # Project all waypoints to screen space
    mvp = proj_matrix @ view_matrix
    ones = np.ones((len(waypoint_positions), 1), dtype=np.float32)
    pts_4d = np.hstack([waypoint_positions, ones])  # (N, 4)
    clip = (mvp @ pts_4d.T).T  # (N, 4)

    # Perspective divide
    w = clip[:, 3:4]
    ndc = clip[:, :3] / np.where(np.abs(w) < 1e-6, 1.0, w)

    # NDC to screen
    screen_x = (ndc[:, 0] + 1.0) * 0.5 * width
    screen_y = (1.0 - ndc[:, 1]) * 0.5 * height  # Y flipped

    # Distance from mouse to each projected waypoint
    dx = screen_x - mouse_x
    dy = screen_y - mouse_y
    distances = np.sqrt(dx * dx + dy * dy)

    # Filter behind camera (w < 0)
    distances[clip[:, 3] <= 0] = float('inf')

    min_idx = int(np.argmin(distances))
    if distances[min_idx] <= max_distance:
        return min_idx
    return None
```

### Pattern 5: PROC Filtering (PARS-08)
**What:** Filter `ParseResult.moves` to only moves within a specific PROC boundary.
**When to use:** When user selects a PROC from the QComboBox.
**Implementation approach:** The parser already extracts `procedures` list. To filter moves by PROC, we need line ranges. The parser can be extended to track PROC start/end line numbers. Between `PROC name()` and `ENDPROC`, collect moves whose `source_line` falls in that range.

### Pattern 6: TCP Orientation Triads (REND-04)
**What:** At each waypoint, draw 3 short colored lines (R=X, G=Y, B=Z) rotated by the waypoint's quaternion orientation.
**When to use:** Always rendered, toggled if desired.
**Implementation:** For each waypoint with a valid `orient` quaternion:
1. Convert ABB quaternion [q1,q2,q3,q4] (q1=w,q2=x,q3=y,q4=z) to rotation matrix via `pyrr.matrix44.create_from_quaternion`
2. Transform 3 unit axis vectors by the rotation matrix
3. Scale to a visible length (e.g., 10-20mm)
4. Emit as GL_LINES vertices with RGB colors

This generates 6 vertices per waypoint (3 axis lines x 2 endpoints). For 1000 waypoints = 6000 vertices = trivial.

### Anti-Patterns to Avoid
- **Storing playback state in multiple places:** The GL widget, code panel, and toolbar must NOT each maintain their own "current index". Use a single PlaybackState object.
- **Modifying QPlainTextEdit document for highlighting:** Use ExtraSelection, not insertHtml() or setHtml(). Modifying the document breaks undo stack and line numbering.
- **Using QTextEdit instead of QPlainTextEdit:** QTextEdit is for rich text. QPlainTextEdit is optimized for large plain text and is the correct choice for a code viewer.
- **Rendering the picking FBO every frame:** If using FBO picking (not recommended), only render the pick buffer on mouse click, not every frame.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Syntax highlighting engine | Custom text scanning | QSyntaxHighlighter subclass | Handles incremental re-highlighting, block state, Qt document integration automatically |
| Line highlighting | Manual text formatting | QPlainTextEdit.setExtraSelections() | Non-destructive, supports multiple selections, standard Qt pattern |
| Timer-based animation | Manual threading / time.sleep() | QTimer.timeout signal | Thread-safe, integrates with Qt event loop, easy to stop/start/change interval |
| Slider value mapping | Manual mouse tracking | QSlider with valueChanged signal | Handles keyboard interaction, accessibility, styling for free |
| Split pane layout | Manual resize handling | QSplitter | Provides drag handle, saves/restores sizes, handles minimum sizes |

**Key insight:** PyQt6 provides purpose-built widgets for every UI component in this phase. The engineering work is in wiring them together through the PlaybackState signal hub, not in building custom widgets.

## Common Pitfalls

### Pitfall 1: QSyntaxHighlighter and QPlainTextEdit Ownership
**What goes wrong:** Creating QSyntaxHighlighter with the wrong parent causes it to not highlight, or to be garbage collected.
**Why it happens:** QSyntaxHighlighter must be passed the QTextDocument (via `editor.document()`), not the widget itself.
**How to avoid:** `self._highlighter = RapidHighlighter(self._editor.document())`
**Warning signs:** Highlighting works initially but disappears after GC cycle; or never appears at all.

### Pitfall 2: QTimer Interval vs Speed Multiplier
**What goes wrong:** Speed slider mapped linearly produces unnatural feel at extremes.
**Why it happens:** Linear mapping of 0.5x-10x to interval in ms makes 10x nearly instant and 0.5x barely different from 1x.
**How to avoid:** Use base interval (e.g., 500ms at 1x) divided by speed factor. At 0.5x = 1000ms, at 10x = 50ms. This is correct and intuitive.
**Warning signs:** Speed slider feels non-responsive at certain ranges.

### Pitfall 3: ExtraSelection vs Document Modification
**What goes wrong:** Using `setExtraSelections()` but forgetting to set `FullWidthSelection` property -- only the text portion is highlighted, not the full line.
**Why it happens:** Default ExtraSelection only highlights the cursor's selection range.
**How to avoid:** Set `QTextCharFormat.Property.FullWidthSelection` to `True` on the selection format.
**Warning signs:** Highlight appears as a narrow strip instead of full-width background.

### Pitfall 4: Coordinate System Mismatch in Ray-Cast Picking
**What goes wrong:** Mouse Y coordinate is inverted relative to OpenGL viewport Y.
**Why it happens:** Qt widget coordinates have Y=0 at top; OpenGL has Y=0 at bottom.
**How to avoid:** When converting mouse position to NDC, flip Y: `ndc_y = 1.0 - (2.0 * mouse_y / height)`. Or flip when converting projected points to screen space.
**Warning signs:** Clicking above a point selects the point below it.

### Pitfall 5: ABB Quaternion Convention
**What goes wrong:** TCP triads render with wrong orientation.
**Why it happens:** ABB RAPID uses [q1,q2,q3,q4] where q1=w (scalar), q2=x, q3=y, q4=z. pyrr expects [x,y,z,w] order.
**How to avoid:** Reorder before passing to pyrr: `pyrr_quat = [orient[1], orient[2], orient[3], orient[0]]` (x,y,z,w from ABB's q2,q3,q4,q1).
**Warning signs:** Triads point in seemingly random directions. Verify with a known orientation (identity quaternion [1,0,0,0] should produce axes aligned with world XYZ).

### Pitfall 6: PROC Boundary Detection for Multi-PROC Files
**What goes wrong:** Moves from one PROC "leak" into another when filtering.
**Why it happens:** The current parser collects ALL moves from the entire file into a flat list. It does not track which PROC each move belongs to.
**How to avoid:** Extend the parser to track PROC boundaries by line number. During Pass 2, record which PROC each move belongs to (e.g., add a `proc_name` field to MoveInstruction, or build a `proc_ranges: dict[str, tuple[int,int]]` mapping).
**Warning signs:** Selecting PROC "main" still shows moves from PROC "path2".

### Pitfall 7: MainWindow Layout Migration
**What goes wrong:** Replacing `setCentralWidget(gl_widget)` with a QSplitter breaks the existing GL widget sizing.
**Why it happens:** QSplitter must be the new central widget, with GL widget and code panel as children.
**How to avoid:** Create QSplitter, add GL widget and code panel, then `setCentralWidget(splitter)`. Set initial sizes with `splitter.setSizes([700, 300])`.
**Warning signs:** GL widget renders at size 0x0 or code panel is invisible.

## Code Examples

### QSplitter Layout for Side-by-Side Panels
```python
# Source: Qt6 QSplitter documentation
from PyQt6.QtWidgets import QSplitter
from PyQt6.QtCore import Qt

# In MainWindow.__init__:
splitter = QSplitter(Qt.Orientation.Horizontal, self)
splitter.addWidget(self._gl_widget)
splitter.addWidget(self._code_panel)
splitter.setSizes([700, 300])  # initial pixel widths
self.setCentralWidget(splitter)
```

### Playback Toolbar with QToolBar
```python
# Source: Qt6 QToolBar + QAction documentation
from PyQt6.QtWidgets import QToolBar, QSlider, QLabel
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

toolbar = QToolBar("Playback", self)
self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, toolbar)

step_back = QAction("<<", self)
step_back.triggered.connect(playback_state.step_backward)
toolbar.addAction(step_back)

play_pause = QAction("Play", self)  # Toggle text: Play/Pause
toolbar.addAction(play_pause)

step_fwd = QAction(">>", self)
step_fwd.triggered.connect(playback_state.step_forward)
toolbar.addAction(step_fwd)

# Position label
pos_label = QLabel("0 / 0")
toolbar.addWidget(pos_label)

# Speed slider
speed_slider = QSlider(Qt.Orientation.Horizontal)
speed_slider.setRange(5, 100)    # 0.5x to 10.0x, stored as 10x value
speed_slider.setValue(10)         # 1.0x default
speed_slider.setFixedWidth(120)
toolbar.addWidget(QLabel("Speed:"))
toolbar.addWidget(speed_slider)

# Scrubber slider
scrubber = QSlider(Qt.Orientation.Horizontal)
scrubber.setRange(0, 0)  # Updated when moves loaded
toolbar.addWidget(scrubber)
```

### QTimer for Auto-Play
```python
# Source: Qt6 QTimer documentation
from PyQt6.QtCore import QTimer

timer = QTimer(self)
timer.timeout.connect(playback_state.step_forward)

def toggle_play():
    if timer.isActive():
        timer.stop()
        play_pause.setText("Play")
    else:
        base_ms = 500
        speed = speed_slider.value() / 10.0  # 0.5 to 10.0
        timer.start(int(base_ms / speed))
        play_pause.setText("Pause")

play_pause.triggered.connect(toggle_play)

# Stop at end
def on_index_changed(index):
    if index >= playback_state.total - 1:
        timer.stop()
        play_pause.setText("Play")
```

### Code Panel Click -> Move Detection (LINK-02)
```python
# Source: Qt6 QPlainTextEdit.cursorPositionChanged signal
def on_cursor_changed():
    cursor = editor.textCursor()
    line = cursor.blockNumber() + 1  # 1-indexed
    # Find move whose source_line matches
    for i, move in enumerate(playback_state._moves):
        if move.source_line == line:
            playback_state.set_index(i)
            break
```

### TCP Triad Geometry Builder
```python
# Build axis line vertices for one waypoint
import pyrr
import numpy as np

def build_triad_vertices(pos: np.ndarray, orient: np.ndarray, length: float = 15.0) -> np.ndarray:
    """Build 6 vertices (3 axis lines) for a TCP orientation triad.

    orient: ABB convention [q1,q2,q3,q4] = [w,x,y,z]
    Returns shape (6, 6) float32 [x,y,z,r,g,b]
    """
    # Convert ABB quaternion to pyrr quaternion [x,y,z,w]
    pyrr_quat = pyrr.Quaternion([orient[1], orient[2], orient[3], orient[0]])
    rot = pyrr.matrix33.create_from_quaternion(pyrr_quat)

    axes = np.eye(3) * length  # 3 unit vectors scaled
    colors = np.array([[1,0,0], [0,1,0], [0,0,1]], dtype=np.float32)  # RGB

    verts = []
    for i in range(3):
        axis_end = pos + rot @ axes[i]
        verts.append([*pos, *colors[i]])
        verts.append([*axis_end, *colors[i]])

    return np.array(verts, dtype=np.float32)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| glSelectBuffer / GL_SELECT render mode | FBO color picking or ray casting | OpenGL 3.0 (2008) | GL_SELECT was removed from core profile. Must use programmatic picking. |
| QRegExp (Qt5) | QRegularExpression (Qt6) | Qt 6.0 | QRegExp is removed from Qt6. QSyntaxHighlighter examples must use QRegularExpression. |
| Qt5 enum style (Qt.AlignLeft) | Qt6 scoped enums (Qt.AlignmentFlag.AlignLeft) | PyQt6 | All code must use fully-qualified enums. |

**Deprecated/outdated:**
- `glLineStipple`: Removed in Core Profile. Dashed lines already handled by fragment shader (Phase 2).
- `QRegExp`: Removed in Qt6. Must use `QRegularExpression` from `PyQt6.QtCore`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-qt 4.4+ |
| Config file | pyproject.toml [tool.pytest.ini_options] |
| Quick run command | `python -m pytest tests/ -x --timeout=10` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLAY-01 | Step forward increments index | unit | `python -m pytest tests/test_playback_state.py::test_step_forward -x` | Wave 0 |
| PLAY-02 | Step backward decrements index | unit | `python -m pytest tests/test_playback_state.py::test_step_backward -x` | Wave 0 |
| PLAY-03 | Auto-play advances through all points | unit | `python -m pytest tests/test_playback_state.py::test_auto_play -x` | Wave 0 |
| PLAY-04 | Current waypoint highlighted in 3D | manual | Visual verification | manual-only (GL rendering) |
| PLAY-05 | Position indicator N/M | unit | `python -m pytest tests/test_playback_toolbar.py::test_position_label -x` | Wave 0 |
| PLAY-06 | Speed slider maps to timer interval | unit | `python -m pytest tests/test_playback_toolbar.py::test_speed_slider -x` | Wave 0 |
| PLAY-07 | Scrubber sets index | unit | `python -m pytest tests/test_playback_toolbar.py::test_scrubber -x` | Wave 0 |
| CODE-01 | Code displayed in panel | unit/integration | `python -m pytest tests/test_code_panel.py::test_code_loaded -x` | Wave 0 |
| CODE-02 | Keywords highlighted | unit | `python -m pytest tests/test_rapid_highlighter.py::test_keyword_formats -x` | Wave 0 |
| CODE-03 | Current line highlighted | unit | `python -m pytest tests/test_code_panel.py::test_line_highlight -x` | Wave 0 |
| LINK-01 | 3D click -> code scroll | integration | `python -m pytest tests/test_linking.py::test_3d_to_code -x` | Wave 0 |
| LINK-02 | Code click -> 3D select | integration | `python -m pytest tests/test_linking.py::test_code_to_3d -x` | Wave 0 |
| PARS-08 | PROC selector filters moves | unit | `python -m pytest tests/test_parser.py::test_proc_filtering -x` | Wave 0 |
| REND-04 | TCP triads rendered | manual | Visual verification | manual-only (GL rendering) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x --timeout=10`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_playback_state.py` -- covers PLAY-01, PLAY-02, PLAY-03
- [ ] `tests/test_playback_toolbar.py` -- covers PLAY-05, PLAY-06, PLAY-07
- [ ] `tests/test_code_panel.py` -- covers CODE-01, CODE-03
- [ ] `tests/test_rapid_highlighter.py` -- covers CODE-02
- [ ] `tests/test_linking.py` -- covers LINK-01, LINK-02
- [ ] `tests/fixtures/multiproc.mod` -- test fixture with multiple PROCs for PARS-08

## Open Questions

1. **PROC boundary tracking granularity**
   - What we know: Parser already extracts `procedures: list[str]` from `RE_PROC.finditer(source)`. Each `MoveInstruction` has `source_line`.
   - What's unclear: Whether to add `proc_name` to `MoveInstruction` dataclass (requires parser change) or track PROC line ranges externally.
   - Recommendation: Add `proc_ranges: dict[str, tuple[int, int]]` to ParseResult. During tokenization, track PROC/ENDPROC statement line numbers. Filter moves by checking `source_line` is within a PROC's range. This avoids modifying the frozen MoveInstruction dataclass.

2. **Waypoint index mapping after PROC filtering**
   - What we know: PlaybackState will hold a filtered `_moves` list. The GL widget renders geometry for ALL moves currently.
   - What's unclear: Should GL widget also re-render to show only the selected PROC's geometry? Or highlight only within the full scene?
   - Recommendation: Re-render geometry for only the selected PROC. This matches user expectation -- selecting a PROC should show only that procedure's path. This means `update_scene()` should accept a filtered move list (or a proc name filter).

3. **Highlight mechanism for current waypoint in GL**
   - What we know: Markers are rendered as GL_POINTS with uniform yellow color.
   - What's unclear: Best approach -- (a) re-upload marker VBO with different color for highlighted point, (b) use a separate small VBO for the highlight marker, (c) pass highlight index as uniform to shader.
   - Recommendation: Option (b) -- maintain a separate small VBO with 1 vertex for the highlighted waypoint, rendered as a larger point (12-16px) with a distinct color (white or red). This avoids re-uploading the full marker VBO on every step. Simple, clean, and O(1) per frame.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.12.9 | -- |
| PyQt6 | All UI | Yes | 6.10.2 | -- |
| PyOpenGL | Rendering | Yes | 3.1.10 | -- |
| pyrr | Quaternion math | Yes | installed | -- |
| NumPy | Ray-cast, geometry | Yes | 2.3.5 | -- |
| pytest | Testing | Yes | 9.0.2 | -- |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.

## Sources

### Primary (HIGH confidence)
- [Qt6 QSyntaxHighlighter Class](https://doc.qt.io/qt-6/qsyntaxhighlighter.html) -- API reference for highlightBlock(), setFormat()
- [Qt6 QPlainTextEdit Class](https://doc.qt.io/qt-6/qplaintextedit.html) -- ExtraSelection, setExtraSelections(), document()
- [Qt6 QSplitter Class](https://doc.qt.io/qt-6/qsplitter.html) -- setSizes(), addWidget()
- [Qt6 QTimer Class](https://doc.qt.io/qt-6/qtimer.html) -- start(), stop(), timeout signal
- [Qt6 QSlider Class](https://doc.qt.io/qt-6/qslider.html) -- valueChanged signal, setRange()
- Existing codebase: `tokens.py` (ParseResult, MoveInstruction, RobTarget with source_line and orient fields)
- Existing codebase: `toolpath_gl_widget.py` (VBO/VAO pipeline, marker rendering, mouse events)
- Existing codebase: `camera.py` (view_matrix, projection_matrix for ray-cast unprojection)

### Secondary (MEDIUM confidence)
- [OpenGL picking tutorial (opengl-tutorial.org)](http://www.opengl-tutorial.org/miscellaneous/clicking-on-objects/picking-with-an-opengl-hack/) -- color picking approach (not recommended, but referenced for comparison)
- [LearnOpenGL Framebuffers](https://learnopengl.com/Advanced-OpenGL/Framebuffers) -- FBO setup reference
- [Qt Syntax Highlighter Example](https://doc.qt.io/qtforpython-6/examples/example_widgets_richtext_syntaxhighlighter.html) -- PySide6 example but API identical to PyQt6

### Tertiary (LOW confidence)
- None -- all findings verified against official Qt6 docs and existing codebase.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are existing PyQt6/PyOpenGL features, already installed and proven in Phase 1-2
- Architecture: HIGH -- PlaybackState signal pattern is standard Qt MVC; all UI components are standard Qt widgets
- Pitfalls: HIGH -- based on direct code review of existing codebase and known Qt6/OpenGL conventions
- Picking approach: HIGH -- ray-cast math is straightforward; waypoint count is small enough that brute-force nearest-point search is instant

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- all technologies are mature releases)
