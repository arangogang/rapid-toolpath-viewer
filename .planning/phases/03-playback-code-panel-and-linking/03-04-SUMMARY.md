---
phase: 03-playback-code-panel-and-linking
plan: 04
subsystem: ui
tags: [pyqt6, qsplitter, signal-wiring, bidirectional-linking, proc-selector]

# Dependency graph
requires:
  - phase: 03-01
    provides: PlaybackState model with current_changed/moves_changed signals
  - phase: 03-02
    provides: CodePanel with line_clicked signal and highlight_line method
  - phase: 03-03
    provides: PlaybackToolbar, GL widget waypoint_clicked signal, set_highlight_index
provides:
  - QSplitter layout with GL widget (60%) and CodePanel (40%)
  - Bidirectional 3D-to-code and code-to-3D linking via PlaybackState
  - PROC selector QComboBox for filtering moves by procedure
  - Complete signal wiring for step-through navigation
affects: [03-05-verification, phase-04]

# Tech tracking
tech-stack:
  added: []
  patterns: [qsplitter-layout, signal-wiring, proc-filtering, gl-context-guard]

key-files:
  created:
    - tests/test_linking.py
  modified:
    - src/rapid_viewer/ui/main_window.py
    - tests/test_main_window.py

key-decisions:
  - "GL context guard (_gl_ready) prevents makeCurrent() hang when widget not yet shown -- essential for headless test execution"
  - "blockSignals on PROC combo during load_file prevents spurious filter triggers during combo population"
  - "dataclasses.replace() creates filtered ParseResult copy for GL scene update on PROC filter change"

patterns-established:
  - "GL context guard: check context().isValid() before calling makeCurrent/update_scene in MainWindow"
  - "Signal wiring centralized in _wire_signals() for clarity"

requirements-completed: [LINK-01, LINK-02, PARS-08, CODE-01, CODE-03]

# Metrics
duration: 639s
completed: 2026-03-30
---

# Phase 03 Plan 04: MainWindow Integration & Bidirectional Linking Summary

**QSplitter layout with bidirectional 3D-to-code linking, PROC selector filtering, and PlaybackState signal wiring in MainWindow**

## Performance

- **Duration:** 639s (~11 min)
- **Started:** 2026-03-30T10:27:45Z
- **Completed:** 2026-03-30T10:38:24Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- MainWindow restructured with QSplitter: GL widget (60%) left, CodePanel (40%) right
- Bidirectional linking: 3D waypoint click scrolls code panel to source line; code panel click selects waypoint in 3D
- PROC selector QComboBox filters moves by procedure and rebuilds GL geometry
- 5 integration tests verify signal chain without requiring GL context

## Task Commits

Each task was committed atomically:

1. **Task 1: MainWindow QSplitter layout and PlaybackState wiring** - `8cff3b0` (feat)
2. **Task 2: Bidirectional linking integration tests** - `756cac6` (test)

## Files Created/Modified
- `src/rapid_viewer/ui/main_window.py` - QSplitter layout, PlaybackState wiring, PROC selector, bidirectional linking slots, GL context guard
- `tests/test_main_window.py` - Updated tests for splitter layout, code panel population, PROC combo population
- `tests/test_linking.py` - Integration tests for LINK-01, LINK-02, PARS-08 signal chains

## Decisions Made
- Added `_gl_ready()` guard to prevent `makeCurrent()` from hanging when GL widget has no valid context (test environments where widget is not shown)
- Used `blockSignals(True)` on PROC combo during `load_file()` to prevent spurious `currentTextChanged` signals while populating the combo box
- Used `dataclasses.replace()` to create filtered ParseResult copies for PROC-filtered GL scene updates

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added GL context guard to prevent makeCurrent() hang**
- **Found during:** Task 1 (MainWindow wiring)
- **Issue:** `update_scene()` and `set_highlight_index()` call `makeCurrent()` which hangs indefinitely when widget has no valid GL context (not shown, test environment)
- **Fix:** Added `_gl_ready()` method checking `context().isValid()` before all GL calls in MainWindow
- **Files modified:** src/rapid_viewer/ui/main_window.py
- **Verification:** All 80 tests pass including load_file tests that previously hung
- **Committed in:** 8cff3b0

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Essential for test execution. No scope creep.

## Issues Encountered
None beyond the GL context hang addressed above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all data paths are fully wired.

## Next Phase Readiness
- All Phase 3 components (PlaybackState, CodePanel, PlaybackToolbar, GL enhancements, MainWindow integration) are wired together
- Ready for Phase 3 final verification (03-05)
- Full test suite: 80 tests, all passing

---
*Phase: 03-playback-code-panel-and-linking*
*Completed: 2026-03-30*
