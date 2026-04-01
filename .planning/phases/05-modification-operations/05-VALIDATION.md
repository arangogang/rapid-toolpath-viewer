---
phase: 5
slug: modification-operations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0+ with pytest-qt 4.4+ |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `python -m pytest tests/test_commands.py tests/test_edit_model.py -x` |
| **Full suite command** | `python -m pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_commands.py tests/test_edit_model.py -x`
- **After every plan wave:** Run `python -m pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | MOD-01 | unit | `python -m pytest tests/test_commands.py::TestOffsetCommand -x` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | MOD-01 | unit | `python -m pytest tests/test_commands.py::TestOffsetCommandMulti -x` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | MOD-02 | unit | `python -m pytest tests/test_commands.py::TestSetSpeedCommand -x` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | MOD-02 | unit | `python -m pytest tests/test_commands.py::TestSetSpeedCommandMulti -x` | ❌ W0 | ⬜ pending |
| 05-01-05 | 01 | 1 | MOD-03 | unit | `python -m pytest tests/test_commands.py::TestDeleteCommand -x` | ❌ W0 | ⬜ pending |
| 05-01-06 | 01 | 1 | MOD-03 | unit | `python -m pytest tests/test_commands.py::TestDeleteCommandBreak -x` | ❌ W0 | ⬜ pending |
| 05-01-07 | 01 | 1 | MOD-03 | unit | `python -m pytest tests/test_commands.py::TestDeleteCommandUndo -x` | ❌ W0 | ⬜ pending |
| 05-01-08 | 01 | 1 | MOD-04 | unit | `python -m pytest tests/test_commands.py::TestInsertCommand -x` | ❌ W0 | ⬜ pending |
| 05-01-09 | 01 | 1 | MOD-04 | unit | `python -m pytest tests/test_commands.py::TestInsertCommandChain -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | MOD-02 | unit | `python -m pytest tests/test_property_panel.py -x` | ✅ (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_commands.py` — stubs for MOD-01, MOD-02, MOD-03, MOD-04 (QUndoCommand undo/redo tests)
- [ ] `tests/test_edit_model.py` — extend with mutation method tests (apply_offset, set_speed, delete_points, insert_after)
- [ ] `tests/test_property_panel.py` — extend with editable widget tests (offset fields, speed/zone inputs, laser combo, action buttons)

*Existing infrastructure covers test framework and conftest.py — no new framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D view updates after offset | MOD-01 | OpenGL rendering requires visual inspection | Select point, apply offset, verify position change in 3D |
| Delete dialog UX | MOD-03 | QMessageBox button labels/behavior | Click Delete, verify Reconnect/Break/Cancel buttons work |
| Insert chaining workflow | MOD-04 | Multi-step user interaction | Select point, insert after, verify new point selected, apply again |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
