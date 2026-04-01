# Code Conventions

> Generated: 2026-03-31

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
