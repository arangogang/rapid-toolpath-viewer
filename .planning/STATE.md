---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Toolpath Editing
status: Not started (roadmap created)
stopped_at: Phase 4 context gathered
last_updated: "2026-04-01T07:54:37.008Z"
last_activity: 2026-04-01 -- Roadmap created for v1.1
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 12
  completed_plans: 12
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-01)

**Core value:** .mod 파일을 열면 즉시 3D 툴패스가 렌더링되고, 각 워크포인트를 클릭하면 해당 RAPID 코드 줄로 이동할 수 있어야 한다.
**Current focus:** Milestone v1.1 -- Toolpath Editing (roadmap created, ready for Phase 4 planning)

## Current Position

Phase: 4 - Edit Infrastructure, Selection, and Inspection
Plan: --
Status: Not started (roadmap created)
Last activity: 2026-04-01 -- Roadmap created for v1.1

Progress: [----------] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 12 (v1.0)
- Average duration: ~2 min
- Total execution time: ~1 hour

**By Phase (v1.0):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 01 P01 | 12s | 2 tasks | 14 files |
| Phase 01 P02 | 3s | 2 tasks | 3 files |
| Phase 01 P03 | 20s | 1 tasks | 3 files |
| Phase 02 P01 | 138s | 2 tasks | 5 files |
| Phase 02 P02 | 142s | 1 tasks | 3 files |
| Phase 02 P03 | 558s | 2 tasks | 4 files |
| Phase 03 P01 | 321s | 2 tasks | 7 files |
| Phase 03 P02 | 195s | 2 tasks | 4 files |
| Phase 03 P03 | 638s | 2 tasks | 5 files |
| Phase 03 P04 | 639s | 2 tasks | 3 files |
| Phase 03 P05 | 120s | 2 tasks | 0 files |

**Recent Trend:**

- v1.0 milestone complete in 12 plans across 3 phases
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 3-phase coarse structure following data dependency chain (Parser -> Renderer -> Interactive features)
- [Roadmap]: REND-04 (TCP orientation triads) and PARS-08 (PROC selection) deferred to Phase 3 as they depend on stable renderer and are lower priority than core path rendering
- [Phase 01]: RobTarget/JointTarget use np.ndarray for pos/orient -- downstream rendering needs NumPy; custom __eq__/__hash__ override frozen dataclass default that fails on array comparison
- [Phase 01]: MoveAbsJ stored with has_cartesian=False and target=None -- parser tracks all moves for code panel, renderer skips non-Cartesian
- [Phase 01]: All 14 regex patterns compiled at module import time in patterns.py -- 5-10x performance vs per-call compilation
- [Phase 01]: Two-pass parser architecture ensures named references always resolve regardless of declaration order in .mod file
- [Phase 01]: tokenize_statements() tracks start_line from first non-empty content -- correct line for code panel highlighting
- [Phase 01]: Offs() resolution returns new RobTarget with pos offset; orient/confdata/extjoint inherited from base per ABB spec
- [Phase 01]: load_file() is public for testability without QFileDialog interaction; lazy parser import inside load_file() for clean error surfacing
- [Phase 02]: Interleaved [x,y,z,r,g,b] float32 vertex layout (stride 24 bytes) for all geometry types
- [Phase 02]: Color palette: MoveL=green, MoveJ=orange, MoveC=blue, markers=yellow
- [Phase 02]: AXES shaders are identity aliases to SOLID shaders (not copies)
- [Phase 02]: Use pyrr.matrix44.create_from_quaternion (module function) not pyrr.Matrix44.create_from_quaternion (class method does not exist in pyrr 0.10.3)
- [Phase 02]: Lazy import of ToolpathGLWidget inside MainWindow.__init__ to isolate OpenGL dependency from parser-only tests
- [Phase 02]: GL widget tests use _has_gl_context() guard to skip gracefully on headless/offscreen platforms
- [Phase 03]: Tokenizer treats PROC/ENDPROC/MODULE/ENDMODULE as implicit statement boundaries for correct source_line tracking
- [Phase 03]: PlaybackState.set_index only emits signal if index is valid AND different from current
- [Phase 03]: Use QTextEdit.ExtraSelection (not QPlainTextEdit.ExtraSelection) -- PyQt6 6.10.2 moved ExtraSelection to QTextEdit base class
- [Phase 03]: TrackingHighlighter subclass pattern for testing QSyntaxHighlighter setFormat calls
- [Phase 03]: Speed slider maps int 5-100 to 0.5x-10.0x; interval = int(500 / (value / 10.0))
- [Phase 03]: Ray-cast picking: screen-space projection of all waypoints, 20px threshold, Y-flip for Qt coords
- [Phase 03]: TCP triads reuse SOLID shader via identity aliases (TRIAD_VERT/TRIAD_FRAG)
- [Phase 03]: ABB quaternion [w,x,y,z] to pyrr [x,y,z,w] conversion with normalization guard
- [Phase 03]: GL context guard (_gl_ready) prevents makeCurrent() hang in headless tests
- [Phase 03]: blockSignals on PROC combo during load_file prevents spurious filter triggers
- [Phase 03]: Phase 3 verified complete via human visual inspection -- all 18 checks passed, no gap closure needed
- [v1.1 Roadmap]: 3-phase coarse structure: EditModel+Selection+Inspection (Phase 4) -> Modifications (Phase 5) -> Export (Phase 6)
- [v1.1 Roadmap]: Research phases 1+2 compressed into Phase 4 (EditModel + undo + selection + read-only property panel)
- [v1.1 Roadmap]: QUndoStack wired in Phase 4 before any mutation code exists (pitfall 3 avoidance)
- [v1.1 Roadmap]: Export last -- ModWriter design benefits from knowing all edit types (coordinate, speed, zone, laser, delete, insert)
- [v1.1 Roadmap]: Source text patching for .mod export, never regeneration (pitfall 2 avoidance)

### Pending Todos

None yet.

### Blockers/Concerns

- MoveAbsJ handling: jointtargets lack Cartesian positions; PARS-04 says parse but exclude from 3D rendering. Decide exact behavior during Phase 1 planning.
- File encoding: real .mod files may use Windows-1252. File loader needs encoding fallback strategy.
- Offs() target variant coverage in export: ModWriter must handle named targets, Offs() references, and inline bracket data (Phase 6 concern)
- MoveC arc topology in delete: verify parser representation of MoveC via-point + endpoint before implementing deletion (Phase 5 concern)
- PROC filter index mapping: EditModel must be canonical source, filtering re-applies from it (Phase 4 design concern)

## Session Continuity

Last session: 2026-04-01T07:54:37.001Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-edit-infrastructure-selection-and-inspection/04-CONTEXT.md
