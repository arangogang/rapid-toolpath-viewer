---
phase: 3
slug: playback-code-panel-and-linking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-qt 4.4+ |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `python -m pytest tests/ -x --timeout=10` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x --timeout=10`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 0 | PLAY-01/02/03 | unit | `python -m pytest tests/test_playback_state.py -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 0 | PLAY-05/06/07 | unit | `python -m pytest tests/test_playback_toolbar.py -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 0 | CODE-01/03 | unit | `python -m pytest tests/test_code_panel.py -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 0 | CODE-02 | unit | `python -m pytest tests/test_rapid_highlighter.py -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 0 | LINK-01/02 | integration | `python -m pytest tests/test_linking.py -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 1 | PARS-08 | unit | `python -m pytest tests/test_parser.py::test_proc_filtering -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 2 | PLAY-01/02 | integration | `python -m pytest tests/test_playback_state.py -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 2 | CODE-01/02/03 | integration | `python -m pytest tests/test_code_panel.py tests/test_rapid_highlighter.py -x` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 2 | LINK-01/02 | integration | `python -m pytest tests/test_linking.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_playback_state.py` — stubs for PLAY-01, PLAY-02, PLAY-03
- [ ] `tests/test_playback_toolbar.py` — stubs for PLAY-05, PLAY-06, PLAY-07
- [ ] `tests/test_code_panel.py` — stubs for CODE-01, CODE-03
- [ ] `tests/test_rapid_highlighter.py` — stubs for CODE-02
- [ ] `tests/test_linking.py` — stubs for LINK-01, LINK-02
- [ ] `tests/fixtures/multiproc.mod` — test fixture with multiple PROCs for PARS-08

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Current waypoint highlighted in 3D view | PLAY-04 | GL rendering requires visual inspection | Step through waypoints; current point should appear larger/distinct color |
| TCP orientation triads rendered at waypoints | REND-04 | GL rendering requires visual inspection | Load .mod file; small XYZ triads should appear at each waypoint position |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
