---
phase: 2
slug: 3d-viewer-and-camera
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-qt 4.4 |
| **Config file** | pyproject.toml (testpaths=["tests"], pythonpath=["src"]) |
| **Quick run command** | `python -m pytest tests/ -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 02-01-01 | 01 | 1 | REND-01, REND-02 | import + smoke | `python -c "from rapid_viewer.renderer.toolpath_renderer import ToolpathRenderer"` | ⬜ pending |
| 02-01-02 | 01 | 1 | REND-03 | import + smoke | `python -c "from rapid_viewer.renderer.shaders import ShaderProgram"` | ⬜ pending |
| 02-02-01 | 02 | 2 | CAM-01, CAM-02, CAM-03 | import + unit | `python -m pytest tests/test_camera.py -q` | ⬜ pending |
| 02-02-02 | 02 | 2 | REND-05 | import + smoke | `python -c "from rapid_viewer.renderer.axes_renderer import AxesRenderer"` | ⬜ pending |
| 02-03-01 | 03 | 3 | REND-01..05, CAM-01..03 | integration | `python -m pytest tests/test_viewer_widget.py -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_camera.py` — unit tests for arcball camera math (orbit, pan, zoom)
- [ ] `tests/test_viewer_widget.py` — pytest-qt smoke tests for ToolpathViewerWidget
- [ ] `PyOpenGL>=3.1.10`, `PyOpenGL-accelerate>=3.1.10`, `pyrr>=0.10.3` installed

*Existing infrastructure (pytest, pytest-qt) covers base needs; new test files required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 3D toolpath renders visually correct | REND-01 | OpenGL output requires visual inspection | Load simple.mod, confirm colored lines appear at correct 3D positions |
| MoveL/MoveJ visual distinction | REND-02 | Solid vs dashed line style is visual | Confirm MoveL=solid, MoveJ=dashed in rendered view |
| MoveC arc curve | REND-03 | Arc shape requires visual check | Load movecircular.mod, confirm smooth arc between waypoints |
| Waypoint markers visible | REND-05 | Marker visibility is visual | Confirm dots/points at each robtarget position |
| Orbit camera smooth | CAM-01 | Responsiveness is perceptual | Left-drag scene, confirm smooth rotation without jitter |
| Pan and zoom | CAM-02, CAM-03 | Interaction feel is perceptual | Middle-drag to pan, scroll to zoom |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
