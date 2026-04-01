# Testing Strategy

> Generated: 2026-03-31

## Infrastructure

| Tool | Config Location | Notes |
|------|----------------|-------|
| pytest | `pyproject.toml [tool.pytest.ini_options]` | testpaths=["tests"], pythonpath=["src"] |
| pytest-qt | dev dependency | Widget testing with `qtbot` fixture |
| PyInstaller | dev dependency | Not testing-related, bundled in dev deps |

## Test Layout

```
tests/
├── conftest.py              # Shared fixtures (6 .mod file loaders)
├── fixtures/                # 6 sample .mod files covering all move types
├── test_parser.py           # Parser: PARS-01 through PARS-07
├── test_camera.py           # Camera: CAM-01 through CAM-03
├── test_geometry_builder.py # Geometry: vertex buffer construction
├── test_viewer_widget.py    # GL widget: smoke tests (needs OpenGL context)
├── test_code_panel.py       # CodePanel: text loading, highlighting
├── test_playback_state.py   # PlaybackState: signal emission, bounds
├── test_playback_toolbar.py # Toolbar: button clicks, speed slider
├── test_rapid_highlighter.py # Syntax: keyword highlighting
├── test_main_window.py      # MainWindow: menu, layout, file loading
└── test_linking.py          # Integration: 3D↔code bidirectional linking
```

## Test Categories

### Unit Tests (no GUI, no OpenGL)
- `test_parser.py` — Pure data: parse .mod strings, assert on RobTarget/MoveInstruction values
- `test_geometry_builder.py` — Pure data: ParseResult → vertex arrays, assert on shapes/values
- `test_camera.py` — Pure math: ArcballCamera matrix generation, orbit/pan/zoom

### Widget Tests (need Qt event loop via qtbot)
- `test_code_panel.py` — CodePanel text operations
- `test_playback_state.py` — Signal emission on state changes
- `test_playback_toolbar.py` — Button/slider interaction
- `test_rapid_highlighter.py` — Syntax highlighting rules
- `test_main_window.py` — Menu actions, layout verification

### GL Tests (need OpenGL context)
- `test_viewer_widget.py` — Guarded by `OPENGL_AVAILABLE` flag; skip on headless CI

### Integration Tests
- `test_linking.py` — End-to-end signal chain: PlaybackState ↔ CodePanel ↔ GL widget

## Fixture Strategy

- **conftest.py** defines `fixtures_dir` and 6 named fixtures (`simple_mod`, `multiline_mod`, etc.)
- Each fixture reads a `.mod` file from `tests/fixtures/` and returns the string content
- Tests call `parse_module()` on fixture content to get `ParseResult`

## Requirement Traceability

Tests reference requirement IDs in docstrings:
- `PARS-01` through `PARS-07` — Parser requirements
- `CAM-01` through `CAM-03` — Camera requirements
- `LINK-01`, `LINK-02` — Bidirectional linking
- `PARS-08` — PROC selector filtering

## Running Tests

```bash
uv run pytest              # All tests
uv run pytest tests/test_parser.py  # Single module
uv run pytest -k "movel"   # By keyword
```

## Coverage Observations

- **Well covered**: Parser (all move types + edge cases), Camera (all interactions), PlaybackState, linking signals
- **Smoke-level only**: GL widget (instantiation + update_scene, no visual assertions)
- **Not covered**: PyInstaller packaging, main.py entry point, file encoding edge cases
- **No CI configured**: Tests run locally only; GL tests need display context
