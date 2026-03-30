---
phase: 03-playback-code-panel-and-linking
plan: 01
subsystem: ui, parser
tags: [qt-signals, playback, proc-ranges, tdd, qobject]

requires:
  - phase: 01-rapid-parser-and-file-load
    provides: MoveInstruction, ParseResult, parse_module, tokenize_statements
provides:
  - PlaybackState QObject with current_changed/moves_changed signals
  - ParseResult.proc_ranges dict mapping PROC names to line ranges
  - multiproc.mod test fixture
affects: [03-02, 03-03, 03-04, 03-05]

tech-stack:
  added: [pytest-qt]
  patterns: [QObject signal-based state model, stack-based PROC/ENDPROC pairing]

key-files:
  created:
    - src/rapid_viewer/ui/playback_state.py
    - tests/test_playback_state.py
    - tests/fixtures/multiproc.mod
  modified:
    - src/rapid_viewer/parser/tokens.py
    - src/rapid_viewer/parser/rapid_parser.py
    - tests/test_parser.py
    - tests/conftest.py

key-decisions:
  - "Tokenizer treats PROC/ENDPROC/MODULE/ENDMODULE as implicit statement boundaries for correct source_line tracking"
  - "PlaybackState.set_index only emits signal if index is valid AND different from current"

patterns-established:
  - "Signal-based state model: QObject subclass with pyqtSignal for observable state changes"
  - "TDD workflow: RED (failing tests) -> GREEN (minimal implementation) -> commit"

requirements-completed: [PLAY-01, PLAY-02, PLAY-03, PARS-08]

duration: 5min
completed: 2026-03-30
---

# Phase 03 Plan 01: PlaybackState Model and PROC Range Extraction Summary

**PlaybackState QObject with step/index signals for waypoint navigation, plus parser PROC line range extraction with tokenizer fix for structural keywords**

## Performance

- **Duration:** 5 min (321s)
- **Started:** 2026-03-30T10:00:05Z
- **Completed:** 2026-03-30T10:05:26Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- PlaybackState model with current_changed/moves_changed Qt signals, step_forward/backward/set_index API
- ParseResult.proc_ranges maps PROC names to (start_line, end_line) tuples for multi-procedure filtering
- Tokenizer fixed to treat PROC/ENDPROC/MODULE/ENDMODULE as implicit statement boundaries (correct source_line for code panel linking)
- 14 new tests (10 PlaybackState + 4 proc_ranges), all passing alongside 11 existing parser tests

## Task Commits

Each task was committed atomically:

1. **Task 1: PlaybackState model with Qt signals** - `e38ba4f` (feat)
2. **Task 2: Parser PROC range extraction and multiproc test fixture** - `41e9b0f` (feat)

## Files Created/Modified
- `src/rapid_viewer/ui/playback_state.py` - PlaybackState QObject with signals for waypoint navigation
- `tests/test_playback_state.py` - 10 unit tests covering all state transitions and boundary conditions
- `tests/fixtures/multiproc.mod` - Test fixture with 2 PROCs (main, path2) and 5 robtargets
- `src/rapid_viewer/parser/tokens.py` - Added proc_ranges field to ParseResult dataclass
- `src/rapid_viewer/parser/rapid_parser.py` - PROC range extraction + tokenizer structural keyword handling
- `tests/test_parser.py` - 4 new proc_ranges tests (single, multi, filtering, empty)
- `tests/conftest.py` - Added multiproc_mod fixture

## Decisions Made
- Tokenizer treats PROC/ENDPROC/MODULE/ENDMODULE as implicit statement boundaries: Without this fix, the tokenizer merged ENDPROC with the next PROC's content into one statement, causing incorrect source_line values that broke proc_ranges filtering.
- PlaybackState.set_index only emits signal when index is valid AND different from current: prevents duplicate signal spam from step_forward/backward calling set_index at boundaries.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tokenizer structural keyword handling**
- **Found during:** Task 2 (PROC range extraction)
- **Issue:** Tokenizer merged ENDPROC with following PROC content into one statement because ENDPROC lacks a semicolon. This caused MoveJ in path2 to get source_line=11 instead of 14, falling outside path2's proc_range (13, 17).
- **Fix:** Added `_is_structural_keyword()` helper and structural keyword detection in tokenize_statements() to flush accumulated content and emit structural keywords as separate statements.
- **Files modified:** src/rapid_viewer/parser/rapid_parser.py
- **Verification:** All 25 tests pass (11 existing + 14 new), proc_ranges filtering correctly isolates moves per PROC.
- **Committed in:** 41e9b0f (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Fix was necessary for proc_ranges filtering to work correctly. No scope creep -- this is a correctness fix for the feature being built.

## Issues Encountered
None beyond the tokenizer fix documented above.

## Known Stubs
None -- all functionality is fully wired.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- PlaybackState is ready for Phase 03 Plan 02+ UI components to observe
- proc_ranges enables PROC dropdown filtering in upcoming plans
- All existing tests continue passing (no regressions)

---
*Phase: 03-playback-code-panel-and-linking*
*Completed: 2026-03-30*
