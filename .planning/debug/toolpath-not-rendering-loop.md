---
status: awaiting_human_verify
trigger: "Toolpath viewer runs but toolpath is never drawn — app keeps resetting to initial state in a loop"
created: 2026-03-30T00:00:00Z
updated: 2026-03-30T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED -- MVP matrix multiplication order is reversed in camera.py
test: Project scene center point through corrected MVP and verify NDC within [-1, 1]
expecting: NDC (0, 0) for scene center
next_action: Await human verification that toolpath is now visible

## Symptoms

expected: After loading a .mod file, the toolpath should be rendered in the 3D OpenGL viewport
actual: Toolpath is not drawn at all; the app repeatedly resets back to its initial/empty state in a loop
errors: No error messages (silent rendering failure -- geometry uploaded but projected off-screen)
reproduction: Run dist/rapid_viewer.exe -> load a .mod file -> toolpath never appears
started: From initial implementation -- the MVP order was always wrong

## Eliminated

- hypothesis: Signal loop between PlaybackState/CodePanel/MainWindow causes infinite reset
  evidence: Instrumented _on_waypoint_changed -- called exactly once per file load, set_index guard prevents re-entry
  timestamp: 2026-03-30

- hypothesis: OpenGL hidden imports missing from PyInstaller spec causing silent crash
  evidence: EXE worked even without OpenGL hidden imports (PyInstaller auto-detected them). Added them anyway for robustness.
  timestamp: 2026-03-30

- hypothesis: initializeGL called multiple times (context loss) causing VBO data loss
  evidence: Instrumented initializeGL with counter -- called exactly once
  timestamp: 2026-03-30

- hypothesis: _gl_ready() returns False during load_file, so update_scene never called
  evidence: Debug output shows update_scene IS called and geometry IS uploaded (solid=4, markers=3)
  timestamp: 2026-03-30

- hypothesis: Parser returns empty moves for the test .mod files
  evidence: Parser correctly returns 3 moves for simple.mod with valid positions
  timestamp: 2026-03-30

## Evidence

- timestamp: 2026-03-30
  checked: Parser output for simple.mod
  found: 3 moves parsed correctly with valid positions (500,0,400), (600,100,400), (700,200,400)
  implication: Parser is not the problem

- timestamp: 2026-03-30
  checked: Geometry builder output
  found: solid_verts=(4,6), marker_verts=(3,6) -- correct geometry generated
  implication: Geometry pipeline is not the problem

- timestamp: 2026-03-30
  checked: EXE with debug prints -- geometry upload
  found: update_scene called with 3 moves, solid=4, markers=3 after paint
  implication: GPU geometry is uploaded correctly, problem is in rendering/projection

- timestamp: 2026-03-30
  checked: pyrr matrix convention
  found: pyrr uses row-vector convention: result = point @ matrix. pt @ view gives correct eye-space coords.
  implication: Combined MVP must be view @ proj (not proj @ view) for pyrr convention

- timestamp: 2026-03-30
  checked: MVP projection of scene center with WRONG order (proj @ view)
  found: Center point (600,100,400) projects to NDC (-603, -100) -- FAR outside clip range [-1,1]
  implication: ALL geometry is clipped. Nothing visible. This is the root cause.

- timestamp: 2026-03-30
  checked: MVP projection of scene center with CORRECT order (view @ proj)
  found: Center point projects to NDC (0, 0) -- perfectly centered. All test points within [-1,1].
  implication: Fix confirmed. Toolpath will now be visible.

## Resolution

root_cause: MVP matrix multiplication order is reversed in camera.py and toolpath_gl_widget.py. The code computed `projection @ view` but pyrr's row-vector convention requires `view @ projection`. With the wrong order, all geometry projects to extreme NDC coordinates (e.g., -603 instead of 0) and is clipped by the GPU -- nothing is ever visible. The same error affected the axes indicator overlay (ortho @ rot instead of rot @ ortho).
fix: Reversed multiplication order in two places: (1) camera.py mvp() method: changed `projection @ view` to `view @ projection`. (2) toolpath_gl_widget.py _draw_axes_indicator(): changed `ortho @ rot_only` to `rot_only @ ortho`. Also enabled OpenGL hidden imports in the PyInstaller spec for build robustness.
verification: All 80 tests pass. Scene center projects to NDC (0,0). All test fixture waypoints project within visible [-1,1] NDC range.
files_changed:
  - src/rapid_viewer/renderer/camera.py
  - src/rapid_viewer/renderer/toolpath_gl_widget.py
  - rapid_viewer.spec
