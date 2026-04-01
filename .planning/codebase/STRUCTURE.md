# Codebase Structure

> Generated: 2026-03-31

## Directory Layout

```
rapid-viewer/
├── pyproject.toml              # Project metadata, deps, tool config (hatchling build)
├── rapid_viewer.spec           # PyInstaller packaging spec
├── rapid_viewer.ico            # Application icon
├── build_icon.py               # Icon generation script
├── CLAUDE.md                   # Project instructions for AI assistants
│
├── src/rapid_viewer/           # Main application package
│   ├── __init__.py
│   ├── main.py                 # Entry point — QApplication + MainWindow launch (41 LOC)
│   │
│   ├── parser/                 # .mod file parsing (pure Python, no Qt dependency)
│   │   ├── __init__.py         # Re-exports: RobTarget, JointTarget, MoveInstruction, MoveType, ParseResult, parse_module, read_mod_file
│   │   ├── tokens.py           # Data model: frozen dataclasses + MoveType enum (120 LOC)
│   │   ├── patterns.py         # Compiled regex patterns for RAPID syntax (133 LOC)
│   │   └── rapid_parser.py     # Two-pass parser: declarations → move instructions (502 LOC)
│   │
│   ├── renderer/               # OpenGL 3.3 Core Profile rendering
│   │   ├── __init__.py         # Empty (renderer imported lazily)
│   │   ├── camera.py           # ArcballCamera: orbit/pan/zoom with quaternion math (172 LOC)
│   │   ├── geometry_builder.py # ParseResult → interleaved float32 vertex arrays (217 LOC)
│   │   ├── shaders.py          # GLSL shader source strings: SOLID, DASHED, AXES, TRIAD (132 LOC)
│   │   └── toolpath_gl_widget.py # QOpenGLWidget subclass: VBO/VAO, picking, triad rendering (507 LOC)
│   │
│   └── ui/                     # PyQt6 UI components
│       ├── __init__.py         # Empty
│       ├── main_window.py      # QMainWindow: splitter layout, menu, signal wiring (214 LOC)
│       ├── code_panel.py       # QTextEdit showing .mod source with line highlighting (90 LOC)
│       ├── playback_state.py   # Observable state for waypoint navigation (84 LOC)
│       ├── playback_toolbar.py # Step/play controls + speed slider (140 LOC)
│       └── rapid_highlighter.py # QSyntaxHighlighter for RAPID keywords (58 LOC)
│
├── tests/                      # pytest test suite
│   ├── __init__.py
│   ├── conftest.py             # Shared fixtures: .mod file loaders (48 LOC)
│   ├── fixtures/               # Sample .mod files for testing
│   │   ├── simple.mod
│   │   ├── multiline.mod
│   │   ├── movecircular.mod
│   │   ├── moveabsj.mod
│   │   ├── offs_inline.mod
│   │   └── multiproc.mod
│   ├── test_parser.py          # Parser unit tests by requirement ID (195 LOC)
│   ├── test_camera.py          # ArcballCamera tests (132 LOC)
│   ├── test_geometry_builder.py # Vertex buffer construction tests (180 LOC)
│   ├── test_viewer_widget.py   # GL widget smoke tests (123 LOC)
│   ├── test_code_panel.py      # CodePanel tests (100 LOC)
│   ├── test_playback_state.py  # PlaybackState signal tests (169 LOC)
│   ├── test_playback_toolbar.py # Toolbar button/slider tests (119 LOC)
│   ├── test_rapid_highlighter.py # Syntax highlighter tests (129 LOC)
│   ├── test_main_window.py     # MainWindow integration tests (109 LOC)
│   └── test_linking.py         # Bidirectional 3D↔code linking tests (205 LOC)
│
└── .planning/                  # GSD planning artifacts (not shipped)
    ├── STATE.md
    ├── PROJECT.md
    ├── ROADMAP.md
    └── phases/                 # Per-phase plans, summaries, verification
```

## Module Boundaries

| Module | Depends On | Depended By | Boundary Rule |
|--------|-----------|-------------|---------------|
| `parser/` | numpy only | renderer, ui | Pure Python, no Qt imports. Clean public API via `__init__.py` |
| `renderer/` | parser.tokens, numpy, PyOpenGL, pyrr | ui.main_window | Lazily imported to isolate OpenGL from parser tests |
| `ui/` | parser, renderer, PyQt6 | main.py | Top-level integration. renderer imported lazily in MainWindow |

## Key Sizes

| Component | Files | Total LOC |
|-----------|-------|-----------|
| Parser | 4 | ~767 |
| Renderer | 5 | ~1,028 |
| UI | 6 | ~586 |
| Tests | 11 | ~1,509 |
| **Total** | **26** | **~4,151** |

## Where to Add New Code

- **New RAPID syntax support**: `parser/patterns.py` (regex) + `parser/rapid_parser.py` (handler)
- **New rendering features**: `renderer/toolpath_gl_widget.py` or new file in `renderer/`
- **New UI panels/dialogs**: New file in `ui/`, wire in `main_window.py`
- **New shaders**: `renderer/shaders.py` (string constants)
- **New test fixtures**: `tests/fixtures/*.mod` + fixture function in `tests/conftest.py`
