---
phase: 05-modification-operations
plan: 03
subsystem: ui
tags: [pyqt6, signals, geometry-rebuild, undo-redo, integration]

requires:
  - phase: 05-01
    provides: EditModel mutation methods and QUndoCommand subclasses
  - phase: 05-02
    provides: PropertyPanel editable signals (offset, speed, zone, laser, delete, insert)
provides:
  - Complete end-to-end modification workflow wired through MainWindow
  - Geometry rebuild from EditModel state after every mutation
  - Selection auto-update after insert/delete operations
affects: [export, phase-06]

tech-stack:
  added: []
  patterns: [synthetic-parse-result for geometry rebuild, signal-handler-mutation pattern]

key-files:
  created: []
  modified:
    - src/rapid_viewer/ui/main_window.py

key-decisions:
  - "Geometry rebuild uses synthetic ParseResult via dataclasses.replace(result, moves=edited_moves)"
  - "PROC filter updated to use EditModel edited moves as canonical source"
  - "Insert auto-selects new point for chaining; delete clears selection"

patterns-established:
  - "Signal wiring: PropertyPanel -> MainWindow handler -> EditModel mutation -> points_changed -> geometry rebuild"
  - "Synthetic ParseResult pattern: replace(parse_result, moves=edited_moves) for GL widget update"

requirements-completed: [MOD-01, MOD-02, MOD-03, MOD-04]

duration: 3min
completed: 2026-04-02
---

# Plan 05-03: MainWindow Wiring + Geometry Rebuild Summary

**End-to-end modification workflow: PropertyPanel signals wired through MainWindow to EditModel mutations with immediate 3D geometry rebuild and undo/redo**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-02T04:40:00Z
- **Completed:** 2026-04-02T04:43:00Z
- **Tasks:** 2 (1 auto + 1 visual checkpoint)
- **Files modified:** 1

## Accomplishments
- 6 PropertyPanel edit signals connected to MainWindow handlers routing to EditModel mutations
- Geometry rebuilds from EditModel state after every mutation via synthetic ParseResult
- PROC filter uses edited moves as canonical source
- Selection auto-updates: insert selects new point, delete clears selection
- Visual verification passed: offset, property edit, delete (reconnect/break), insert, undo/redo all confirmed

## Task Commits

1. **Task 1: Wire PropertyPanel signals to EditModel and rebuild geometry** - `b786383` (feat)
2. **Task 2: Visual verification** - Human-approved checkpoint

## Files Created/Modified
- `src/rapid_viewer/ui/main_window.py` - 6 signal connections + 7 handler methods + geometry rebuild via points_changed

## Decisions Made
- Synthetic ParseResult via `dataclasses.replace(result, moves=edited_moves)` avoids modifying the original parse result
- PROC filter reads from EditModel to reflect edits when switching procedures
- Insert auto-selects the new point for continuous chaining per D-10

## Deviations from Plan
None - plan executed as specified

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All modification operations functional with undo/redo
- Ready for Phase 6 (Export) which needs `build_edited_moves()` to generate patched .mod output

---
*Phase: 05-modification-operations*
*Completed: 2026-04-02*
