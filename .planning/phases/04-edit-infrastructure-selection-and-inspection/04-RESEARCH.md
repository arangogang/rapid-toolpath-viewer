# Phase 4: Edit Infrastructure, Selection, and Inspection - Research

**Researched:** 2026-04-01
**Domain:** PyQt6 undo/redo infrastructure, 3D selection model, property panel UI
**Confidence:** HIGH

## Summary

Phase 4 builds three interconnected subsystems on top of the existing v1.0 viewer: (1) a mutable EditModel wrapping frozen parser tokens with QUndoStack-based undo/redo, (2) a SelectionState managing single/multi-select of waypoints in the 3D viewer, and (3) a read-only property inspection panel. No actual edit operations are performed in this phase -- the infrastructure is wired so Phase 5 can add mutations immediately.

The existing codebase provides strong patterns to follow. PlaybackState (QObject + pyqtSignal) is the template for SelectionState. The GL widget already has ray-cast picking (`waypoint_clicked` signal) and a highlight marker draw pass that can be extended for multi-selection rendering. QUndoStack lives in `PyQt6.QtGui` (verified on dev machine) and provides `createUndoAction`/`createRedoAction` that auto-manage enabled/disabled state and shortcut text.

**Primary recommendation:** Build EditModel as a QObject owning QUndoStack, with SelectionState as a separate QObject. Wire both into MainWindow alongside existing PlaybackState. Property panel is a simple QFormLayout widget placed below the code panel in a vertical QSplitter.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Create a new `SelectionState` class (QObject) separate from `PlaybackState`. PlaybackState continues to manage playback cursor (current_index). SelectionState manages a `set[int]` of selected waypoint indices.
- **D-02:** Plain click on a waypoint: updates both PlaybackState.current_index AND replaces SelectionState to just that point. Shift/Ctrl+click: toggles the clicked point in SelectionState, and moves PlaybackState.current_index to the clicked point. Code panel always follows current_index.
- **D-03:** Property panel placed below the code panel in the right pane (vertical QSplitter within the existing right side of the horizontal QSplitter). Layout: [3D Viewport | Code Panel / Property Panel].
- **D-04:** When multiple waypoints are selected, property panel shows the last-clicked point's properties (current_index). Header displays selection count (e.g., "3 points selected"). Phase 5 batch edits will apply to all selected points.
- **D-05:** Selection visual feedback uses color changes only, no size or shape changes. Unselected markers: yellow (existing). Selected markers: cyan or white. Current marker (last clicked): red/magenta (existing highlight color). Path lines remain unchanged.
- **D-06:** EditModel holds a list of mutable `EditPoint` objects, each wrapping one frozen `MoveInstruction`. EditPoint has mutable fields: `pos` (np.ndarray copy), `speed`, `zone`, `laser_on`, `deleted` flag. Original `MoveInstruction` kept as reference for diff/export.
- **D-07:** EditModel owns the `QUndoStack`. All mutations go through EditModel methods that internally create QUndoCommands. MainWindow connects Edit menu Undo/Redo actions to `undo_stack.undo()`/`redo()`.
- **D-08:** Undo/Redo actions visible in Edit menu from Phase 4 (Ctrl+Z/Ctrl+Y), but disabled until edits are made in Phase 5.
- **D-09:** Title bar shows dirty-state indicator (asterisk) when EditModel has uncommitted changes (any EditPoint differs from its original).

### Claude's Discretion
- Signal names for SelectionState (e.g., `selection_changed`, `selection_cleared`)
- Exact color values for selected vs current markers (within the cyan/white and red/magenta guidance)
- Internal EditPoint field layout and helper methods
- QUndoCommand subclass naming and structure (placeholder commands for Phase 4)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EDIT-01 | Mutable EditModel layer -- frozen parser token wrapper for all editing | EditModel with EditPoint dataclass wrapping MoveInstruction; QObject pattern from PlaybackState |
| EDIT-02 | QUndoStack-based Undo/Redo (Ctrl+Z/Y) -- all edits as QUndoCommand | QUndoStack in PyQt6.QtGui verified; createUndoAction/createRedoAction auto-manage enabled state |
| SEL-01 | Single waypoint selection in 3D viewer with code line highlight | Extend existing waypoint_clicked signal + mouseReleaseEvent; SelectionState QObject |
| SEL-02 | Shift/Ctrl multi-select with visual distinction | Qt modifier key detection via event.modifiers(); multi-highlight VBO for selected markers |
| INSP-01 | Property panel showing coordinates, speed, zone, laser state | QFormLayout-based widget reading from EditModel via current_index |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech Stack**: Python + PyQt6 + PyOpenGL only
- **Platform**: Windows desktop only
- **Scope**: Code verification viewer -- no editing of RAPID code text
- **Conventions**: `from __future__ import annotations` in all modules; ruff formatting; type hints on public APIs
- **Qt patterns**: PyQt6 fully-qualified enums; pyqtSignal for state changes; blockSignals for programmatic updates
- **OpenGL**: 3.3 Core Profile; interleaved [x,y,z,r,g,b] float32 vertex layout
- **Testing**: pytest + pytest-qt; `_make_move()` helper pattern; test by requirement ID
- **GSD workflow**: Use GSD commands for all repo edits

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyQt6 | >=6.10 | QUndoStack, QUndoCommand, QFormLayout, QAction | Already in stack; QUndoStack is in PyQt6.QtGui |
| NumPy | >=1.26 | EditPoint pos array copies, vertex buffer construction | Already in stack |
| PyOpenGL | >=3.1.10 | Multi-selection marker rendering (VBO updates) | Already in stack |

### No New Dependencies
This phase requires zero new packages. All functionality comes from PyQt6 and existing dependencies.

## Architecture Patterns

### New Module Locations
```
src/rapid_viewer/
  ui/
    selection_state.py    # NEW: SelectionState QObject (set[int] + signals)
    edit_model.py         # NEW: EditModel QObject (EditPoint list + QUndoStack)
    property_panel.py     # NEW: PropertyPanel QWidget (QFormLayout)
  renderer/
    toolpath_gl_widget.py # MODIFY: multi-select rendering, modifier key handling
  ui/
    main_window.py        # MODIFY: vertical QSplitter, Edit menu, signal wiring
```

### Pattern 1: SelectionState (mirrors PlaybackState)
**What:** QObject with `set[int]` of selected indices and pyqtSignal emissions
**When to use:** Whenever selection changes need to propagate to multiple UI components

```python
# Recommended implementation pattern
from PyQt6.QtCore import QObject, pyqtSignal

class SelectionState(QObject):
    """Observable selection model for waypoint multi-select.

    Signals:
        selection_changed(set): Emitted when selection set changes. Payload is frozenset of indices.
    """
    selection_changed = pyqtSignal(object)  # frozenset[int] -- use object because pyqtSignal doesn't support set

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._selected: set[int] = set()

    @property
    def selected_indices(self) -> frozenset[int]:
        return frozenset(self._selected)

    def select_single(self, index: int) -> None:
        """Replace selection with single index."""
        self._selected = {index}
        self.selection_changed.emit(frozenset(self._selected))

    def toggle(self, index: int) -> None:
        """Add or remove index from selection (Ctrl+click)."""
        if index in self._selected:
            self._selected.discard(index)
        else:
            self._selected.add(index)
        self.selection_changed.emit(frozenset(self._selected))

    def extend_to(self, index: int) -> None:
        """Shift+click: toggle the clicked point (per D-02, same as Ctrl behavior for this phase)."""
        self.toggle(index)

    def clear(self) -> None:
        self._selected.clear()
        self.selection_changed.emit(frozenset())
```

**Note on pyqtSignal type:** `pyqtSignal(set)` does not work in PyQt6 -- use `pyqtSignal(object)` and pass `frozenset[int]`.

### Pattern 2: EditModel with QUndoStack
**What:** QObject holding mutable EditPoint list and owning the QUndoStack
**When to use:** Single source of truth for all mutable state

```python
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QUndoStack

class EditModel(QObject):
    """Mutable edit layer over frozen parser tokens.

    Signals:
        model_changed(): Emitted when any EditPoint changes (undo/redo/edit).
        dirty_changed(bool): Emitted when dirty state changes.
    """
    model_changed = pyqtSignal()
    dirty_changed = pyqtSignal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._undo_stack = QUndoStack(self)
        self._points: list[EditPoint] = []
        self._undo_stack.cleanChanged.connect(self._on_clean_changed)

    @property
    def undo_stack(self) -> QUndoStack:
        return self._undo_stack

    @property
    def is_dirty(self) -> bool:
        return not self._undo_stack.isClean()

    def load(self, moves: list[MoveInstruction]) -> None:
        """Initialize from parsed moves. Clears undo history."""
        self._points = [EditPoint.from_move(m) for m in moves]
        self._undo_stack.clear()
        self._undo_stack.setClean()
        self.model_changed.emit()

    def _on_clean_changed(self, clean: bool) -> None:
        self.dirty_changed.emit(not clean)
```

### Pattern 3: EditPoint Dataclass
**What:** Mutable wrapper around frozen MoveInstruction

```python
from dataclasses import dataclass, field
import numpy as np
from rapid_viewer.parser.tokens import MoveInstruction

@dataclass
class EditPoint:
    """Mutable copy of a MoveInstruction for editing."""
    original: MoveInstruction          # reference to frozen source
    pos: np.ndarray                    # mutable copy of target.pos
    speed: str                         # mutable copy
    zone: str                          # mutable copy
    laser_on: bool                     # mutable copy
    deleted: bool = False              # soft-delete flag

    @classmethod
    def from_move(cls, move: MoveInstruction) -> EditPoint:
        pos = move.target.pos.copy() if move.target is not None else np.zeros(3)
        return cls(
            original=move,
            pos=pos,
            speed=move.speed,
            zone=move.zone,
            laser_on=move.laser_on,
        )
```

### Pattern 4: QUndoStack Auto-Actions for Edit Menu
**What:** `createUndoAction`/`createRedoAction` return QActions that auto-enable/disable
**Critical detail:** These actions are automatically disabled when the stack is empty (Phase 4 behavior: always disabled since no edits exist yet).

```python
# In MainWindow._setup_menu():
edit_menu = menu_bar.addMenu("&Edit")

# createUndoAction and createRedoAction auto-manage enabled state
undo_action = self._edit_model.undo_stack.createUndoAction(self, "&Undo")
undo_action.setShortcut("Ctrl+Z")
edit_menu.addAction(undo_action)

redo_action = self._edit_model.undo_stack.createRedoAction(self, "&Redo")
redo_action.setShortcut("Ctrl+Y")
edit_menu.addAction(redo_action)
```

**Verified:** `createUndoAction` returns a `QAction` (from `PyQt6.QtGui`) that starts disabled when stack is empty. No manual enable/disable management needed.

### Pattern 5: Multi-Selection Rendering in GL Widget
**What:** Render selected markers with different color via a separate VBO
**How:** When selection changes, rebuild a small VBO of selected marker vertices with cyan color, draw as GL_POINTS with same marker shader but different color.

```python
# In ToolpathGLWidget:
def set_selected_indices(self, indices: frozenset[int]) -> None:
    """Update the selection highlight VBO with cyan-colored markers."""
    if self._waypoint_positions is None or not indices:
        self._selected_count = 0
        self.update()
        return

    valid = [i for i in indices if 0 <= i < len(self._waypoint_positions)]
    if not valid:
        self._selected_count = 0
        self.update()
        return

    # Build vertex array: [x, y, z, r, g, b] with cyan color
    verts = np.zeros((len(valid), 6), dtype=np.float32)
    for j, idx in enumerate(valid):
        verts[j, :3] = self._waypoint_positions[idx]
        verts[j, 3:] = [0.0, 1.0, 1.0]  # cyan

    self.makeCurrent()
    self._upload_vbo(self._selected_vbo, verts)
    self._selected_count = len(valid)
    self.doneCurrent()
    self.update()
```

### Pattern 6: Modifier Key Detection
**What:** Detect Shift/Ctrl on mouse click in ToolpathGLWidget

```python
# In mouseReleaseEvent, after pick succeeds:
modifiers = event.modifiers()
shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
ctrl = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
# Emit signal with modifiers so MainWindow can route to SelectionState
```

**Design choice:** Emit a richer signal (e.g., `waypoint_picked(int, bool, bool)` for index, shift, ctrl) or keep `waypoint_clicked(int)` and have MainWindow query modifiers from QApplication. Recommended: extend signal to carry modifiers, keeping the GL widget stateless about selection logic.

### Pattern 7: Property Panel Layout
**What:** QFormLayout-based read-only display

```python
# Property panel structure
class PropertyPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._header = QLabel("No selection")
        self._x_label = QLabel("-")
        self._y_label = QLabel("-")
        self._z_label = QLabel("-")
        self._speed_label = QLabel("-")
        self._zone_label = QLabel("-")
        self._laser_label = QLabel("-")

        layout = QVBoxLayout(self)
        layout.addWidget(self._header)

        form = QFormLayout()
        form.addRow("X:", self._x_label)
        form.addRow("Y:", self._y_label)
        form.addRow("Z:", self._z_label)
        form.addRow("Speed:", self._speed_label)
        form.addRow("Zone:", self._zone_label)
        form.addRow("Laser:", self._laser_label)
        layout.addLayout(form)
```

### Pattern 8: Vertical QSplitter in Right Pane (D-03)
**What:** Nest a vertical QSplitter inside the right side of the existing horizontal QSplitter

```python
# In MainWindow.__init__():
# Right pane: vertical splitter with code panel (top) + property panel (bottom)
right_splitter = QSplitter(Qt.Orientation.Vertical, self)
right_splitter.addWidget(self._code_panel)
right_splitter.addWidget(self._property_panel)
right_splitter.setSizes([500, 200])

# Main splitter: GL widget (left) | right_splitter (right)
splitter = QSplitter(Qt.Orientation.Horizontal, self)
splitter.addWidget(self._gl_widget)
splitter.addWidget(right_splitter)
splitter.setSizes([700, 300])
```

### Pattern 9: Title Bar Dirty Indicator (D-09)
**What:** Show asterisk in title when EditModel is dirty

```python
# In MainWindow, connected to EditModel.dirty_changed:
def _on_dirty_changed(self, dirty: bool) -> None:
    base = self.windowTitle().rstrip(" *")
    if dirty:
        self.setWindowTitle(f"{base} *")
    else:
        self.setWindowTitle(base)
```

### Anti-Patterns to Avoid
- **Merging SelectionState into PlaybackState:** Violates D-01. Selection and playback are independent concerns -- playback auto-advances, selection is user-driven.
- **Storing selection in GL widget:** GL widget should be stateless about selection logic. It receives indices to render, nothing more.
- **Manual QAction enable/disable for undo/redo:** Use `createUndoAction`/`createRedoAction` which auto-manage this.
- **Mutable MoveInstruction:** Never mutate frozen dataclasses. EditPoint exists specifically to hold mutable copies.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Undo/Redo state machine | Custom undo list | `QUndoStack` + `QUndoCommand` | Handles command merging, clean state tracking, action creation |
| Undo/Redo menu actions | Manual QAction with enable/disable | `QUndoStack.createUndoAction()` / `createRedoAction()` | Auto-manages enabled state, text updates, shortcuts |
| Dirty state tracking | Custom flag comparison | `QUndoStack.isClean()` + `cleanChanged` signal | Already tracks clean/dirty relative to last setClean() call |

## Common Pitfalls

### Pitfall 1: pyqtSignal with set type
**What goes wrong:** `pyqtSignal(set)` or `pyqtSignal(frozenset)` fails at class definition time in PyQt6.
**Why it happens:** PyQt6 signal type system only supports registered metatypes. `set` and `frozenset` are not registered.
**How to avoid:** Use `pyqtSignal(object)` and document that the payload is `frozenset[int]`.
**Warning signs:** `TypeError` at class definition time, not at emit time.

### Pitfall 2: QUndoStack import location
**What goes wrong:** `from PyQt6.QtWidgets import QUndoStack` fails.
**Why it happens:** In PyQt6, QUndoStack and QUndoCommand moved to `QtGui`, not `QtWidgets` (unlike Qt5).
**How to avoid:** `from PyQt6.QtGui import QUndoStack, QUndoCommand`.
**Warning signs:** `ImportError: cannot import name 'QUndoStack' from 'PyQt6.QtWidgets'`.

### Pitfall 3: EditModel initialization order
**What goes wrong:** EditModel created before parse result is available, then load_file tries to access it.
**Why it happens:** EditModel needs to exist for Edit menu wiring, but has no data until file load.
**How to avoid:** EditModel starts empty (no points). `load_file()` calls `edit_model.load(parse_result.moves)` after parsing.
**Warning signs:** IndexError or empty property panel after file load.

### Pitfall 4: Selection indices invalidation on file reload
**What goes wrong:** Selection holds indices from previous file; new file has different move count.
**Why it happens:** Selection is not cleared when a new file is loaded.
**How to avoid:** `load_file()` must call `selection_state.clear()` before setting new moves.
**Warning signs:** Cyan markers at wrong positions or index out of range after loading new file.

### Pitfall 5: PROC filter vs EditModel index mapping
**What goes wrong:** EditModel indices don't match filtered PlaybackState indices after PROC filter.
**Why it happens:** PlaybackState operates on filtered moves; EditModel holds ALL moves.
**How to avoid:** EditModel always holds ALL moves. PROC filtering applies to display only. Selection indices map to EditModel indices (which are the same as "all moves" indices). When PROC filter is active, selection/inspection still references the EditModel's global index.
**Warning signs:** Property panel shows wrong waypoint data after switching PROC filter.

### Pitfall 6: GL context guard for selection VBO upload
**What goes wrong:** `makeCurrent()` hangs or crashes in headless tests.
**Why it happens:** No valid GL context available outside of `paintGL` lifecycle.
**How to avoid:** Check `_has_gl_context()` (existing pattern) before any VBO upload in `set_selected_indices()`.
**Warning signs:** Test hangs on `makeCurrent()` call.

## Code Examples

### QUndoStack Wiring (verified on dev machine)
```python
# Source: Verified via Python REPL on dev machine (PyQt6.QtGui)
from PyQt6.QtGui import QUndoStack, QUndoCommand

stack = QUndoStack()
# createUndoAction returns QAction, starts disabled when stack empty
undo_action = stack.createUndoAction(None, "&Undo")
assert not undo_action.isEnabled()  # True: no commands to undo

# cleanChanged(bool) signal: True = clean, False = dirty
stack.cleanChanged.connect(lambda clean: print(f"clean={clean}"))
```

### Qt Modifier Key Check (verified API)
```python
# Source: PyQt6 Qt.KeyboardModifier enum
from PyQt6.QtCore import Qt

def check_modifiers(event):
    mods = event.modifiers()
    shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
    ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
    return shift, ctrl
```

### QFormLayout Property Display
```python
# Source: PyQt6 QFormLayout pattern
from PyQt6.QtWidgets import QFormLayout, QLabel, QWidget, QVBoxLayout

class PropertyPanel(QWidget):
    def update_from_point(self, point: EditPoint | None) -> None:
        if point is None:
            self._header.setText("No selection")
            for lbl in [self._x_label, self._y_label, self._z_label,
                        self._speed_label, self._zone_label, self._laser_label]:
                lbl.setText("-")
            return
        self._x_label.setText(f"{point.pos[0]:.3f}")
        self._y_label.setText(f"{point.pos[1]:.3f}")
        self._z_label.setText(f"{point.pos[2]:.3f}")
        self._speed_label.setText(point.speed)
        self._zone_label.setText(point.zone)
        self._laser_label.setText("ON" if point.laser_on else "OFF")
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x + pytest-qt 4.x |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/ -x --tb=short` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDIT-01 | EditModel wraps MoveInstruction into mutable EditPoint | unit | `python -m pytest tests/test_edit_model.py -x` | Wave 0 |
| EDIT-01 | EditModel.load() populates points from ParseResult.moves | unit | `python -m pytest tests/test_edit_model.py::test_load -x` | Wave 0 |
| EDIT-02 | QUndoStack created and accessible via edit_model.undo_stack | unit | `python -m pytest tests/test_edit_model.py::test_undo_stack -x` | Wave 0 |
| EDIT-02 | Undo/Redo actions in Edit menu, disabled when stack empty | widget | `python -m pytest tests/test_main_window.py::test_edit_menu -x` | Wave 0 |
| SEL-01 | Single click selects waypoint, emits selection_changed | unit | `python -m pytest tests/test_selection_state.py::test_select_single -x` | Wave 0 |
| SEL-02 | Ctrl+click toggles selection, Shift+click toggles selection | unit | `python -m pytest tests/test_selection_state.py::test_toggle -x` | Wave 0 |
| INSP-01 | PropertyPanel displays X,Y,Z, speed, zone, laser from EditPoint | widget | `python -m pytest tests/test_property_panel.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x --tb=short`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_edit_model.py` -- covers EDIT-01, EDIT-02
- [ ] `tests/test_selection_state.py` -- covers SEL-01, SEL-02
- [ ] `tests/test_property_panel.py` -- covers INSP-01
- No framework install needed (pytest + pytest-qt already configured)

## Sources

### Primary (HIGH confidence)
- PyQt6.QtGui QUndoStack API -- verified via Python REPL on dev machine (PyQt6 6.10)
- PyQt6.QtGui QUndoCommand API -- verified via Python REPL on dev machine
- Existing codebase: PlaybackState, ToolpathGLWidget, MainWindow, CodePanel, GeometryBuilder

### Secondary (MEDIUM confidence)
- Qt6 documentation patterns for QUndoStack/QUndoCommand lifecycle (training data, consistent with verified API)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies; all APIs verified on dev machine
- Architecture: HIGH - patterns directly extend existing codebase (PlaybackState, GL widget)
- Pitfalls: HIGH - QUndoStack import location and pyqtSignal type constraints verified empirically

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (stable stack, no moving targets)
