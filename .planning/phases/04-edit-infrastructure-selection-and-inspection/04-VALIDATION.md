---
phase: 4
slug: edit-infrastructure-selection-and-inspection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-qt 4.x |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -v --timeout=30` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -v --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | EDIT-01 | unit | `uv run pytest tests/test_edit_model.py -x -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | EDIT-02 | unit | `uv run pytest tests/test_edit_model.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | SEL-01 | unit | `uv run pytest tests/test_selection_state.py -x -q` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | SEL-02 | unit | `uv run pytest tests/test_selection_state.py -x -q` | ❌ W0 | ⬜ pending |
| 04-03-01 | 03 | 2 | INSP-01 | unit | `uv run pytest tests/test_property_panel.py -x -q` | ❌ W0 | ⬜ pending |
| 04-04-01 | 04 | 2 | SEL-01 | visual | manual | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_edit_model.py` — stubs for EDIT-01, EDIT-02
- [ ] `tests/test_selection_state.py` — stubs for SEL-01, SEL-02
- [ ] `tests/test_property_panel.py` — stubs for INSP-01

*Existing pytest + pytest-qt infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Selection color feedback in 3D | SEL-01 | OpenGL rendering requires visual inspection | Load test.mod, click waypoint, verify cyan highlight |
| Multi-select Shift/Ctrl in 3D | SEL-02 | Mouse modifier interaction requires manual test | Shift+click 3 points, verify all cyan |
| Property panel layout placement | INSP-01 | Widget layout requires visual check | Verify panel appears below code panel |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
