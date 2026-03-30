---
phase: 01-parser-and-file-loading
plan: 03
subsystem: ui
tags: [pyqt6, qmainwindow, qfiledialog, file-loading, opengl-shell]

# Dependency graph
requires:
  - phase: 01-parser-and-file-loading (plan 02)
    provides: parse_module(), read_mod_file(), ParseResult dataclass from rapid_parser.py

provides:
  - PyQt6 MainWindow with File > Open dialog (Ctrl+O) and .mod file filter
  - Application entry point (main.py) with QApplication lifecycle and CLI file argument support
  - Title bar update to show loaded filename (FILE-02)
  - ParseResult stored internally on MainWindow for Phase 2 renderer consumption

affects: [phase-02-3d-viewer, phase-03-playback-linking]

# Tech tracking
tech-stack:
  added: [PyQt6.QtWidgets.QMainWindow, PyQt6.QtWidgets.QFileDialog, PyQt6.QtWidgets.QMessageBox, PyQt6.QtGui.QAction, pytest-qt]
  patterns: [QMainWindow subclass with menuBar setup, lazy parser import inside load_file(), load_file() as public method for testability]

key-files:
  created:
    - src/rapid_viewer/main.py
    - src/rapid_viewer/ui/main_window.py
    - tests/test_main_window.py
  modified: []

key-decisions:
  - "load_file() is a public method (not prefixed with _) to allow direct invocation in tests without triggering QFileDialog"
  - "Parser imported lazily inside load_file() to avoid import-time errors if rapid_parser has issues"
  - "CLI argument support added to main.py: if sys.argv[1] exists, load_file() is called immediately after show()"
  - "Encoding fallback (UTF-8 -> latin-1) delegated entirely to read_mod_file() in rapid_parser.py -- MainWindow has no encoding logic"

patterns-established:
  - "Pattern 1: QMainWindow._setup_menu() separates menu construction from __init__ for clarity"
  - "Pattern 2: parse_result property exposes private _parse_result for read-only downstream access"
  - "Pattern 3: tests/test_main_window.py uses qtbot.addWidget() for proper Qt widget lifecycle in pytest-qt"

requirements-completed: [FILE-01, FILE-02]

# Metrics
duration: ~20min
completed: 2026-03-30
---

# Phase 01 Plan 03: PyQt6 MainWindow with File Dialog Summary

**PyQt6 MainWindow shell with File > Open dialog (.mod filter, Ctrl+O shortcut) and title bar update -- Phase 1 complete, ParseResult ready for renderer**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-03-30
- **Completed:** 2026-03-30
- **Tasks:** 1 auto task + 1 human-verify checkpoint (approved)
- **Files modified:** 3

## Accomplishments

- MainWindow with "ABB RAPID Toolpath Viewer" title launches cleanly via `python -m rapid_viewer.main`
- File > Open (Ctrl+O) opens native QFileDialog filtered to "RAPID Module (*.mod)"
- After loading a .mod file, title bar updates to "ABB RAPID Toolpath Viewer - {filename}"
- ParseResult stored on MainWindow instance, accessible via `.parse_result` property for Phase 2 renderer
- Three window tests pass green (title update, parse result stored, minimum size)
- Human verification confirmed: file dialog and title bar update work end-to-end

## Task Commits

Each task was committed atomically:

1. **Task 1: Create MainWindow with file dialog and application entry point** - `a49d6dd` (feat)

**Plan metadata:** (docs commit to follow with SUMMARY + STATE updates)

## Files Created/Modified

- `src/rapid_viewer/main.py` - Application entry point: QApplication setup, MainWindow instantiation, CLI file argument support
- `src/rapid_viewer/ui/main_window.py` - MainWindow class: File menu, QFileDialog, load_file(), parse_result property
- `tests/test_main_window.py` - 3 pytest-qt tests: title update, parse result stored, minimum window size

## Decisions Made

- `load_file()` is public to enable direct test invocation without triggering QFileDialog interactive mode
- Parser import is lazy (inside `load_file()`) to keep import errors surfaced at load time rather than app startup
- Encoding fallback fully delegated to `read_mod_file()` in rapid_parser.py — UI layer stays clean

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 1 complete. All three plans (01-01, 01-02, 01-03) are done:
- Data model contracts and regex patterns established (01-01)
- Full RAPID parser with 11 TDD tests green (01-02)
- PyQt6 application shell with file loading UI (01-03)

Phase 2 (3D Viewer and Camera) can now consume `MainWindow.parse_result` (a `ParseResult` with `.moves`, `.targets`, `.joint_targets`, `.source_text`) to build the VBO/VAO rendering pipeline.

No blockers for Phase 2.

---
*Phase: 01-parser-and-file-loading*
*Completed: 2026-03-30*

## Self-Check: PASSED

- FOUND: .planning/phases/01-parser-and-file-loading/01-03-SUMMARY.md
- FOUND: commit a49d6dd (feat(01-03): create MainWindow with file dialog and application entry point)
