---
phase: 01-parser-and-file-loading
plan: "02"
subsystem: parser
tags: [python, regex, rapid, pytest, numpy, tdd, two-pass-parser]

requires:
  - phase: 01-01
    provides: "RobTarget, JointTarget, MoveInstruction, MoveType, ParseResult dataclasses; 14 compiled regex patterns; 5 fixture .mod files; 11 test stubs"

provides:
  - "parse_module(source) -> ParseResult: two-pass RAPID .mod parser handling all 4 move types"
  - "tokenize_statements(source): semicolon-based tokenizer with comment stripping and line tracking"
  - "read_mod_file(path): UTF-8 with latin-1 fallback for Windows-encoded files"
  - "resolve_target_ref(): handles named refs, Offs() offset resolution, inline robtargets"
  - "All 11 TDD tests green (PARS-01 through PARS-07)"

affects:
  - 02-renderer
  - 03-interactive-features

tech-stack:
  added: []
  patterns:
    - "Two-pass parser: Pass 1 builds target lookup dicts, Pass 2 resolves move instructions"
    - "Semicolon-based statement tokenization before regex -- required for multiline robtarget declarations"
    - "Offs() resolution by cloning base RobTarget with pos += [dx, dy, dz], orient unchanged"
    - "TDD: RED commit (failing stubs) then GREEN commit (implementation)"

key-files:
  created:
    - "src/rapid_viewer/parser/rapid_parser.py"
  modified:
    - "tests/test_parser.py"
    - "src/rapid_viewer/parser/__init__.py"

key-decisions:
  - "Two-pass architecture: targets extracted before moves so named references always resolve correctly regardless of declaration order in .mod file"
  - "tokenize_statements() tracks start_line as line where first non-empty content appeared -- matches text editor line-click behavior for code panel"
  - "Offs() returns new RobTarget with modified pos only; orient/confdata/extjoint inherit from base -- correct per ABB RAPID spec"
  - "MoveAbsJ stored with has_cartesian=False and target=None -- parser tracks all moves for code panel; renderer skips non-Cartesian"

patterns-established:
  - "Pattern: All move instruction parsers call resolve_target_ref() -- single point for Offs/inline/named resolution"
  - "Pattern: try_* functions return None on no-match (not raise) -- clean two-pass scanning"

requirements-completed:
  - PARS-01
  - PARS-02
  - PARS-03
  - PARS-04
  - PARS-05
  - PARS-06
  - PARS-07

duration: 3min
completed: 2026-03-30
---

# Phase 01 Plan 02: RAPID .mod File Parser Summary

**Two-pass RAPID parser with semicolon tokenizer, Offs() resolution, and all 4 move types -- all 11 TDD tests green in under 3 minutes**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-30T08:04:27Z
- **Completed:** 2026-03-30T08:07:25Z
- **Tasks:** 2 of 2
- **Files modified:** 3

## Accomplishments

- Converted 11 pytest.skip() stubs to real assertions covering PARS-01 through PARS-07 plus Offs(), wobj, module_name, and procedures (RED state, `dc23b01`)
- Implemented `src/rapid_viewer/parser/rapid_parser.py` (457 lines) with full two-pass architecture: tokenizer, robtarget/jointtarget parsers, resolve_target_ref, try_parse_move, parse_module, read_mod_file
- All 11 tests pass green with zero failures and zero warnings (`33a047b`)
- Updated `src/rapid_viewer/parser/__init__.py` to re-export `parse_module` and `read_mod_file`

## Task Commits

Each task was committed atomically:

1. **Task 1: RED -- Convert test stubs to real assertions** - `dc23b01` (test)
2. **Task 2: GREEN -- Implement rapid_parser.py** - `33a047b` (feat)

**Plan metadata:** (docs commit -- see below)

_Note: TDD plan -- RED commit (failing tests) followed by GREEN commit (implementation)_

## Files Created/Modified

- `src/rapid_viewer/parser/rapid_parser.py` - Full two-pass RAPID parser: tokenize_statements, parse_robtarget_data, try_parse_robtarget_decl, try_parse_jointtarget_decl, resolve_target_ref, try_parse_move, parse_module, read_mod_file
- `tests/test_parser.py` - 11 real-assertion tests replacing pytest.skip() stubs
- `src/rapid_viewer/parser/__init__.py` - Added re-exports for parse_module and read_mod_file

## Decisions Made

- Two-pass architecture ensures named references always resolve even when Move instructions appear before robtarget declarations in the .mod file -- common in real ABB programs
- `tokenize_statements()` tracks `start_line` as the line where first non-empty content of the statement appeared, not where the semicolon was -- gives correct line for MoveJ on line 7 even if future RAPID code wraps across lines
- `resolve_target_ref()` checks Offs() pattern first (most specific), then inline brackets, then named lookup -- prevents false positives
- Offs() name stored as `"Offs(base_name,dx,dy,dz)"` string for traceability in ParseResult

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid escape sequence in docstring**
- **Found during:** Task 2 (GREEN implementation)
- **Issue:** Docstring contained `\WObj` which Python 3.12 flags as SyntaxWarning (invalid escape sequence)
- **Fix:** Changed `\WObj` to `WObj` in the docstring text only -- no behavior change
- **Files modified:** src/rapid_viewer/parser/rapid_parser.py
- **Verification:** pytest ran with 0 warnings after fix
- **Committed in:** 33a047b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Trivial docstring fix. No scope creep.

## Issues Encountered

None beyond the SyntaxWarning in the docstring (auto-fixed above).

## Known Stubs

None. `parse_module()` is fully implemented and all data flows from fixtures through parser to ParseResult. No hardcoded values or placeholder returns exist in the parser.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 02 (renderer) can immediately call `parse_module(source)` and receive a fully populated `ParseResult` with `moves`, `targets`, and `joint_targets`
- `result.moves` is a list of `MoveInstruction` objects where each has `move_type`, `target.pos` (numpy array), `target.orient`, `source_line`, and `has_cartesian`
- MoveAbsJ entries have `has_cartesian=False` and `target=None` -- renderer must filter these before constructing vertex buffers
- MoveC entries have both `circle_point` and `target` populated -- renderer needs both points for arc interpolation

---
*Phase: 01-parser-and-file-loading*
*Completed: 2026-03-30*

## Self-Check: PASSED

- FOUND: src/rapid_viewer/parser/rapid_parser.py
- FOUND: tests/test_parser.py
- FOUND: src/rapid_viewer/parser/__init__.py
- FOUND: .planning/phases/01-parser-and-file-loading/01-02-SUMMARY.md
- FOUND commit: dc23b01 (RED -- test stubs)
- FOUND commit: 33a047b (GREEN -- implementation)
- All 11 pytest tests pass
