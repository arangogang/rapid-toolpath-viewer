---
phase: 04-edit-infrastructure-selection-and-inspection
plan: 01
subsystem: ui
tags: [pyqt6, qundostack, dataclass, selection, edit-model]

# Dependency graph
requires:
  - phase: 01-rapid-parser-and-file-load
    provides: "MoveInstruction and RobTarget frozen dataclasses"
provides:
  - "EditPoint mutable dataclass wrapping MoveInstruction"
  - "EditModel QObject with QUndoStack for undo/redo"
  - "SelectionState QObject for multi-select waypoint management"
affects: [04-02-property-panel, 04-03-mainwindow-integration, 05-modifications]

# Tech tracking
tech-stack:
  added: [QUndoStack]
  patterns: [mutable-wrapper-over-frozen-dataclass, observable-selection-set]

key-files:
  created:
    - src/rapid_viewer/ui/edit_model.py
    - src/rapid_viewer/ui/selection_state.py
    - tests/test_edit_model.py
    - tests/test_selection_state.py
  modified: []

key-decisions:
  - "QUndoStack imported from PyQt6.QtGui (not QtWidgets) per PyQt6 API"
  - "selection_changed uses pyqtSignal(object) because PyQt6 does not support frozenset as signal type"
  - "EditPoint.from_move for MoveAbsJ (target=None) defaults pos to np.zeros(3)"
  - "extend_to delegates to toggle (Ctrl+click behavior per D-02)"

patterns-established:
  - "Mutable wrapper pattern: EditPoint wraps frozen MoveInstruction with .original reference"
  - "Observable set pattern: SelectionState emits frozenset on every mutation"

requirements-completed: [EDIT-01, EDIT-02, SEL-01, SEL-02]

# Metrics
duration: 2min
completed: 2026-04-01
---

# Phase 4 Plan 01: EditModel and SelectionState Summary

**EditModel with QUndoStack wrapping MoveInstruction into mutable EditPoints, and SelectionState with observable multi-select set -- 20 tests passing**

## Performance

- **Duration:** 2 min 23 sec
- **Started:** 2026-04-01T08:37:36Z
- **Completed:** 2026-04-01T08:39:59Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- SelectionState QObject with select_single/toggle/extend_to/clear and selection_changed signal
- EditPoint mutable dataclass with from_move classmethod wrapping frozen MoveInstruction
- EditModel QObject owning QUndoStack with load/point_at/point_count/is_dirty and dirty_changed/model_reset signals
- Full TDD: 20 unit tests (8 SelectionState + 12 EditModel) all passing with no GL/widget dependency

## Task Commits

Each task was committed atomically:

1. **Task 1: SelectionState model with tests** - `f3c2f83` (feat)
2. **Task 2: EditModel and EditPoint with tests** - `e0c144b` (feat)

_Both tasks followed TDD: RED (import error) -> GREEN (all pass)_

## Files Created/Modified
- `src/rapid_viewer/ui/selection_state.py` - SelectionState QObject with multi-select management
- `src/rapid_viewer/ui/edit_model.py` - EditPoint dataclass + EditModel QObject with QUndoStack
- `tests/test_selection_state.py` - 8 tests for SEL-01, SEL-02
- `tests/test_edit_model.py` - 12 tests for EDIT-01, EDIT-02

## Decisions Made
- QUndoStack imported from PyQt6.QtGui (not QtWidgets) per PyQt6 6.10 API
- selection_changed uses pyqtSignal(object) because PyQt6 does not support frozenset as a signal type
- EditPoint.from_move for MoveAbsJ (target=None) defaults pos to np.zeros(3, dtype=np.float64)
- extend_to delegates to toggle (same as Ctrl+click per design decision D-02)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- EditModel and SelectionState ready for PropertyPanel (Plan 02) and MainWindow integration (Plan 03)
- QUndoStack is wired and tested, ready for Phase 5 mutation commands to push onto it
- No blockers

## Self-Check: PASSED

All 4 files verified present. Both task commits (f3c2f83, e0c144b) verified in git log.

---
*Phase: 04-edit-infrastructure-selection-and-inspection*
*Completed: 2026-04-01*
