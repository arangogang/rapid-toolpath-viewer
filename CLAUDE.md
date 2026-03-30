<!-- GSD:project-start source:PROJECT.md -->
## Project

**ABB RAPID Toolpath Viewer**

ABB RAPID 로봇 프로그램 파일(.mod)을 불러와 툴패스를 3D로 시각화하는 Windows 데스크탑 애플리케이션이다. 로봇 엔지니어가 RAPID 코드를 실제 로봇에 올리기 전에 경로의 정확성을 검증하는 도구다.

**Core Value:** .mod 파일을 열면 즉시 3D 툴패스가 렌더링되고, 각 워크포인트를 클릭하면 해당 RAPID 코드 줄로 이동할 수 있어야 한다.

### Constraints

- **Tech Stack**: Python + PyQt6 + PyOpenGL — 빠른 구현, 사용자가 명시적 선택
- **Platform**: Windows 데스크탑 전용
- **Scope**: 코드 검증 뷰어 — 편집/시뮬레이션 기능 없음
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime | 3.11 for significant performance gains over 3.10; 3.12+ also fine. Avoid 3.13 until all C-extension deps confirm compatibility. |
| PyQt6 | 6.10.2 | GUI framework | User-specified constraint. Mature Qt6 bindings, QOpenGLWidget provides native OpenGL surface integration. GPL licensed (acceptable for internal tooling). |
| PyOpenGL | 3.1.10 | OpenGL bindings | User-specified constraint. Direct OpenGL API access, integrates with PyQt6's QOpenGLWidget. Use modern shader pipeline (OpenGL 3.3+), NOT fixed-function pipeline. |
| NumPy | >=1.26 | Math/arrays | Essential for vertex buffer construction, coordinate transforms, quaternion math. The backbone of all 3D data handling in Python. |
### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyOpenGL-accelerate | 3.1.10 | C-accelerated PyOpenGL paths | Always install alongside PyOpenGL. Provides 2-5x speedup for array operations and format handlers. |
| pyrr | 0.10.3 | 3D math (matrices, quaternions, vectors) | View/projection matrix construction, camera transforms, quaternion-based arcball rotation. NumPy-native, purpose-built for OpenGL pipelines. |
| numpy | >=1.26 | Array computation | Vertex buffers, coordinate arrays, robtarget data storage, batch transforms. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Project/dependency management | Faster than pip, lockfile support, reproducible builds. Use `uv init` + `uv add`. |
| ruff | Linting + formatting | Replaces flake8, black, isort in one tool. Configure in pyproject.toml. |
| pytest | Testing | Standard Python testing. Use pytest-qt for GUI widget tests. |
| pyinstaller | Windows executable packaging | Bundles Python + deps into .exe for distribution to robot engineers who don't have Python. |
## Installation
# Initialize project with uv
# Core dependencies
# Dev dependencies
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| PyOpenGL (raw) | moderngl 5.12.0 | If you want a cleaner API that wraps OpenGL 3.3 core profile. Fewer lines of code for VBO/VAO/shader setup. However, it adds an abstraction layer over what PyOpenGL already does, and PyQt6's QOpenGLWidget expects raw GL calls. Mixing moderngl's context with Qt's context requires care. Stick with PyOpenGL since it is the user's explicit choice and integrates naturally with QOpenGLWidget. |
| PyOpenGL (raw) | vispy 0.14+ | If building a scientific visualization dashboard. Vispy is high-level (scene graph, cameras, visuals built-in) but hides too much for a custom toolpath viewer. Its built-in camera controls are convenient but inflexible when you need custom interaction (e.g., step-through playback linked to code highlighting). Overkill abstraction for this project. |
| PyOpenGL (raw) | pyqtgraph 0.13+ | If 2D plotting is the primary need with some 3D. Its 3D system (GLViewWidget) is basic and not designed for custom rendering pipelines. Insufficient for toolpath visualization with line style differentiation and marker rendering. |
| PyOpenGL (raw) | pyvista + pyvistaqt | If working with complex mesh data (CAD, FEA, medical imaging). Built on VTK -- extremely heavyweight dependency (~500MB). Massive overkill for rendering lines and points. Also has known PyQt6 compatibility quirks (certain 6.6.x and 6.7.x versions are blacklisted). |
| PyOpenGL (raw) | Qt3D (PyQt6-3D) | If you want a scene-graph approach within Qt itself. Less community support, fewer examples, harder to debug. Raw OpenGL gives more control for this use case. |
| pyrr | PyGLM | If you need exact GLM (C++) parity. PyGLM is faster for bulk operations but pyrr is more Pythonic and sufficient for this project's scale. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| OpenGL fixed-function pipeline (glBegin/glEnd, glVertex, glLoadIdentity) | Deprecated since OpenGL 3.0 (2008). Will not work with OpenGL Core Profile contexts. PyQt6 defaults to Core Profile on many systems. Tutorials using this are 10+ years outdated. | Modern shader pipeline: write vertex/fragment shaders, use VBOs/VAOs. Target OpenGL 3.3 Core Profile. |
| PyQt5 | Legacy. PyQt6 is the current maintained version. Enum handling changed (e.g., `Qt.AlignLeft` became `Qt.AlignmentFlag.AlignLeft`). Mixing PyQt5 patterns into PyQt6 code causes subtle bugs. | PyQt6 6.10.x |
| PySide6 | Functionally equivalent to PyQt6 but user explicitly chose PyQt6. Mixing the two in the same project is impossible. Stick with the choice. | PyQt6 |
| matplotlib 3D (mplot3d) | Extremely slow for interactive 3D. No real-time orbit camera. Designed for static publication figures, not interactive toolpath viewers. | PyOpenGL with QOpenGLWidget |
| tkinter | No OpenGL integration without hacks. No modern widget set. | PyQt6 |
| abb_motion_program_exec | This is for *executing* motion programs on live ABB robots via Robot Web Services. It does NOT parse .mod files from disk. Different problem entirely. | Custom regex-based .mod parser |
## Architecture Decisions Embedded in Stack
### OpenGL Pipeline: Modern Shaders (OpenGL 3.3 Core)
- **Vertex shaders** for position transforms (model/view/projection matrices)
- **Fragment shaders** for coloring (line type differentiation, selection highlighting)
- **VBOs** (Vertex Buffer Objects) for geometry data
- **VAOs** (Vertex Array Objects) for binding state
### RAPID .mod File Parsing: Custom Regex Parser
### 3D Camera: Custom Arcball Implementation
- **Arcball rotation:** Map mouse drag to quaternion rotation on a virtual sphere
- **Pan:** Middle-mouse or Shift+drag translates the view
- **Zoom:** Scroll wheel adjusts distance or FOV
- **Implementation:** ~150-200 lines of Python using pyrr for matrix/quaternion math
- **Integration:** Override QOpenGLWidget.mousePressEvent/mouseMoveEvent/wheelEvent
## Stack Patterns
- Use `GL_LINES` or `GL_LINE_STRIP` primitives
- Dashed lines in modern OpenGL require a fragment shader that discards fragments based on distance along the line (no more `glLineStipple` in core profile)
- Alternative: render dashed lines as thin quads with texture
- Use `GL_POINTS` with `gl_PointSize` in vertex shader
- Or render small 3D shapes (cubes, spheres) at each target position for better visibility
- Color-based picking: render each point with a unique color to an offscreen FBO, read pixel at mouse position
- Simpler: ray-cast from mouse through projection, find nearest point (sufficient for point-cloud-like data)
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| PyQt6 6.10.x | Python 3.9+ | Python 3.11+ recommended for performance |
| PyOpenGL 3.1.10 | PyQt6 6.10.x | Both use the same OpenGL context. No conflicts. |
| PyOpenGL-accelerate 3.1.10 | PyOpenGL 3.1.10 | Must match PyOpenGL version exactly |
| pyrr 0.10.3 | NumPy >=1.26 | Pure Python + NumPy, no binary compat issues |
| pyinstaller 6.x | PyQt6 6.10.x | Known to work. Use `--hidden-import` for PyOpenGL plugins if needed. |
## Sources
- [PyQt6 on PyPI](https://pypi.org/project/PyQt6/) -- version 6.10.2 confirmed, Jan 2026 release
- [PyOpenGL on PyPI](https://pypi.org/project/PyOpenGL/) -- version 3.1.10 confirmed, Aug 2025 release
- [moderngl on PyPI](https://pypi.org/project/moderngl/) -- version 5.12.0, evaluated and rejected for this project
- [pyrr on PyPI](https://pypi.org/project/pyrr/) -- version 0.10.3, 3D math utilities
- [Qt Forum: Shader-based OpenGL in PyQt6](https://forum.qt.io/topic/137468/a-few-basic-changes-in-pyqt6-and-pyside6-regarding-shader-based-opengl-graphics) -- confirmed Core Profile requirements
- [ABB RAPID Technical Reference](https://library.e.abb.com/public/688894b98123f87bc1257cc50044e809/Technical%20reference%20manual_RAPID_3HAC16581-1_revJ_en.pdf) -- robtarget data type specification
- [GERTY: RobTarget documentation](https://batpartners.github.io/en/datatype/DataType-RobTarget/) -- robtarget structure reference
- [abb_motion_program_exec](https://pypi.org/project/abb-motion-program-exec/) -- evaluated, not suitable for file parsing
- [pyvistaqt on PyPI](https://pypi.org/project/pyvistaqt/) -- evaluated, too heavyweight
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
