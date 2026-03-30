---
phase: 1
slug: parser-and-file-loading
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | pytest.ini or pyproject.toml (Wave 0 creates) |
| **Quick run command** | `pytest tests/test_parser.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_parser.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| FILE-01 | file_dialog | 1 | FILE-01 | manual | — | — | ⬜ pending |
| FILE-02 | file_dialog | 1 | FILE-02 | manual | — | — | ⬜ pending |
| PARS-01 | parser_core | 1 | PARS-01 | unit | `pytest tests/test_parser.py::test_movel -v` | ❌ W0 | ⬜ pending |
| PARS-02 | parser_core | 1 | PARS-02 | unit | `pytest tests/test_parser.py::test_movej -v` | ❌ W0 | ⬜ pending |
| PARS-03 | parser_core | 1 | PARS-03 | unit | `pytest tests/test_parser.py::test_movec -v` | ❌ W0 | ⬜ pending |
| PARS-04 | parser_core | 1 | PARS-04 | unit | `pytest tests/test_parser.py::test_moveabsj -v` | ❌ W0 | ⬜ pending |
| PARS-05 | parser_core | 1 | PARS-05 | unit | `pytest tests/test_parser.py::test_robtarget -v` | ❌ W0 | ⬜ pending |
| PARS-06 | parser_core | 1 | PARS-06 | unit | `pytest tests/test_parser.py::test_multiline -v` | ❌ W0 | ⬜ pending |
| PARS-07 | parser_core | 1 | PARS-07 | unit | `pytest tests/test_parser.py::test_line_numbers -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — test package init
- [ ] `tests/test_parser.py` — stubs for PARS-01 through PARS-07
- [ ] `tests/conftest.py` — shared fixtures (sample .mod content strings)
- [ ] `pytest` install — `pip install pytest`

*Wave 0 must create test stubs before parser implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| File dialog opens with .mod filter | FILE-01 | Qt GUI interaction | Launch app, click Open, verify filter shows "RAPID Module (*.mod)" |
| Title bar updates after file load | FILE-02 | Qt GUI state | Load any .mod file, verify window title shows filename |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
