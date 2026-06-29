---
phase: 06-export
verified: 2026-06-29T00:00:00Z
status: human_needed
score: 11/11 must-haves verified
re_verification: false
human_verification:
  - test: "Make several edits (offset, speed change, delete, insert), then File > Save As (Ctrl+Shift+S) to a NEW filename"
    expected: "Native save dialog appears defaulting to '<name>_modified.mod'; the file is written; the dirty asterisk clears from the title bar; the status bar shows 'Saved: <name>'"
    why_human: "QFileDialog is a blocking native dialog that cannot be driven in a headless pytest session"
  - test: "Re-open the exported .mod file"
    expected: "All edits are present -- moved positions, changed speed/zone, '! [DELETED]' comments for removed points, and a new MoveL line after the source of each inserted point"
    why_human: "Round-trip is unit-tested programmatically, but visual confirmation in the reopened file/3D view requires an interactive session"
  - test: "Select a point, enter dZ=100, click Insert After, then watch the code panel"
    expected: "Property panel + 3D highlight follow the new point AND the code-panel highlight lands on the newly inserted MoveL line (one below the source)"
    why_human: "Confirms the forward highlight fix (export line map) behaves correctly in the live event loop"
---

# Phase 6: Export (.mod Save As) Verification Report

**Phase Goal:** Export the edited toolpath back to a valid RAPID .mod file via source-text patching (preserving formatting/comments/non-move code), wired into a Save As UI action with encoding preservation and overwrite protection.
**Verified:** 2026-06-29T00:00:00Z (retroactive close-out of the v1.1 milestone audit gap)
**Status:** human_needed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `export_mod(...)` splits source into lines and patches in place (trailing newline preserved) | VERIFIED | `mod_writer.py` `export_mod`; round-trip test asserts identity for unmodified input |
| 2  | Named-target position edits patch the (possibly multiline) robtarget declaration | VERIFIED | `_patch_robtarget_pos` via `__ROBTARGET_POS__` sentinel; `test_patch_named_target_pos`, `test_multiline_robtarget` |
| 3  | Offs() targets patch numeric args and preserve variable args (e.g. zLayer) | VERIFIED | `_patch_offs_args`; `test_patch_offs_target` |
| 4  | Inline `[[x,y,z]...]` targets are patched on the move line | VERIFIED | `_patch_inline_pos`; `test_patch_inline_target` |
| 5  | Speed/zone edits replace the correct tokens using bracket-depth comma parsing | VERIFIED | `_patch_speed_zone`; `test_patch_speed`, `test_patch_zone` |
| 6  | Deleted points are commented out as `! [DELETED] <orig>` (formatting preserved) | VERIFIED | `test_delete_comments_out` |
| 7  | Inserted points generate a `MoveL` line after the source line, inheriting indent | VERIFIED | `_generate_move_line` + `INSERT_AFTER`; `test_insert_generates_line` |
| 8  | An inserted-then-deleted point emits nothing (export/build_edited_moves/line-map agree) | VERIFIED | reconciliation fix 2026-06-29; `test_inserted_then_deleted_emits_nothing` |
| 9  | Patches apply in descending line order so indices stay valid through insert/delete | VERIFIED | `patches.sort(..., reverse=True)`; `test_reverse_patch_order` |
| 10 | Save As (Ctrl+Shift+S) writes the patched text using the file's tracked encoding, with overwrite protection + dirty clear | VERIFIED | `main_window._save_as`; `test_save_as_prevents_overwrite`, `test_save_as_exports_file` |
| 11 | export_mod optionally emits a visible-index -> exported-line map for highlight sync, without altering the returned text | VERIFIED | `line_map` out-param 2026-06-29; `test_line_map_*` (6 tests) confirm content + byte-identical output when omitted |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status |
|----------|----------|--------|
| `src/rapid_viewer/export/mod_writer.py` | export_mod() + patch helpers for all 6 edit types + optional line_map | VERIFIED |
| `src/rapid_viewer/export/__init__.py` | re-export of export_mod | VERIFIED |
| `src/rapid_viewer/ui/commands.py` | InsertPointCommand sets is_inserted=True | VERIFIED |
| `src/rapid_viewer/parser/rapid_parser.py` | read_mod_file returns (content, encoding) | VERIFIED |
| `src/rapid_viewer/ui/main_window.py` | `_save_as()` + encoding tracking + overwrite guard + dirty clear + line-map highlight | VERIFIED |
| `tests/test_mod_writer.py` | export tests covering all edit types + round-trip + line_map | VERIFIED (19 tests) |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `main_window._save_as` | `export/mod_writer.py` | `export_mod(..., line_map=...)` -> file write + highlight | WIRED |
| `main_window._on_points_changed` | `export/mod_writer.py` | export -> code-panel live preview + `_highlight_current_line` | WIRED |
| `rapid_parser.read_mod_file` | `main_window` | `(content, encoding)` -> reused on write | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| export_mod imports cleanly | `python -c "from rapid_viewer.export.mod_writer import export_mod"` | ok | PASS |
| ModWriter tests pass | `pytest tests/test_mod_writer.py -q` | 19 passed | PASS |
| Full suite, no regressions | `PYTHONPATH=src py -3.12 -m pytest -q` | 183 passed | PASS |

### Requirements Coverage

| Requirement | Plan | Description | Status |
|-------------|------|-------------|--------|
| EXP-01 | 06-01, 06-02 | Save As .mod export preserving all edit types | SATISFIED |

### Known Limitations (non-blocking)

1. **Forward code-panel highlight after edits is now FIXED.** `export_mod` populates an optional `{visible-index -> exported-line}` map; `MainWindow._highlight_current_line` consults it so insert/delete navigation highlights the correct regenerated line (previously the inserted point highlighted the source line / a `! [DELETED]` line). The map falls back to `source_line` when a PROC filter is active (indices don't align). Covered by `test_insert_highlights_inserted_line_not_source`.
2. **Reverse direction (code-click -> 3D select) still uses frozen source_line.** `_on_code_line_clicked` matches the clicked line against `move.source_line`, so after an insert, clicking the shifted/inserted lines may select the wrong move or none. OPEN (tracked follow-up).
3. **Chained-insert saved order.** `export_mod`'s descending-sort insertion writes multiple inserts after the same source line in reverse path order. The highlight map mirrors this so highlighting stays consistent with the saved text, but the saved RAPID executes those inserted moves in reverse order. Separate pre-existing export-ordering issue; OPEN (tracked follow-up).

### Human Verification Required

See frontmatter -- Save As round-trip (EXP-01), reopening the exported file, and confirming the insert highlight now lands on the inserted line.

### Gaps Summary

No automated gaps. All 11 observable truths verified by code inspection and the 19 ModWriter tests plus the Save As tests (183 total, green). EXP-01 is satisfied at the export-engine and UI-wiring layers. The forward highlight desync is resolved this milestone; the reverse code-click direction and the chained-insert saved-order issue remain as documented non-blocking follow-ups.

---

_Verifier: Claude (retroactive close-out of the v1.1 milestone audit gap; Phase 6 had no VERIFICATION.md)._
