---
phase: 03-playback-code-panel-and-linking
plan: 03
subsystem: ui, renderer
tags: [pyqt6, qtoolbar, qtimer, opengl, ray-cast, quaternion, pyrr, tcp-triad]

# Dependency graph
requires:
  - phase: 03-01
    provides: PlaybackState model with current_changed/moves_changed signals
provides:
  - PlaybackToolbar widget with step/play/speed/scrubber controls
  - GL widget highlight marker at current waypoint (14px white point)
  - Ray-cast picking via waypoint_clicked signal (20px screen-space threshold)
  - TCP orientation triads (RGB axis lines from ABB quaternions)
  - build_triad_vertices() geometry builder function
affects: [03-04, 03-05, main-window-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [QTimer-based auto-play with speed slider, screen-space ray-cast picking, ABB-to-pyrr quaternion conversion]

key-files:
  created:
    - src/rapid_viewer/ui/playback_toolbar.py
    - tests/test_playback_toolbar.py
  modified:
    - src/rapid_viewer/renderer/toolpath_gl_widget.py
    - src/rapid_viewer/renderer/shaders.py
    - src/rapid_viewer/renderer/geometry_builder.py

key-decisions:
  - "Speed slider maps integer 5-100 to 0.5x-10.0x with formula int(500 / (value / 10.0))"
  - "Ray-cast picking projects all waypoints to screen space via MVP matrix, Y-flip for Qt coordinate system"
  - "TCP triads reuse SOLID shader (identity alias TRIAD_VERT/TRIAD_FRAG) with per-vertex RGB color"
  - "ABB quaternion [w,x,y,z] converted to pyrr [x,y,z,w] with normalization guard"

patterns-established:
  - "Scrubber signal-blocking pattern: _blocking_scrubber flag prevents valueChanged->set_index->current_changed->setValue loop"
  - "Click-vs-drag detection: track press position, check <3px distance on release before attempting pick"

requirements-completed: [PLAY-04, PLAY-05, PLAY-06, PLAY-07, REND-04, LINK-01]

# Metrics
duration: 638s
completed: 2026-03-30
---

# Phase 03 Plan 03: Playback Toolbar and GL Widget Enhancements Summary

**PlaybackToolbar with step/play/speed/scrubber controls, plus GL widget highlight marker, ray-cast picking, and TCP orientation triads**

## Performance

- **Duration:** 638s (~10 min)
- **Started:** 2026-03-30T10:14:26Z
- **Completed:** 2026-03-30T10:25:04Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- PlaybackToolbar with step back/forward, play/pause toggle, speed slider (0.5x-10x), scrubber, and position label all connected to PlaybackState
- GL widget renders 14px white highlight point at current waypoint via set_highlight_index()
- Ray-cast picking projects waypoints to screen coordinates and emits waypoint_clicked(int) on click within 20px
- TCP orientation triads render as RGB axis lines at each Cartesian waypoint using ABB quaternion rotation

## Task Commits

Each task was committed atomically:

1. **Task 1: Playback toolbar widget (RED)** - `1333a40` (test)
2. **Task 1: Playback toolbar widget (GREEN)** - `c8721ff` (feat)
3. **Task 2: GL widget highlight/picking/triads** - `ff8cefe` (feat)

## Files Created/Modified
- `src/rapid_viewer/ui/playback_toolbar.py` - PlaybackToolbar QToolBar with step/play/speed/scrubber/label controls
- `tests/test_playback_toolbar.py` - 7 tests covering position label, speed mapping, scrubber range, play/pause toggle
- `src/rapid_viewer/renderer/toolpath_gl_widget.py` - Added highlight marker, ray-cast picking, TCP triads, waypoint_clicked signal
- `src/rapid_viewer/renderer/shaders.py` - Added TRIAD_VERT/TRIAD_FRAG aliases
- `src/rapid_viewer/renderer/geometry_builder.py` - Added triad_verts field to GeometryBuffers, build_triad_vertices() function

## Decisions Made
- Speed slider uses integer range 5-100 (representing 0.5x-10.0x) to avoid float slider complexity; interval formula: int(500 / (value / 10.0))
- Ray-cast picking uses screen-space projection rather than color-based FBO picking -- simpler, sufficient for point-cloud data
- TCP triads reuse solid line shader via identity aliases (same pattern as AXES_VERT/AXES_FRAG)
- ABB quaternion [w,x,y,z] to pyrr [x,y,z,w] conversion with normalization guard for robustness

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functionality is fully wired.

## Next Phase Readiness
- PlaybackToolbar ready for MainWindow integration (Plan 04/05)
- GL widget waypoint_clicked signal ready to connect to PlaybackState.set_index for bidirectional linking
- set_highlight_index() ready to connect to PlaybackState.current_changed for visual feedback

---
*Phase: 03-playback-code-panel-and-linking*
*Completed: 2026-03-30*
