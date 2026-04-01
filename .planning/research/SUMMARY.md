# Project Research Summary

**Project:** ABB RAPID Toolpath Viewer — Milestone v1.1 Toolpath Editing
**Domain:** Industrial robot program editor (Windows desktop, extending read-only viewer)
**Researched:** 2026-04-01
**Confidence:** HIGH

## Executive Summary

This milestone extends a working read-only RAPID toolpath viewer into a constrained editing tool. The goal is not a full IDE — it is a surgical correction tool that lets robot engineers adjust waypoint coordinates, speed/zone parameters, and laser state before uploading programs to ABB controllers. The existing stack (Python 3.11 + PyQt6 + PyOpenGL + NumPy + pyrr) requires zero new dependencies to implement editing; all required capabilities ship with PyQt6's standard library (QUndoStack, QFormLayout, QDoubleSpinBox, QRubberBand). The architecture upgrade is additive: frozen parser tokens stay frozen, and a new mutable EditModel layer wraps them for editing operations.

The recommended approach builds editing on top of the existing signal-driven architecture using a strict separation between a mutable edit model and the immutable parse layer. The critical design decision — and the one most commonly gotten wrong in tools of this type — is the .mod serialization strategy. The export function must patch original source text at known line positions rather than regenerating the file from parsed data. Regeneration destroys comments, IF/WHILE logic, custom PROC structure, and any RAPID code the parser does not understand, making the tool unusable for real-world programs. Text patching is the only viable strategy and must be designed before any editing features ship.

The two highest-risk decisions are (1) whether to wire QUndoStack from the start or retrofit it later, and (2) whether to use text patching or reconstruction for export. Both are architectural commitments that cannot be made later without rewriting all editing features already built. Research confidence is high across all four areas — the stack is proven, the architecture is based on direct codebase analysis, and the pitfalls are grounded in observed failure modes of similar tools and the existing code's constraints.

## Key Findings

### Recommended Stack

The existing stack is sufficient. No new packages are needed. The key additions come from modules already bundled with PyQt6: `QUndoStack`/`QUndoCommand` (in `PyQt6.QtGui`) for undo/redo, standard widget classes (`QFormLayout`, `QDoubleSpinBox`, `QComboBox`) for the property panel, and `QRubberBand` for drag-selection. The mutable edit model uses stdlib `dataclasses.replace()`, which is already established in `main_window.py`. Export uses stdlib `pathlib.Path.write_text()`.

**Core technologies (unchanged):**
- Python 3.11+: runtime — no change needed
- PyQt6 >=6.10: GUI + QUndoStack — adds undo framework and property panel widgets at no install cost
- PyOpenGL >=3.1.10: OpenGL rendering — existing pipeline reused without modification
- NumPy >=1.26: vertex buffers and coordinate math — batch selection highlight VBO
- pyrr >=0.10.3: 3D math — unchanged

**New capabilities unlocked from existing stack:**
- `PyQt6.QtGui.QUndoStack` + `QUndoCommand`: full undo/redo with Ctrl+Z/Ctrl+Y, clean-state tracking, window title asterisk for unsaved changes
- `dataclasses.replace()`: produce new frozen instances from edits (already used in `main_window.py` line 166)
- `str.splitlines()` + line-index replacement: surgical .mod source patching with no external parser

**What not to add:**
- Jinja2/Mako: overkill for .mod text patching; use direct string manipulation instead
- python-undo or similar: PyQt6's QUndoStack is better integrated; a second undo system creates competing state
- attrs/pydantic: dataclasses are sufficient for the edit model
- pandas: NumPy arrays cover all coordinate math needs

### Expected Features

The research confirmed a clear tier hierarchy. Single-waypoint coordinate editing is the #1 request on ABB community forums. Undo and Save As are non-negotiable — engineers will not use a tool without them. Multi-select and batch operations are the top differentiator but belong in v1.2 due to UI complexity. The feature dependency graph has a clear root: the mutable data model must exist before any editing feature can be built.

**Must have (table stakes):**
- Single waypoint selection in 3D — required before any editing action; extends existing ray-cast picking
- Waypoint info panel — coordinate, speed, zone, laser state display on selection
- Coordinate modification (offset-based, not absolute) — #1 edit operation for robot engineers; absolute input risks dangerous typos
- Speed and zone property editing — second most common edit; use dropdown for constrained RAPID values
- Laser on/off toggle — domain-specific table stake for laser welding/cutting application
- Save As / Export modified .mod — editing without export is useless; "Save As" only, never overwrite
- Undo/Redo — engineers will not edit without a safety net; must be wired before any edit feature
- Delete waypoint — remove erroneous or unnecessary points with topology reconnection choice

**Should have (differentiators):**
- Real-time 3D update on edit — immediate visual feedback when property values change
- Dirty state indicator — asterisk in title bar, "Save changes?" prompt on close
- Multi-select + batch offset — select multiple points, apply same offset to all; deferred to v1.2
- Coordinate system display (world + wobj frame) — engineers think in workobject coordinates

**Defer to v1.2:**
- Multi-select and batch operations — valuable but adds significant UI complexity; single-point covers 80% of use cases
- Visual diff (original vs modified ghost overlay) — nice to have, not blocking
- Insert waypoint — high complexity (new robtarget generation + source insertion)
- 3D drag gizmos — high effort, low precision; engineers prefer numeric input

**Explicit anti-features:**
- In-place RAPID code editing — scope creep into IDE territory; code panel stays read-only
- Robot arm / IK visualization — RobotStudio's domain
- Collision detection — requires CAD mesh import
- Overwrite save — robot production files must not be silently overwritten

### Architecture Approach

The architecture change is additive: the parse pipeline is unchanged, and a new mutable EditModel layer sits between ParseResult and the UI. The key architectural win is that `EditModel.to_parse_result()` produces output compatible with the existing `build_geometry()` function — the entire rendering pipeline is reused without modification. All edits flow through an EditController which handles scene rebuild after mutations. A new ModWriter module patches original source text at known `source_line` positions, applying patches bottom-to-top to keep line numbers valid.

**Major components (new):**
1. `EditModel` (`model/edit_model.py`) — mutable working copy of ParseResult; owns selection state; emits Qt signals on change; single source of truth for all editing operations
2. `EditableMove` (inner class of EditModel) — mutable wrapper around frozen `MoveInstruction`; tracks `is_modified` per field for surgical export patching
3. `EditController` (`model/edit_controller.py`) — command dispatch between PropertyPanel and EditModel; triggers scene rebuild; QUndoStack integration point
4. `PropertyPanel` (`ui/property_panel.py`) — QFormLayout-based inspector showing/editing waypoint properties; offset-based coordinate input (not absolute); speed/zone via QComboBox
5. `ModWriter` (`export/mod_writer.py`) — exports modified .mod by patching original source text; applies changes bottom-to-top to preserve line number validity throughout the patch sequence

**Existing components requiring moderate changes:**
- `MainWindow`: add 3-way QSplitter, QUndoStack instance, Edit menu, File > Save As action
- `ToolpathGLWidget`: add Ctrl+click multi-select, selection highlight VBO, emit modifier key state
- `CodePanel`: update displayed text after edits (observe mutable document rather than original source_text)

**Patterns to follow:**
- Immutable core / mutable wrapper: parser tokens stay frozen; EditableMove wraps them
- Signal-driven updates: all state flows through Qt signals; no direct cross-component calls
- Controller mediates mutations: PropertyPanel never calls EditModel directly
- Full scene rebuild on edit: `build_geometry()` + `update_scene()` is fast enough for <5000 moves
- Source patching for export: patch original source_text, never regenerate

**Anti-patterns to avoid:**
- Making parser dataclasses mutable: breaks `__hash__`, corrupts `targets` dict lookups
- In-place source text mutation during editing: shifts line numbers and invalidates all `source_line` references
- Dual source of truth for move list: both PlaybackState and EditModel holding separate copies leads to desync
- Direct GL widget mutation from PropertyPanel: bypasses EditModel, loses change tracking, breaks undo

### Critical Pitfalls

1. **Frozen dataclass mutation (rewrite risk)** — Do not remove `frozen=True` from `MoveInstruction` or `RobTarget`. Unfreezing breaks custom `__hash__` and corrupts the `targets` dict. Use `dataclasses.replace()` to produce new frozen instances; this pattern is already established in `main_window.py`.

2. **Serialization destroys .mod content (feature DOA)** — Never reconstruct .mod from parsed data. The parser discards comments, IF/ELSE blocks, custom PROCs, and all non-move content intentionally. Use text patching: locate the source line via `source_line` metadata, regex-replace only the changed values, apply patches bottom-to-top. This is the single highest-risk architectural decision.

3. **Undo/redo cannot be retrofitted (rewrite risk)** — Wire QUndoStack before implementing any edit feature. Every mutation must be a QUndoCommand subclass from day one. Retrofitting undo after building editing features requires rewriting every edit operation. Use `beginMacro`/`endMacro` for compound operations like delete+reconnect.

4. **Signal loops from multiple selection observers** — With 4 components observing selection state (3D widget, code panel, playback state, property panel), circular signal chains cause infinite loops or stale UI. Keep PlaybackState as the single source of truth for index. Use `blockSignals(True)` when programmatically updating UI controls that emit change signals.

5. **Delete waypoint topology corruption** — Deleting waypoint B from A->B->C silently creates an A->C connection. MoveC arcs become invalid if their intermediate point is deleted. Implement deletion as a multi-step operation with user confirmation; use soft-delete (mark as disabled) to make undo trivial.

6. **PROC filter + EditModel index mismatch** — The existing PROC filter creates a filtered view using `dataclasses.replace()`. Edits made in a filtered view must reference canonical (unfiltered) move indices, not filtered list indices. EditModel must be the canonical source; filtering re-applies after every edit.

## Implications for Roadmap

Based on the feature dependency graph (FEATURES.md), architecture build order (ARCHITECTURE.md), and pitfall-to-phase mapping (PITFALLS.md), the editing milestone should be structured in four phases. The dependency chain is deterministic: EditModel first (all editing depends on it), undo infrastructure at the same time, visual inspection before mutation, mutations before export.

### Phase 1: Mutable Edit Model + Undo Infrastructure

**Rationale:** The feature dependency graph from FEATURES.md shows the mutable data model as the root dependency of all editing operations — no edit feature can be built without it. PITFALLS.md ranks undo retrofit as a rewrite-level risk (Pitfall 3). Both must be established before any editing UI exists. This phase produces no visible editing UI but is entirely unit-testable in isolation, providing a safe foundation.
**Delivers:** `EditModel` with `EditableMove` wrapper, `EditController` stub, QUndoStack wired into MainWindow with Edit menu (Undo/Redo/Delete disabled until file loaded), PROC filter updated to reference canonical EditModel indices
**Addresses:** Mutable data model (root dependency), undo infrastructure, PROC filter architecture
**Avoids:** Pitfall 1 (frozen mutation via dataclasses.replace()), Pitfall 3 (undo retrofit), Pitfall 6 (PROC filter index mismatch), Pitfall 12 (signal loops — establish single source of truth discipline from the start)

### Phase 2: Property Panel + Selection Enhancement

**Rationale:** Once EditModel exists, the property panel is the first user-visible editing feature. ARCHITECTURE.md recommends building the panel read-only first to validate signal wiring before adding mutation complexity. This phase also handles the 3-way splitter layout change in MainWindow and the selection highlight infrastructure in the GL widget.
**Delivers:** PropertyPanel (read-only display), 3-way QSplitter layout (GL | Property | Code at 55/20/25%), Ctrl+click multi-select in ToolpathGLWidget, selection highlight VBO, dirty state indicator in title bar
**Addresses:** Waypoint info panel (table stake), single waypoint selection in 3D, real-time 3D feedback for selection changes
**Avoids:** Pitfall 5 (signal loops — PropertyPanel observes EditModel via signals, never calls GL widget directly), Pitfall 11 (accidental edits — explicit selection required before editing is possible)

### Phase 3: Edit Operations + QUndoCommand Integration

**Rationale:** With EditModel and PropertyPanel in place, all edit operations (coordinate offset, speed, zone, laser, delete) can be built using a consistent QUndoCommand pattern. ARCHITECTURE.md confirms full scene rebuild is fast enough (< 50ms for typical files) so no GL optimization is needed for v1.1. FEATURES.md recommends this build order within the phase: coordinate modification first, then speed/zone, then delete.
**Delivers:** Coordinate offset editing with immediate 3D update, speed/zone editing via QComboBox with RAPID value validation, laser toggle, waypoint deletion with topology warning and soft-delete for easy undo, all operations wrapped in QUndoCommands, Edit Mode toggle to prevent accidental edits during camera navigation
**Addresses:** All 8 table stake editing features from FEATURES.md
**Avoids:** Pitfall 4 (GL rebuild — use full rebuild, not incremental, for simplicity), Pitfall 6 (delete topology — confirmation dialog + MoveC warning), Pitfall 7 (stale source_line — track edits as patch list, not source_text mutation), Pitfall 10 (speed/zone validation via dropdown + format check), Pitfall 11 (Edit Mode toggle)

### Phase 4: Save As / .mod Export

**Rationale:** ARCHITECTURE.md notes ModWriter only depends on EditModel (not on PropertyPanel or EditController), so it can theoretically be built in parallel with Phase 3. Placing it last ensures the text-patching engine is designed with a complete picture of all edit types it must handle — coordinate, speed, zone, laser, and delete. This is the "capstone" that makes all edits permanent. The serialization strategy (text patching) must be validated against real-world .mod files including the sample `00_CoCr_19.2pi_Shear_Test.mod` before shipping.
**Delivers:** ModWriter with source text patching (bottom-to-top patch application preserving line number validity), File > Save As menu action with QFileDialog (Ctrl+Shift+S), code panel refresh after edits so modified values appear in the source view, Offs() dependency warning displayed in PropertyPanel for affected targets
**Addresses:** Save As / Export (final table stake), code panel sync, Offs() transparency
**Avoids:** Pitfall 2 (serialization destroys content — text patching, not regeneration), Pitfall 7 (stale line numbers — patches reference original source_line from ParseResult, applied at export time only), Pitfall 8 (Offs() dependencies — display warning rather than silent stale positions), Pitfall 9 (code panel stale — single mutable document as source of truth)

### Phase Ordering Rationale

- EditModel must come first because FEATURES.md's dependency graph shows it as the root of all editing operations; no edit feature can exist without it
- QUndoStack wired in Phase 1 (not Phase 3) because PITFALLS.md identifies undo retrofit as a full-rewrite risk; every QUndoCommand subclass in Phase 3 is trivial to write if the stack is already wired
- PropertyPanel built read-only in Phase 2 before mutations are added; this validates the EditModel signal wiring without the complexity of mutations, reducing the debugging surface when edits are introduced
- Save As placed last because the ModWriter design benefits from knowing all edit types it must handle; building it early risks missing a case and requiring a redesign of the patch format
- This order avoids all critical pitfalls by design: the mutable wrapper is established before any UI (Pitfall 1), the serialization strategy is committed to at architecture time (Pitfall 2), undo is wired before mutations (Pitfall 3), selection architecture is clean before adding the fourth observer (Pitfall 5), delete topology is handled alongside the delete command (Pitfall 6)

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Save As / Export):** The text-patching engine must handle three robtarget declaration variants: named target (`CONST robtarget p10 := ...`), `Offs()` reference in the move instruction, and inline bracket data. Verify all three formats against the sample `00_CoCr_19.2pi_Shear_Test.mod` file before implementing. The regex patterns for each variant need validation.
- **Phase 3 (Delete):** MoveC arc topology handling requires understanding the parser's internal representation of MoveC (via-point + endpoint pair). Inspect `tokens.py` and `rapid_parser.py` for MoveC handling before implementing deletion for MoveC instructions to avoid the arc-becomes-invalid case silently.

Phases with standard patterns (skip research-phase):
- **Phase 1 (EditModel + Undo):** QUndoStack is well-documented in Qt 6.11 official docs. `dataclasses.replace()` is stdlib. The pattern is already used in the codebase. No novel technical challenges.
- **Phase 2 (PropertyPanel):** QFormLayout, QDoubleSpinBox, QComboBox, QSplitter are standard Qt widgets. Verified in Qt 6.11 docs. No research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new dependencies. All capabilities verified in PyQt6 6.10/6.11 official documentation. QUndoStack confirmed in QtGui module (not just QtWidgets). `dataclasses.replace()` usage already present in codebase. |
| Features | MEDIUM-HIGH | Table stakes confirmed via ABB community forum threads and RobotStudio/RoboDK competitive analysis. Domain-specific laser toggle not independently validated against other ABB laser cell tools — assumed correct from PROJECT.md context. |
| Architecture | HIGH | Based on direct analysis of all existing modules (`tokens.py`, `rapid_parser.py`, `geometry_builder.py`, `toolpath_gl_widget.py`, `main_window.py`, `playback_state.py`). Component boundaries, signal patterns, and integration points are derived from actual code, not inference. |
| Pitfalls | HIGH | Pitfalls 1–6 grounded in direct codebase risk analysis. Serialization pitfall confirmed by round-trip parsing literature. GL rebuild pitfall confirmed by OpenGL VBO documentation. QUndoStack guidance from Qt official docs. |

**Overall confidence:** HIGH

### Gaps to Address

- **Offs() target variant coverage in export:** The parser resolves `Offs(base, dx, dy, dz)` to standalone `RobTarget` instances with no stored back-reference. The ModWriter must handle this case, but the exact source text format of `Offs()` occurrences (inline in move instruction vs. separate variable assignment) needs verification against the sample .mod file before Phase 4. At minimum, display a warning in PropertyPanel when the selected target was derived via Offs().

- **MoveC arc representation in delete:** PITFALLS.md identifies MoveC deletion as a special case requiring user confirmation. The exact parser representation of MoveC's via-point and endpoint (separate MoveInstruction entries vs. a single compound entry) must be confirmed in `tokens.py` before Phase 3 delete implementation to avoid silent arc corruption.

- **Code panel refresh strategy:** Pitfall 9 requires the code panel to observe a single mutable document rather than the original `source_text`. The exact mechanism — whether EditController pushes patched text to CodePanel after each edit, or whether CodePanel subscribes to an EditModel signal — should be decided in Phase 2 (when PropertyPanel is wired) rather than Phase 3 (when the first mutation happens).

- **PROC filter index mapping implementation:** Pitfall 12 requires edits to reference canonical (unfiltered) move indices. The Phase 1 EditModel design must explicitly address how filtered view indices map back to canonical indices. The existing `dataclasses.replace(self._parse_result, moves=filtered_moves)` pattern creates a disconnected copy — EditModel must be the canonical source and filtering must re-apply from it.

## Sources

### Primary (HIGH confidence)
- Qt 6.11 official documentation (QUndoStack, QUndoCommand, QFormLayout, QUndoStack overview, Undo Framework Example) — undo framework API, integration patterns, and implementation reference
- Direct codebase analysis of `tokens.py`, `rapid_parser.py`, `geometry_builder.py`, `toolpath_gl_widget.py`, `main_window.py`, `playback_state.py` — architecture baseline and pitfall identification grounded in actual code
- ABB RAPID Technical Reference Manual (3HAC16581-1) — robtarget data type, MoveL/MoveJ/MoveC syntax, speed and zone data types
- OpenGL VBO best practices (Khronos Wiki, LearnOpenGL Advanced Data) — glBufferSubData vs glBufferData guidance for GL rebuild pitfall

### Secondary (MEDIUM confidence)
- ABB RobotStudio and RoboDK documentation — competitive feature analysis for table stakes; confirms coordinate modification and speed/zone editing as top user needs
- ABB community forums (robotstudio.com/discussion/10759, discussion/8547) — direct confirmation that coordinate modification is the #1 request for simple program editors
- ABB Developer Center Undo-Redo article — reference for RobotStudio's own command pattern implementation

### Tertiary (MEDIUM confidence)
- Round-trip parsing literature (jayconrod.com "Preserving comments when parsing", lossless syntax trees article) — validation of text patching vs AST regeneration strategy for editors that must preserve formatting

---
*Research completed: 2026-04-01*
*Ready for roadmap: yes*
