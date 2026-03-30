---
phase: 01-parser-and-file-loading
plan: "01"
subsystem: parser
tags: [python, dataclasses, regex, rapid, pytest, numpy]

requires: []

provides:
  - "RobTarget, JointTarget, MoveInstruction, MoveType, ParseResult frozen dataclasses in tokens.py"
  - "14 compiled regex patterns for RAPID syntax in patterns.py"
  - "5 fixture .mod files covering all move types and edge cases"
  - "11 test stubs for TDD Plan 02 covering PARS-01 through PARS-07"
  - "pyproject.toml with pytest configured (testpaths=[tests], pythonpath=[src])"

affects:
  - 01-parser-and-file-loading
  - 02-renderer

tech-stack:
  added:
    - "Python stdlib: dataclasses, enum, re (regex)"
    - "numpy >=1.26 (pos/orient ndarray storage)"
    - "pytest 9.0.2 (test framework)"
  patterns:
    - "Frozen dataclasses for immutable token types (RobTarget, JointTarget, MoveInstruction)"
    - "Non-frozen dataclass for mutable result container (ParseResult)"
    - "Module-level re.compile() for all regex patterns (performance)"
    - "Custom __eq__ and __hash__ on frozen dataclasses containing np.ndarray fields"
    - "src/ layout with pythonpath pytest config for clean imports"

key-files:
  created:
    - "pyproject.toml"
    - "src/rapid_viewer/__init__.py"
    - "src/rapid_viewer/parser/__init__.py"
    - "src/rapid_viewer/parser/tokens.py"
    - "src/rapid_viewer/parser/patterns.py"
    - "src/rapid_viewer/ui/__init__.py"
    - "tests/__init__.py"
    - "tests/conftest.py"
    - "tests/fixtures/simple.mod"
    - "tests/fixtures/multiline.mod"
    - "tests/fixtures/movecircular.mod"
    - "tests/fixtures/moveabsj.mod"
    - "tests/fixtures/offs_inline.mod"
    - "tests/test_parser.py"
  modified: []

key-decisions:
  - "RobTarget and JointTarget use np.ndarray for pos/orient — directly compatible with downstream rendering pipeline, no conversion needed"
  - "Custom __eq__/__hash__ on frozen dataclasses override default (which fails on ndarray comparison) using np.array_equal"
  - "MoveAbsJ stored with has_cartesian=False and target=None — parser tracks all moves for code panel, renderer skips non-Cartesian"
  - "All 14 regex patterns compiled at module import time for 5-10x repeated-use performance"
  - "Scientific notation handled in _NUM pattern — required for 9E+09 external axis convention"

patterns-established:
  - "Pattern: Parser dataclasses are pure Python with no Qt dependency — enables unit testing without GUI"
  - "Pattern: frozen=True for token types (RobTarget, JointTarget, MoveInstruction), non-frozen for ParseResult"
  - "Pattern: Test fixtures are real RAPID .mod syntax with valid structure"

requirements-completed:
  - PARS-05
  - PARS-06
  - PARS-07

duration: 12min
completed: 2026-03-30
---

# Phase 01 Plan 01: Project Skeleton and Data Model Contracts Summary

**Parser dataclasses (RobTarget, JointTarget, MoveInstruction, ParseResult), 14 compiled RAPID regex patterns, 5 fixture .mod files, and 11 TDD test stubs — all contracts defined before implementation begins**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-30T07:57:51Z
- **Completed:** 2026-03-30T08:09:51Z
- **Tasks:** 2 of 2
- **Files modified:** 14

## Accomplishments

- Created complete project skeleton with pyproject.toml, src/ layout, and pytest configured with src/ on pythonpath
- Defined all 5 data model contracts as typed dataclasses: MoveType enum, RobTarget, JointTarget, MoveInstruction (frozen), ParseResult (non-frozen with default_factory lists)
- Implemented 14 compiled regex patterns covering robtarget/jointtarget declarations, all 4 move instruction types, Offs(), WObj, and module/proc boundaries
- Created 5 fixture .mod files with valid RAPID syntax covering simple moves, multiline declarations, MoveC, MoveAbsJ, and Offs() expressions
- Created 11 test stubs (red state) covering PARS-01 through PARS-07 plus Offs, wobj, module_name, and procedures for TDD Plan 02

## Task Commits

Each task was committed atomically:

1. **Task 1: Create project skeleton and data model contracts** - `58bc132` (feat)
2. **Task 2: Create test fixtures and test stubs** - `8d2193f` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `pyproject.toml` - Project config with pytest testpaths/pythonpath and ruff line-length
- `src/rapid_viewer/__init__.py` - Package with `__version__ = "0.1.0"`
- `src/rapid_viewer/parser/__init__.py` - Re-exports all public token types
- `src/rapid_viewer/parser/tokens.py` - MoveType, RobTarget, JointTarget, MoveInstruction, ParseResult dataclasses
- `src/rapid_viewer/parser/patterns.py` - 14 compiled regex patterns for RAPID syntax
- `src/rapid_viewer/ui/__init__.py` - Empty placeholder for Phase 03 UI components
- `tests/__init__.py` - Empty package marker
- `tests/conftest.py` - Fixtures for all 5 .mod files
- `tests/fixtures/simple.mod` - MoveL + MoveJ basic moves, 3 robtargets
- `tests/fixtures/multiline.mod` - Multiline robtarget declarations spanning 5+ lines
- `tests/fixtures/movecircular.mod` - MoveC with circle_point and end_point
- `tests/fixtures/moveabsj.mod` - MoveAbsJ with jointtarget, plus MoveL
- `tests/fixtures/offs_inline.mod` - Offs() inline expressions
- `tests/test_parser.py` - 11 test stubs in red/skip state

## Decisions Made

- Used `np.ndarray` for `pos` and `orient` fields on RobTarget — downstream OpenGL rendering needs NumPy arrays; avoids conversion step
- Added custom `__eq__` and `__hash__` to frozen dataclasses holding `np.ndarray` because Python's default frozen dataclass `__eq__` uses `==` which returns an array for ndarray
- MoveAbsJ design: `has_cartesian=False`, `target=None`, `joint_target` populated — renderer skips it in 3D, code panel still shows source line
- All regex patterns compiled once at module-level import, not per-call

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. All imports verified, pytest collected 11 tests without errors.

## Known Stubs

None - this plan defines contracts only. No data flows to UI yet; `parse_module()` implementation is Plan 02's scope.

## User Setup Required

None - no external service configuration required. All dependencies (pytest, numpy) are standard Python packages.

## Next Phase Readiness

- Plan 02 can immediately implement `parse_module()` in `src/rapid_viewer/parser/rapid_parser.py` — all contracts and test infrastructure are in place
- Test stubs in `tests/test_parser.py` turn green as implementation completes each requirement
- The 5 fixture files provide comprehensive coverage for the TDD cycle

---
*Phase: 01-parser-and-file-loading*
*Completed: 2026-03-30*
