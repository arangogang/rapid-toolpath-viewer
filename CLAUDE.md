<!-- GSD:project-start source:PROJECT.md -->
## Project

**ABB RAPID Toolpath Viewer**

ABB RAPID 로봇 프로그램 파일(.mod)을 불러와 툴패스를 3D로 시각화하는 Windows 데스크탑 애플리케이션이다. 로봇 엔지니어가 RAPID 코드를 실제 로봇에 올리기 전에 경로의 정확성을 검증하는 도구다.

**Core Value:** .mod 파일을 열면 즉시 3D 툴패스가 렌더링되고, 각 워크포인트를 클릭하면 해당 RAPID 코드 줄로 이동할 수 있어야 한다.

### Constraints

- **Tech Stack**: Python + PyQt6 + PyOpenGL — 빠른 구현, 사용자가 명시적 선택
- **Platform**: Windows 데스크탑 전용
- **Scope**: 코드 검증 뷰어 — 편집/시뮬레이션 기능 없음
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12.9 (runtime on dev machine) - requires `>=3.11` per `pyproject.toml`
- GLSL 3.30 Core - OpenGL shaders defined as string constants in `src/rapid_viewer/renderer/shaders.py`
- Batch script - `build.bat` for Windows build automation
## Runtime
- CPython 3.12.9 on Windows 11 Pro
- OpenGL 3.3 Core Profile context (set in `src/rapid_viewer/main.py` via `QSurfaceFormat`)
- uv (recommended in CLAUDE.md, no `uv.lock` file present)
- No lockfile detected - dependencies specified only in `pyproject.toml`
## Frameworks
- PyQt6 `>=6.10` - GUI framework, provides QMainWindow, QOpenGLWidget, QSyntaxHighlighter, signal/slot system
- PyOpenGL `>=3.1.10` - Raw OpenGL 3.3 Core Profile bindings (VBO/VAO/shader pipeline, no fixed-function)
- NumPy `>=1.26` - Vertex buffer construction, coordinate transforms, array math
- pytest `>=9.0` - Test runner, configured in `pyproject.toml` `[tool.pytest.ini_options]`
- pytest-qt `>=4.4` - Qt widget testing support
- PyInstaller `>=6.0` - Bundles into single Windows `.exe` (spec file: `rapid_viewer.spec`)
- ruff - Linting and formatting (line-length: 100, configured in `pyproject.toml`)
- hatchling - Build backend (`[build-system]` in `pyproject.toml`)
## Key Dependencies
- `PyQt6>=6.10` - Entire GUI framework; QOpenGLWidget hosts the 3D viewport
- `PyOpenGL>=3.1.10` - All rendering calls (GL_LINES, GL_POINTS, shader compilation)
- `PyOpenGL-accelerate>=3.1.10` - C-accelerated paths for PyOpenGL (must match PyOpenGL version exactly)
- `pyrr>=0.10.3` - 3D math: quaternion rotation, matrix44 creation (view/projection/MVP), arcball camera math
- `numpy>=1.26` - Vertex array construction, coordinate transforms, ray-cast picking math
- `PyInstaller>=6.0` - Distribution packaging (spec: `rapid_viewer.spec`, output: `dist/rapid_viewer.exe`)
## PyQt6 Modules Used
- `PyQt6.QtWidgets` - QMainWindow, QSplitter, QFileDialog, QMessageBox, QPlainTextEdit, QToolBar, QSlider, QComboBox, QLabel
- `PyQt6.QtGui` - QAction, QSurfaceFormat, QSyntaxHighlighter, QFont, QColor, QTextCharFormat, QTextCursor
- `PyQt6.QtCore` - Qt, QTimer, QObject, QRegularExpression, pyqtSignal
- `PyQt6.QtOpenGLWidgets` - QOpenGLWidget (3D viewport base class)
## Configuration
- No `.env` files present - application has no external service dependencies
- No environment variables required at runtime
- OpenGL 3.3 Core Profile forced globally before QApplication creation (`src/rapid_viewer/main.py` lines 23-27)
- `pyproject.toml` - All project metadata, dependencies, pytest config, ruff config
- `rapid_viewer.spec` - PyInstaller spec with explicit hidden imports for PyOpenGL dynamic imports and PyQt6 plugins
- `build.bat` - Windows batch script that cleans `build/` and `dist/`, runs PyInstaller, verifies output
- Entry point: `src/rapid_viewer/main.py`
- Console: disabled (GUI-only app)
- UPX compression: disabled (avoids antivirus false positives)
- Icon: `rapid_viewer.ico`
- Excluded packages: tkinter, matplotlib, scipy, PIL, IPython
- Hidden imports: all rapid_viewer submodules, PyQt6 modules, OpenGL modules, numpy
## Platform Requirements
- Python 3.11+ (3.12 recommended)
- Windows (primary target; no macOS/Linux testing indicated)
- GPU with OpenGL 3.3 Core Profile support
- uv package manager (recommended)
- Windows desktop (single `.exe` via PyInstaller, no Python installation needed)
- GPU with OpenGL 3.3 Core Profile support
- No network connectivity required (fully offline desktop app)
## Python Version Notes
- `pyproject.toml` specifies `requires-python = ">=3.11"`
- CLAUDE.md recommends avoiding Python 3.13 until C-extension dependency compatibility is confirmed
- Development machine runs Python 3.12.9
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Language & Style
- **Python 3.11+** with `from __future__ import annotations` in all modules
- **Ruff** for linting/formatting, line length 100 (`pyproject.toml [tool.ruff]`)
- No explicit flake8/black/isort — ruff handles all
## Naming
| Entity | Convention | Examples |
|--------|-----------|----------|
| Modules | snake_case | `rapid_parser.py`, `geometry_builder.py`, `playback_state.py` |
| Classes | PascalCase | `ArcballCamera`, `PlaybackState`, `ToolpathGLWidget` |
| Functions/methods | snake_case | `parse_module()`, `orbit_start()`, `update_scene()` |
| Constants | UPPER_SNAKE | `APP_TITLE`, `SOLID_VERT`, `GL_LINES` |
| Private members | `_` prefix | `_parse_result`, `_gl_ready`, `_current_index` |
| Test functions | `test_` prefix | `test_parse_movel()`, `test_camera_instantiates()` |
## Type Annotations
- All public APIs have type hints (parameters + return types)
- `np.ndarray` used for array types (no shape/dtype annotation)
- Union types use `X | None` syntax (3.10+ style)
- `tuple[int, ...]` and `list[MoveInstruction]` for container types
## Docstrings
- All modules have module-level docstrings explaining purpose and public API
- Classes have docstrings with signal documentation where applicable
- Not all methods have docstrings — kept for non-obvious logic only
- Style: imperative, concise (not NumPy/Google style)
## Data Modeling
- **Frozen dataclasses** for immutable data: `RobTarget`, `JointTarget`, `MoveInstruction`
- Custom `__eq__`/`__hash__` on dataclasses with `np.ndarray` fields
- **Enum with auto()** for `MoveType`
- **Non-frozen dataclass** for `ParseResult` (mutable accumulator)
- `dataclasses.replace()` used for immutable updates
## Import Patterns
- `from __future__ import annotations` in every module
- Explicit named imports (not `from module import *`)
- Lazy imports for heavy dependencies (OpenGL) to isolate test scoping
- Parser module has clean `__init__.py` re-exports
## Qt Patterns
- PyQt6 fully-qualified enums: `Qt.AlignmentFlag.AlignLeft` (not `Qt.AlignLeft`)
- `pyqtSignal` for observable state changes
- `QObject` parentage for memory management
- `blockSignals()` to prevent cascading during programmatic updates
- `QTextEdit.ExtraSelection` (not QPlainTextEdit variant)
## OpenGL Patterns
- Modern pipeline only: VBOs, VAOs, shader programs (no fixed-function)
- OpenGL 3.3 Core Profile target
- Interleaved vertex layout: `[x, y, z, r, g, b]` as float32, stride 24 bytes
- `_gl_ready` guard flag prevents GL calls before context initialization
- `_has_gl_context()` check for graceful headless test skipping
## Testing Patterns
- Tests organized by requirement ID (PARS-01, CAM-01, LINK-01, etc.)
- Shared fixtures in `conftest.py` loading `.mod` files
- `pytest-qt` `qtbot` for widget tests
- `OPENGL_AVAILABLE` flag for conditional GL test skipping
- Signal spy via `qtbot.waitSignal()` and `PlaybackState` observation
## Error Handling
- Minimal try/except — prefer letting exceptions propagate
- `QMessageBox` for user-facing file load errors
- No custom exception classes
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Strict unidirectional data flow: `.mod` file text -> `ParseResult` -> `GeometryBuffers` -> GPU VBOs
- Qt signals for bidirectional UI linking (3D viewport <-> code panel <-> playback state)
- No global state; `PlaybackState` is the single observable source of truth for current waypoint
- Parser layer has zero Qt dependency (pure Python + NumPy), enabling headless testing
- OpenGL 3.3 Core Profile with modern shader pipeline (VBO/VAO, no fixed-function)
## Layers
- Purpose: Read `.mod` files and extract structured robot program data
- Location: `src/rapid_viewer/parser/`
- Contains: Regex patterns, tokenizer, two-pass parser, frozen dataclass tokens
- Depends on: `numpy` (for coordinate arrays), `re` (stdlib)
- Used by: `MainWindow.load_file()` which calls `parse_module()`
- Purpose: Convert parsed data into GPU geometry and render via OpenGL
- Location: `src/rapid_viewer/renderer/`
- Contains: Geometry builder, GLSL shaders, arcball camera, QOpenGLWidget
- Depends on: Parser tokens (`ParseResult`, `MoveInstruction`), PyOpenGL, pyrr, PyQt6
- Used by: `MainWindow` embeds `ToolpathGLWidget`
- Purpose: Application window, code viewer, playback controls, signal wiring
- Location: `src/rapid_viewer/ui/`
- Contains: MainWindow, CodePanel, PlaybackToolbar, PlaybackState, RapidHighlighter
- Depends on: Parser (for `ParseResult`), Renderer (for `ToolpathGLWidget`), PyQt6
- Used by: `main.py` entry point
## Data Flow
- `PlaybackState` (`src/rapid_viewer/ui/playback_state.py`) is the single source of truth for current waypoint index
- Emits `current_changed(int)` signal consumed by:
- Emits `moves_changed()` consumed by `PlaybackToolbar._on_moves_changed()` -> updates scrubber range
## Key Abstractions
- Purpose: Complete output of parsing a `.mod` file -- the contract between parser and all consumers
- Definition: `src/rapid_viewer/parser/tokens.py` lines 106-121
- Pattern: Mutable dataclass (built incrementally by parser), then treated as read-only by consumers
- Contains: `module_name`, `moves: list[MoveInstruction]`, `targets: dict[str, RobTarget]`, `joint_targets`, `source_text`, `procedures`, `proc_ranges`, `errors`
- Purpose: GPU-ready vertex arrays, the contract between geometry builder and GL widget
- Definition: `src/rapid_viewer/renderer/geometry_builder.py` lines 24-38
- Pattern: Dataclass holding four NumPy arrays: `solid_verts`, `dashed_verts`, `marker_verts`, `triad_verts`
- Each array: shape `(N, 6)`, dtype `float32`, interleaved `[x, y, z, r, g, b]`
- Purpose: Interactive 3D camera with orbit/pan/zoom, produces view and projection matrices
- Definition: `src/rapid_viewer/renderer/camera.py`
- Pattern: Stateful object with quaternion-based rotation, consumed by `ToolpathGLWidget.paintGL()`
- Outputs: `mvp()` returns `float32` 4x4 matrix for shader upload
- Purpose: Observable model for current waypoint index, centralizes navigation logic
- Definition: `src/rapid_viewer/ui/playback_state.py`
- Pattern: QObject with Qt signals (`current_changed`, `moves_changed`), similar to a ViewModel
## Entry Points
- Location: `src/rapid_viewer/main.py`
- Triggers: `python -m rapid_viewer.main [file.mod]`
- Responsibilities: Set OpenGL 3.3 Core Profile surface format, create `QApplication`, create `MainWindow`, optional CLI file load, start event loop
- Location: `src/rapid_viewer/ui/main_window.py` -> `MainWindow.load_file(file_path)`
- Triggers: Menu action `Ctrl+O`, CLI argument, or programmatic call
- Responsibilities: Parse file, distribute result to GL widget, code panel, playback state, update title bar
- Location: `src/rapid_viewer/parser/rapid_parser.py` -> `parse_module(source)`
- Triggers: Called by `MainWindow.load_file()`
- Responsibilities: Tokenize, extract targets (Pass 1), extract moves (Pass 2), return `ParseResult`
## Error Handling
- Parser functions (`try_parse_robtarget_decl`, `try_parse_move`) return `None` on failure rather than raising -- malformed statements are silently skipped
- `ParseResult.errors` field exists for non-fatal warnings but is not currently populated
- `MainWindow.load_file()` wraps everything in `except Exception` and shows `QMessageBox.critical()`
- `read_mod_file()` falls back from UTF-8 to latin-1 encoding on `UnicodeDecodeError`
- `ToolpathGLWidget.update_scene()` guards against missing OpenGL context (defers upload to `initializeGL`)
- `tessellate_arc()` falls back to straight line for degenerate (collinear) 3-point arcs
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
