---
phase: quick
plan: 260330-nz9
subsystem: packaging
tags: [pyinstaller, windows, build, packaging]
dependency_graph:
  requires: [src/rapid_viewer/main.py, PyQt6, numpy]
  provides: [dist/rapid_viewer.exe, rapid_viewer.spec, build.bat]
  affects: [distribution]
tech_stack:
  added: [pyinstaller>=6.0]
  patterns: [PyInstaller one-file EXE, PyQt6 plugin collection via collect_data_files]
key_files:
  created:
    - rapid_viewer.spec
    - build.bat
  modified:
    - pyproject.toml
decisions:
  - "Used python -m PyInstaller instead of uv run pyinstaller (uv not in PATH)"
  - "build.bat uses python -m PyInstaller for portability on systems without uv"
  - "UPX disabled (upx=False) to prevent antivirus false positives"
  - "console=False to suppress console window in GUI app"
metrics:
  duration: "5 minutes"
  completed: "2026-03-30"
  tasks_completed: 2
  tasks_total: 3
  status: "checkpoint:human-verify"
---

# Quick Task 260330-nz9: PyInstaller Windows Build Summary

**One-liner:** PyInstaller 6.19.0 one-file EXE build for rapid_viewer with PyQt6 plugin collection, src/ pathex, and OpenGL stubs ready for future activation.

## Tasks Completed

| # | Task | Commit | Result |
|---|------|--------|--------|
| 1 | Add pyinstaller>=6.0 to dev deps | 5aa8a8e | pyinstaller 6.19.0 installed |
| 2 | Write rapid_viewer.spec + build.bat, run PyInstaller | 41d050b | dist/rapid_viewer.exe (73MB) created |
| 3 | human-verify checkpoint | — | AWAITING |

## Build Output

```
dist/rapid_viewer.exe  73MB
Build time: ~60 seconds
PyInstaller: 6.19.0
Python: 3.12.9
Platform: Windows-11-10.0.26200
```

## Warnings (non-blocking)

26 "Library not found" warnings for optional Qt3D, WebEngine, and SCXML DLLs. These are not needed for this application (they're Qt premium/optional features). The app will run correctly without them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocked] uv not found in PATH**
- **Found during:** Task 1 (uv add --dev pyinstaller command failed)
- **Issue:** `uv: command not found` — uv is not installed or not in the shell PATH in this environment
- **Fix:** Used `python -m pip install "pyinstaller>=6.0"` for installation, and `python -m PyInstaller` in build.bat
- **Files modified:** build.bat (uses `python -m PyInstaller` instead of `uv run pyinstaller`)
- **Impact:** Functionally identical result. pyproject.toml was still updated with the dependency declaration. Users running build.bat need Python in PATH (standard on Windows with Python installer).

## Known Stubs

None. This task only creates build infrastructure, not application features.

## Self-Check

- [x] rapid_viewer.spec exists
- [x] build.bat exists
- [x] dist/rapid_viewer.exe exists (73MB)
- [x] pyproject.toml has pyinstaller>=6.0 in dev section
- [x] Commits 5aa8a8e and 41d050b exist

## Self-Check: PASSED
