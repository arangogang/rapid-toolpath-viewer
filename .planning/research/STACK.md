# Technology Stack: Toolpath Editing (v1.1)

**Project:** ABB RAPID Toolpath Viewer — Editing Milestone
**Researched:** 2026-04-01
**Scope:** Stack additions/changes for selection, inspection, modification, deletion, .mod export
**Overall confidence:** HIGH

## Key Finding: No New Dependencies Required

The existing stack (PyQt6 6.10.x + PyOpenGL 3.1.10 + NumPy + pyrr) already provides everything needed for toolpath editing. PyQt6 ships QUndoStack/QUndoCommand in QtGui, QFormLayout/QDoubleSpinBox in QtWidgets for property panels, and standard file I/O for .mod serialization. Adding third-party libraries would be unnecessary complexity.

## Current Stack (Unchanged)

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.11+ | Runtime | Keep |
| PyQt6 | >=6.10 | GUI framework | Keep |
| PyOpenGL | >=3.1.10 | OpenGL bindings | Keep |
| PyOpenGL-accelerate | >=3.1.10 | C-accelerated paths | Keep |
| pyrr | >=0.10.3 | 3D math | Keep |
| NumPy | >=1.26 | Array computation | Keep |

## New Capabilities from Existing Stack

### 1. Undo/Redo: PyQt6.QtGui.QUndoStack + QUndoCommand

**What it provides:** Full undo/redo framework with command history, clean-state tracking, and automatic QAction creation for menu integration.

**Why use it (not a custom stack):**
- Already bundled in PyQt6.QtGui -- zero additional dependency
- `createUndoAction()` / `createRedoAction()` auto-generate Edit menu items with Ctrl+Z/Ctrl+Y
- `isClean()` / `cleanChanged` signal enables "unsaved changes" detection for window title asterisk
- Command merging via `mergeWith()` lets consecutive offset edits on the same waypoint compress into one undo step
- Battle-tested in Qt for 20+ years

**Integration point:** MainWindow creates one QUndoStack instance. Each edit operation (modify position, change speed, delete waypoint) is a QUndoCommand subclass pushed onto the stack. The command's `redo()` mutates the data model and `undo()` restores it.

**Import:** `from PyQt6.QtGui import QUndoStack, QUndoCommand`

**Confidence:** HIGH (verified in Qt 6.10/6.11 official docs)

### 2. Property Inspector Panel: PyQt6.QtWidgets (QFormLayout, QDoubleSpinBox, QComboBox, QLabel)

**What it provides:** Two-column label+field layout for displaying and editing waypoint properties (X/Y/Z coordinates, speed, zone, laser state).

**Key widgets for the inspector:**

| Widget | Purpose | Why |
|--------|---------|-----|
| QFormLayout | Label-field two-column layout | Platform-native alignment (Windows left-aligned labels) |
| QDoubleSpinBox | X, Y, Z coordinate editing | Built-in validation, decimal precision control, step increment via arrows |
| QComboBox | Speed (v100, v500...) and zone (fine, z10...) selection | Constrained choices, prevents invalid input |
| QCheckBox | Laser on/off toggle | Binary state, clear UX |
| QLabel | Read-only fields (move type, target name, source line) | Non-editable display |
| QGroupBox | Section grouping (Position, Motion Parameters, Tool) | Visual hierarchy |

**Integration point:** New `InspectorPanel` widget as a QDockWidget or third pane in the existing QSplitter. Connected to PlaybackState.current_changed signal -- when the selected waypoint changes, the panel updates.

**Confidence:** HIGH (standard PyQt6 widgets, no version concerns)

### 3. Multi-Selection in 3D Viewer: Existing OpenGL picking + NumPy

**What it provides:** Rubber-band rectangle selection and Ctrl+click multi-select using the existing ray-cast picking infrastructure.

**Key additions (all from existing stack):**
- `QRubberBand` (PyQt6.QtWidgets) for visual drag-select rectangle
- NumPy batch screen-space projection (already implemented in `_try_pick`) extended to return all points within a rectangle instead of the nearest one
- Selection state stored as `set[int]` of waypoint indices

**No new rendering infrastructure needed:** Selected waypoints can be highlighted by uploading a separate VBO with selected-point colors (e.g., cyan) using the existing `_create_vao_vbo` / `_upload_vbo` pattern. The marker shader already supports per-vertex color.

**Confidence:** HIGH

### 4. .mod File Serialization: Python str + pathlib (stdlib)

**What it provides:** Export modified toolpath back to a valid ABB RAPID .mod file.

**Why no template engine or AST library is needed:**
- The .mod format is line-based text, not a complex tree structure
- Approach: **line-level patching** of the original source text, not full regeneration
  - For coordinate edits: find the robtarget declaration line, regex-replace the bracket data
  - For speed/zone edits: find the MoveL/MoveJ line, regex-replace the parameter
  - For deletions: remove the move instruction line (and optionally the orphaned robtarget declaration)
  - For SetDO changes: insert/modify SetDO lines before the move instruction
- This preserves original formatting, comments, and non-parsed content (critical for robot engineers who expect their file structure to be maintained)

**Why NOT full AST regeneration:**
- .mod files contain content the parser ignores (comments, TPWrite, WaitTime, custom functions)
- Full regeneration would lose this content, making the tool unusable for real-world files
- Line-level patching is simpler, safer, and preserves user intent

**Key pattern:**
```python
lines = source_text.splitlines()
lines[target_line - 1] = new_line_content  # 1-indexed to 0-indexed
output = "\n".join(lines)
Path(output_path).write_text(output, encoding="utf-8")
```

**Integration point:** New `rapid_viewer/serializer/mod_writer.py` module. Uses ParseResult metadata (source_line fields on MoveInstruction and RobTarget) to locate lines to modify.

**Confidence:** HIGH

### 5. Mutable Edit Model: Python dataclasses (stdlib)

**What it provides:** A mutable layer on top of the frozen ParseResult/MoveInstruction tokens.

**Current problem:** `MoveInstruction` and `RobTarget` are `frozen=True` dataclasses. They cannot be modified in place.

**Solution:** Use `dataclasses.replace()` (already imported in main_window.py) to create modified copies. The edit model wraps ParseResult with a mutable list of moves and a dict tracking pending modifications:

```python
@dataclass
class EditableScene:
    """Mutable wrapper over ParseResult for editing operations."""
    original: ParseResult          # immutable reference
    moves: list[MoveInstruction]   # mutable copy of original.moves
    targets: dict[str, RobTarget]  # mutable copy
    pending_changes: dict[int, MoveInstruction]  # source_line -> modified move
    deleted_lines: set[int]        # source lines to remove on export
```

**Why not make tokens mutable:** Frozen dataclasses provide hashability and safety guarantees for the parser. The edit layer should be separate from the parse layer -- separation of concerns.

**Confidence:** HIGH (stdlib dataclasses, no external dependency)

## What NOT to Add

| Library | Why Not | Use Instead |
|---------|---------|-------------|
| **jinja2 / mako** (template engines) | Overkill for .mod text patching. Templates imply full file regeneration which loses comments and formatting. | Direct string manipulation with `str.splitlines()` and line-index replacement |
| **python-undo / undoable** (3rd-party undo libs) | PyQt6's QUndoStack is better integrated (signals, QActions, clean-state tracking). Adding a separate undo lib creates two competing systems. | PyQt6.QtGui.QUndoStack |
| **attrs / pydantic** (data modeling) | Dataclasses are sufficient. The edit model is simple (one wrapper class + replace()). Pydantic's validation overhead is unnecessary for internal data. | stdlib dataclasses + dataclasses.replace() |
| **copy / deepcopy** (for undo state snapshots) | Storing full ParseResult snapshots per undo step wastes memory (files with 10k+ waypoints). QUndoCommand's redo/undo should store only the delta. | QUndoCommand with targeted field storage (old_value/new_value pattern) |
| **PyQt6-3D** | Selection highlighting and inspector UI are 2D widget concerns, not 3D scene graph concerns. The existing OpenGL pipeline handles all 3D needs. | Existing QOpenGLWidget + shader pipeline |
| **pandas** | No tabular data analysis needed. NumPy arrays are sufficient for coordinate math. | NumPy |
| **lark / pyparsing** (parser generators) | The .mod serializer patches existing text at known line numbers. No parsing needed for export. The existing regex parser handles import. | Line-index string manipulation |

## Architecture Impact on Existing Code

### Tokens (parser/tokens.py) -- Minor Change
- Keep all dataclasses frozen
- Add one field to `MoveInstruction`: `original_stmt: str | None = None` to store the raw statement text for serialization (enables line-patching without re-parsing)
- Alternative: reconstruct statement from fields during export (simpler but less faithful to original formatting)

### GL Widget (renderer/toolpath_gl_widget.py) -- Moderate Change
- Add selection rendering (selected waypoints VBO with distinct color)
- Add `QRubberBand` for rectangle selection
- Extend `_try_pick` to return multiple indices for rectangle pick
- Add `set_selected_indices(indices: set[int])` public method

### MainWindow (ui/main_window.py) -- Moderate Change
- Add QUndoStack instance
- Add Edit menu (Undo, Redo, Delete)
- Add File > Save As action for .mod export
- Add InspectorPanel as QDockWidget or splitter pane
- Wire inspector edits -> QUndoCommand -> data model -> GL update

### New Modules Required
| Module | Purpose |
|--------|---------|
| `ui/inspector_panel.py` | Property editing panel (QFormLayout-based) |
| `serializer/mod_writer.py` | .mod file export via line-patching |
| `model/edit_scene.py` | Mutable edit model wrapping ParseResult |
| `model/commands.py` | QUndoCommand subclasses (ModifyPosition, ModifySpeed, DeleteWaypoint, etc.) |

## Installation

No changes to pyproject.toml dependencies. Existing install command works:

```bash
uv sync
```

No new packages. All new code uses PyQt6 and stdlib.

## Sources

- [QUndoStack Class | Qt GUI | Qt 6.11.0](https://doc.qt.io/qt-6/qundostack.html) -- confirmed in QtGui module, API verified
- [QUndoCommand Class | Qt GUI | Qt 6.11.0](https://doc.qt.io/qt-6/qundocommand.html) -- redo/undo/mergeWith pattern
- [Overview of Qt's Undo Framework | Qt 6.10](https://doc.qt.io/qt-6/qundo.html) -- architecture guide
- [QFormLayout Class | Qt Widgets | Qt 6.11.0](https://doc.qt.io/qt-6/qformlayout.html) -- two-column property panel layout
- [Undo Framework Example | Qt 6.10.1](https://doc.qt.io/qt-6/qtwidgets-tools-undoframework-example.html) -- reference implementation pattern
