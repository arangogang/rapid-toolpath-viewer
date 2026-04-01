---
plan: 04-03
phase: 04-edit-infrastructure-selection-and-inspection
status: checkpoint
started: 2026-04-01T09:00:00Z
completed: 2026-04-01T09:30:00Z
duration_seconds: 1800
tasks_completed: 2
tasks_total: 3
---

# Plan 04-03 Summary: MainWindow Integration

## What Was Built

Integrated all Phase 4 components into a working application:

1. **GL widget multi-select rendering** — waypoint_picked signal with Shift/Ctrl modifier flags, cyan-colored selected markers VBO, magenta current-when-selected marker
2. **MainWindow full integration** — EditModel, SelectionState, PropertyPanel wired with signal connections; Edit menu with Undo/Redo; dirty title bar; vertical right-pane splitter

## Key Decisions

- waypoint_clicked(int) replaced with waypoint_picked(int, bool, bool) for modifier awareness
- Selection routing: shift/ctrl → toggle, plain click → select_single
- PropertyPanel updates on both selection_changed and current_changed signals
- PROC filter change clears selection state

## Self-Check: PENDING

Task 3 (human visual verification) awaiting user approval.

## Commits

- `637340f` feat(04-03): add multi-select rendering and modifier-aware pick signal to GL widget
- `ba9e6a7` feat(04-03): integrate EditModel, SelectionState, PropertyPanel into MainWindow

## key-files

### created
(none — modified existing files)

### modified
- src/rapid_viewer/renderer/toolpath_gl_widget.py — waypoint_picked signal, set_selected_indices, _draw_selected, modifier detection
- src/rapid_viewer/ui/main_window.py — EditModel + SelectionState + PropertyPanel wiring, Edit menu, dirty title

## Test Results

All 110 tests pass (including 6 MainWindow tests, 30 Phase 4 model tests).
