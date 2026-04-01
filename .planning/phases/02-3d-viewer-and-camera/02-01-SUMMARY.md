---
phase: 02-3d-viewer-and-camera
plan: 01
subsystem: renderer
tags: [geometry, shaders, opengl, vertex-buffers]
dependency_graph:
  requires: [parser/tokens.py]
  provides: [renderer/geometry_builder.py, renderer/shaders.py]
  affects: [02-03 GL widget, 02-04 camera]
tech_stack:
  added: [PyOpenGL>=3.1.10, PyOpenGL-accelerate>=3.1.10, pyrr>=0.10.3]
  patterns: [interleaved-vertex-layout, CPU-side-geometry-build, GLSL-as-python-constants]
key_files:
  created:
    - src/rapid_viewer/renderer/__init__.py
    - src/rapid_viewer/renderer/geometry_builder.py
    - src/rapid_viewer/renderer/shaders.py
    - tests/test_geometry_builder.py
  modified:
    - pyproject.toml
decisions:
  - "Interleaved [x,y,z,r,g,b] float32 vertex layout (stride 24 bytes) for all geometry types"
  - "Color palette: MoveL=green, MoveJ=orange, MoveC=blue, markers=yellow"
  - "AXES shaders are aliases to SOLID shaders (same code, different MVP at draw time)"
metrics:
  duration_seconds: 138
  completed: "2026-03-30T09:06:42Z"
  tasks_completed: 2
  tasks_total: 2
  tests_passed: 8
  tests_total: 8
  files_created: 4
  files_modified: 1
---

# Phase 02 Plan 01: Geometry Builder and Shader Source Library Summary

Geometry conversion pipeline (ParseResult to GPU-ready float32 vertex arrays) and 8 GLSL shader strings as Python constants targeting OpenGL 3.3 Core Profile.

## What Was Built

### geometry_builder.py
- `GeometryBuffers` dataclass: three float32 numpy arrays (solid_verts, dashed_verts, marker_verts), all shape (N, 6) with interleaved [x, y, z, r, g, b]
- `build_geometry()`: iterates ParseResult.moves, converts MoveL to solid segments, MoveJ to dashed segments, MoveC to arc-tessellated solid polylines, markers at every Cartesian waypoint
- `tessellate_arc()`: 3-point circular arc tessellation with collinear fallback to straight line
- MoveAbsJ (has_cartesian=False) silently skipped -- no geometry produced
- Helper functions `_add_segment()` and `_add_polyline()` for GL_LINES vertex pair construction

### shaders.py
- 8 exported constants: SOLID_VERT, SOLID_FRAG, DASHED_VERT, DASHED_FRAG, MARKER_VERT, MARKER_FRAG, AXES_VERT, AXES_FRAG
- All target `#version 330 core` (OpenGL 3.3 Core Profile)
- Dashed shader uses `flat` qualifier on vStartPos for correct NDC-space dash calculation
- Marker shader uses `gl_PointCoord` circular discard for round point sprites
- AXES_VERT/AXES_FRAG are identity aliases to SOLID pair (not copies)

### Dependencies
- Added to pyproject.toml: PyOpenGL>=3.1.10, PyOpenGL-accelerate>=3.1.10, pyrr>=0.10.3

## Test Results

8/8 tests passing:
1. test_empty_parse_result -- empty moves returns (0,6) arrays
2. test_movel_produces_solid_segment -- MoveL generates solid GL_LINES vertices
3. test_movej_produces_dashed_segment -- MoveJ generates dashed GL_LINES vertices
4. test_moveabsj_skipped -- MoveAbsJ produces zero geometry
5. test_movec_tessellates_arc -- MoveC arc tessellation produces >= 32 solid vertices
6. test_arc_collinear_fallback -- collinear arc degrades to straight line (17 points)
7. test_vertex_layout_dtype -- all arrays float32 with shape (N, 6)
8. test_marker_at_every_cartesian_waypoint -- 3 MoveL = 3 marker rows

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all functions are fully implemented with real logic.

## Decisions Made

1. **Interleaved vertex layout**: [x,y,z,r,g,b] float32, stride 24 bytes. Chosen for simplicity and single-VBO-per-draw-type efficiency.
2. **Color palette**: MoveL=green(0.2,0.8,0.2), MoveJ=orange(0.8,0.5,0.1), MoveC=blue(0.2,0.6,1.0), markers=yellow(1.0,1.0,0.3). Visually distinct on dark background.
3. **AXES shader aliasing**: AXES_VERT/AXES_FRAG are `is` aliases to SOLID pair, not string copies. Downstream code passes different MVP uniform to draw the axes triad.

## Self-Check: PASSED

All 6 files verified present on disk. 8/8 tests green. All shader imports verified.
