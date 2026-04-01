# Technical Concerns

> Generated: 2026-03-31

## No TODOs/FIXMEs Found

The codebase has zero TODO, FIXME, HACK, or XXX comments. All known issues are tracked in STATE.md decisions/blockers.

## Risk Areas

### 1. File Encoding Fragility
- **Location**: `parser/rapid_parser.py` — `read_mod_file()`
- **Risk**: Real-world .mod files often use Windows-1252 encoding. Current implementation may fail on non-UTF-8 files.
- **Noted in**: STATE.md blockers
- **Severity**: Medium — affects real-world usability

### 2. GL Context Dependency
- **Location**: `renderer/toolpath_gl_widget.py`
- **Risk**: The largest file (507 LOC) handles VBO/VAO management, picking, and triad rendering in a single widget class. All GL operations guarded by `_gl_ready` flag, but no fallback if OpenGL 3.3 Core Profile is unavailable on target machine.
- **Severity**: Low — Windows target machines typically have OpenGL 3.3+

### 3. No CI Pipeline
- **Risk**: Tests only run locally. GL-dependent tests (`test_viewer_widget.py`) need a display context and are skipped via `OPENGL_AVAILABLE` guard. No automated regression protection.
- **Severity**: Medium — acceptable for early-stage internal tool

### 4. Parser Regex Complexity
- **Location**: `parser/patterns.py` (133 LOC), `parser/rapid_parser.py` (502 LOC)
- **Risk**: Two-pass regex parser handles known RAPID syntax well, but novel/malformed .mod files could silently produce incomplete results. No validation that all expected targets were resolved.
- **Severity**: Low — tool is a viewer, not a safety-critical interpreter

### 5. Single-File Architecture for GL Widget
- **Location**: `renderer/toolpath_gl_widget.py` (507 LOC)
- **Risk**: Handles scene rendering, ray-cast picking, triad rendering, highlight management, and mouse interaction. Growing complexity could benefit from extraction (e.g., separate picking module).
- **Severity**: Low — manageable at current size

### 6. MoveAbsJ Gap
- **Location**: Parser stores MoveAbsJ with `has_cartesian=False` and `target=None`
- **Risk**: These moves are parsed but excluded from 3D rendering. If a .mod file uses only MoveAbsJ, the viewer shows nothing with no explanation to the user.
- **Severity**: Low — most real programs use Cartesian moves

## Performance Considerations

- **Regex compilation**: All 14 patterns compiled at module import time (good)
- **Vertex buffers**: Built as interleaved float32 arrays via NumPy (good)
- **No LOD or culling**: All geometry rendered every frame. Fine for typical toolpath sizes (hundreds to low thousands of points). Could become slow for very large programs (10k+ waypoints).

## Security

- **File input only**: No network operations, no external API calls
- **File dialog**: Uses Qt native dialog — no path injection risk
- **No user-supplied code execution**: Parser extracts data only
- **Low attack surface**: Internal tool reading trusted .mod files

## Dependency Risks

| Dependency | Risk | Notes |
|-----------|------|-------|
| PyQt6 | GPL license | Acceptable for internal tooling, not for commercial distribution |
| PyOpenGL-accelerate | Binary build | Must match PyOpenGL version exactly; pip install can fail without C compiler |
| pyrr | Unmaintained? | Last release 0.10.3 (2021), but stable API, pure Python |
