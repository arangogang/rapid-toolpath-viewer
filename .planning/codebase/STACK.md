# Technology Stack

**Analysis Date:** 2026-03-31

## Languages

**Primary:**
- Python 3.12.9 (runtime on dev machine) - requires `>=3.11` per `pyproject.toml`

**Secondary:**
- GLSL 3.30 Core - OpenGL shaders defined as string constants in `src/rapid_viewer/renderer/shaders.py`
- Batch script - `build.bat` for Windows build automation

## Runtime

**Environment:**
- CPython 3.12.9 on Windows 11 Pro
- OpenGL 3.3 Core Profile context (set in `src/rapid_viewer/main.py` via `QSurfaceFormat`)

**Package Manager:**
- uv (recommended in CLAUDE.md, no `uv.lock` file present)
- No lockfile detected - dependencies specified only in `pyproject.toml`

## Frameworks

**Core:**
- PyQt6 `>=6.10` - GUI framework, provides QMainWindow, QOpenGLWidget, QSyntaxHighlighter, signal/slot system
- PyOpenGL `>=3.1.10` - Raw OpenGL 3.3 Core Profile bindings (VBO/VAO/shader pipeline, no fixed-function)
- NumPy `>=1.26` - Vertex buffer construction, coordinate transforms, array math

**Testing:**
- pytest `>=9.0` - Test runner, configured in `pyproject.toml` `[tool.pytest.ini_options]`
- pytest-qt `>=4.4` - Qt widget testing support

**Build/Dev:**
- PyInstaller `>=6.0` - Bundles into single Windows `.exe` (spec file: `rapid_viewer.spec`)
- ruff - Linting and formatting (line-length: 100, configured in `pyproject.toml`)
- hatchling - Build backend (`[build-system]` in `pyproject.toml`)

## Key Dependencies

**Critical (runtime):**
- `PyQt6>=6.10` - Entire GUI framework; QOpenGLWidget hosts the 3D viewport
- `PyOpenGL>=3.1.10` - All rendering calls (GL_LINES, GL_POINTS, shader compilation)
- `PyOpenGL-accelerate>=3.1.10` - C-accelerated paths for PyOpenGL (must match PyOpenGL version exactly)
- `pyrr>=0.10.3` - 3D math: quaternion rotation, matrix44 creation (view/projection/MVP), arcball camera math
- `numpy>=1.26` - Vertex array construction, coordinate transforms, ray-cast picking math

**Infrastructure:**
- `PyInstaller>=6.0` - Distribution packaging (spec: `rapid_viewer.spec`, output: `dist/rapid_viewer.exe`)

## PyQt6 Modules Used

The application uses these specific PyQt6 submodules (relevant for PyInstaller hidden imports):
- `PyQt6.QtWidgets` - QMainWindow, QSplitter, QFileDialog, QMessageBox, QPlainTextEdit, QToolBar, QSlider, QComboBox, QLabel
- `PyQt6.QtGui` - QAction, QSurfaceFormat, QSyntaxHighlighter, QFont, QColor, QTextCharFormat, QTextCursor
- `PyQt6.QtCore` - Qt, QTimer, QObject, QRegularExpression, pyqtSignal
- `PyQt6.QtOpenGLWidgets` - QOpenGLWidget (3D viewport base class)

## Configuration

**Environment:**
- No `.env` files present - application has no external service dependencies
- No environment variables required at runtime
- OpenGL 3.3 Core Profile forced globally before QApplication creation (`src/rapid_viewer/main.py` lines 23-27)

**Build:**
- `pyproject.toml` - All project metadata, dependencies, pytest config, ruff config
- `rapid_viewer.spec` - PyInstaller spec with explicit hidden imports for PyOpenGL dynamic imports and PyQt6 plugins
- `build.bat` - Windows batch script that cleans `build/` and `dist/`, runs PyInstaller, verifies output

**PyInstaller Configuration (`rapid_viewer.spec`):**
- Entry point: `src/rapid_viewer/main.py`
- Console: disabled (GUI-only app)
- UPX compression: disabled (avoids antivirus false positives)
- Icon: `rapid_viewer.ico`
- Excluded packages: tkinter, matplotlib, scipy, PIL, IPython
- Hidden imports: all rapid_viewer submodules, PyQt6 modules, OpenGL modules, numpy

## Platform Requirements

**Development:**
- Python 3.11+ (3.12 recommended)
- Windows (primary target; no macOS/Linux testing indicated)
- GPU with OpenGL 3.3 Core Profile support
- uv package manager (recommended)

**Production:**
- Windows desktop (single `.exe` via PyInstaller, no Python installation needed)
- GPU with OpenGL 3.3 Core Profile support
- No network connectivity required (fully offline desktop app)

## Python Version Notes

- `pyproject.toml` specifies `requires-python = ">=3.11"`
- CLAUDE.md recommends avoiding Python 3.13 until C-extension dependency compatibility is confirmed
- Development machine runs Python 3.12.9

---

*Stack analysis: 2026-03-31*
