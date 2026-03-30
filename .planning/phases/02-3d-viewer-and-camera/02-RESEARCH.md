# Phase 2: 3D Viewer and Camera - Research

**Researched:** 2026-03-30
**Domain:** PyQt6 QOpenGLWidget, OpenGL 3.3 Core Profile, pyrr 3D math, arcball camera
**Confidence:** HIGH

## Summary

Phase 2 builds the interactive 3D rendering layer on top of the Phase 1 parser. The core challenge is standing up a modern OpenGL 3.3 Core Profile pipeline inside a PyQt6 `QOpenGLWidget`, loading parsed `ParseResult` data into GPU-side VBOs, and driving the scene with an arcball camera. Nothing in this phase touches Qt fixed-function or PyOpenGL immediate mode -- both are banned by the stack decision.

The most technically subtle problems are: (1) dashed lines for MoveJ segments require a fragment shader that discards fragments by distance -- `glLineStipple` does not exist in Core Profile; (2) MoveC arc segments require a CPU-side geometry step to tessellate the three-point arc into a polyline before uploading to the GPU; (3) the arcball camera accumulates rotation as a quaternion, not as Euler angles, to avoid gimbal lock; and (4) PyQt6's import paths for OpenGL classes changed from PyQt5 -- `QOpenGLWidget` is in `PyQt6.QtOpenGLWidgets`, not `PyQt6.QtWidgets`.

**Primary recommendation:** Build the OpenGL widget as a standalone `ToolpathGLWidget(QOpenGLWidget)` class; keep the `ParseResult`-to-GPU geometry conversion in a separate `GeometryBuilder` module. Use raw PyOpenGL calls (`OpenGL.GL.*`) rather than Qt wrapper classes (`QOpenGLBuffer`) to keep the code portable and debuggable against standard OpenGL tutorials.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REND-01 | Toolpath rendered in 3D: MoveL=solid, MoveJ=dashed, MoveC=arc | VBO/VAO with two shader programs (solid + dashed); MoveC arc tessellation via 3-point circumcircle |
| REND-02 | Waypoint markers at each robtarget position | GL_POINTS with gl_PointSize in vertex shader, or small billboard quad per point |
| REND-03 | XYZ coordinate axes indicator in viewport corner | Separate 6-vertex VAO (3 axes, 2 verts each), drawn after main scene in a fixed small viewport region |
| REND-05 | OpenGL 3.3 Core Profile + VBO/VAO architecture | QSurfaceFormat set to (3,3) CoreProfile before QApplication; all geometry in VBOs |
| CAM-01 | Mouse left-drag orbits the 3D view (arcball rotation) | mousePressEvent + mouseMoveEvent -> quaternion accumulation via pyrr |
| CAM-02 | Scroll wheel zooms in/out | wheelEvent -> adjust camera distance or FOV |
| CAM-03 | Mouse middle-drag pans the view | mousePressEvent (middle button) + mouseMoveEvent -> screen-space translation vector |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech Stack**: Python + PyQt6 + PyOpenGL -- locked, no alternatives
- **OpenGL**: 3.3 Core Profile ONLY -- no `glBegin/glEnd`, no `glLineStipple`, no `glLoadIdentity`, no fixed-function pipeline
- **VBO/VAO**: mandatory architecture -- no immediate mode rendering
- **pyrr**: 3D math (matrices, quaternions) -- use for all MVP construction and arcball rotation
- **Platform**: Windows desktop only
- **Scope**: Viewer only -- no editing
- **GSD Workflow**: All code changes through GSD commands

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.9 | Runtime | Already installed |
| PyQt6 | 6.10.2 | `QOpenGLWidget`, event loop, mouse events | User-specified; `QOpenGLWidget` provides OpenGL surface integrated with Qt event system |
| PyOpenGL | 3.1.10 | OpenGL 3.3 Core API bindings | User-specified; direct `GL.*` calls, integrates with Qt's OpenGL context |
| PyOpenGL-accelerate | 3.1.10 | C-extension speedup for PyOpenGL array paths | Always install alongside PyOpenGL -- 2-5x speedup on buffer uploads |
| pyrr | 0.10.3 | Matrix44, Quaternion, look_at, perspective | NumPy-native 3D math; purpose-built for OpenGL matrix/quaternion pipelines |
| numpy | 2.3.5 | Float32 vertex arrays, arc tessellation math | Vertex buffers must be `np.float32`; all geometry built in NumPy |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Geometry unit tests | Test arc tessellation, VBO data layout, camera math |
| pytest-qt | 4.5.0 | Widget lifecycle tests | Test `ToolpathGLWidget` initialization with real Qt context |

### Not Yet Needed in Phase 2

| Library | Why Not Yet |
|---------|-------------|
| pyinstaller | Phase 3+ packaging step |

### Installation

PyOpenGL and pyrr are not yet installed. Must install before any Phase 2 task runs:

```bash
pip install PyOpenGL==3.1.10 PyOpenGL-accelerate==3.1.10 pyrr==0.10.3
```

Also add to `pyproject.toml` dependencies:

```toml
dependencies = [
    "PyQt6>=6.10",
    "numpy>=1.26",
    "PyOpenGL>=3.1.10",
    "PyOpenGL-accelerate>=3.1.10",
    "pyrr>=0.10.3",
]
```

**Version verification (2026-03-30):**
- PyOpenGL 3.1.10 -- confirmed available on PyPI (published Aug 2025)
- PyOpenGL-accelerate 3.1.10 -- confirmed, cp312-win_amd64 wheel available
- pyrr 0.10.3 -- confirmed available on PyPI

---

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)

```
src/
  rapid_viewer/
    ui/
      main_window.py          # Existing -- add GL widget embedding
      toolpath_gl_widget.py   # NEW: ToolpathGLWidget(QOpenGLWidget)
    renderer/
      __init__.py             # NEW package
      geometry_builder.py     # NEW: ParseResult -> numpy vertex arrays
      shaders.py              # NEW: vertex/fragment shader source strings
      camera.py               # NEW: ArcballCamera state + matrices
```

### Pattern 1: QSurfaceFormat Setup (CRITICAL -- must happen before QApplication)

**What:** Force OpenGL 3.3 Core Profile globally. If this is omitted, Qt may give a compatibility context where deprecated APIs silently work, hiding bugs until deployment.

**When to use:** In `main.py`, before `QApplication(sys.argv)`.

```python
# Source: Qt documentation https://doc.qt.io/qt-6/qopenglwidget.html
from PyQt6.QtGui import QSurfaceFormat

fmt = QSurfaceFormat()
fmt.setVersion(3, 3)
fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
fmt.setDepthBufferSize(24)
QSurfaceFormat.setDefaultFormat(fmt)

# THEN create QApplication
app = QApplication(sys.argv)
```

### Pattern 2: QOpenGLWidget Lifecycle

**What:** Three virtual methods implement the rendering pipeline.

**Import path (PyQt6-specific):**
```python
# Source: Qt Forum https://forum.qt.io/topic/137468/...
from PyQt6.QtOpenGLWidgets import QOpenGLWidget   # NOT QtWidgets
from PyQt6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram
```

**Lifecycle skeleton:**

```python
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import numpy as np

class ToolpathGLWidget(QOpenGLWidget):
    def initializeGL(self):
        """Called once -- context is current. Compile shaders, create VAOs/VBOs."""
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.1, 0.1, 0.15, 1.0)
        self._init_shaders()
        self._init_geometry()

    def resizeGL(self, w: int, h: int):
        """Called on window resize. Update viewport and projection matrix."""
        glViewport(0, 0, w, h)
        aspect = w / max(h, 1)
        self._camera.set_aspect(aspect)

    def paintGL(self):
        """Called each frame. Bind shader, upload uniforms, draw."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self._draw_toolpath()
        self._draw_markers()
        self._draw_axes_indicator()

    def update_scene(self, parse_result):
        """Called from MainWindow after file load. Rebuild VBOs."""
        self.makeCurrent()          # context must be current outside lifecycle methods
        self._rebuild_geometry(parse_result)
        self.doneCurrent()
        self.update()               # schedule repaint (not repaint() directly)
```

### Pattern 3: VBO/VAO Setup

**What:** Upload vertex data to GPU. Each attribute (position, color) goes into a VBO bound to a VAO.

**Data layout:** Interleaved per-vertex data `[x, y, z, r, g, b]` as `np.float32` in a single VBO. Stride = 6 floats = 24 bytes.

```python
# Source: PyOpenGL documentation + standard OpenGL 3.3 practice
from OpenGL.GL import *
import numpy as np
import ctypes

def create_vao_vbo(vertex_data: np.ndarray) -> tuple[int, int]:
    """
    vertex_data: shape (N, 6) float32 -- [x, y, z, r, g, b] per vertex
    Returns (vao_id, vbo_id)
    """
    vao = glGenVertexArrays(1)
    vbo = glGenBuffers(1)

    glBindVertexArray(vao)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)

    data = vertex_data.astype(np.float32)
    glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)

    stride = 6 * 4  # 6 floats * 4 bytes

    # Attribute 0: position (x, y, z)
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))

    # Attribute 1: color (r, g, b)
    glEnableVertexAttribArray(1)
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(3 * 4))

    glBindVertexArray(0)
    return vao, vbo

def update_vbo(vbo: int, vertex_data: np.ndarray):
    """Re-upload VBO data after geometry changes (e.g. file reload)."""
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    data = vertex_data.astype(np.float32)
    glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_DYNAMIC_DRAW)
    glBindBuffer(GL_ARRAY_BUFFER, 0)
```

### Pattern 4: Model-View-Projection with pyrr

**What:** Construct the MVP matrix from camera state and pass it as a uniform.

```python
# Source: pyrr docs https://github.com/adamlwgriffiths/Pyrr/blob/master/pyrr/matrix44.py
import pyrr
import numpy as np

class ArcballCamera:
    def __init__(self):
        self._rotation = pyrr.Quaternion()    # identity
        self._distance = 1000.0               # mm from origin
        self._pan = np.zeros(3, dtype=np.float32)
        self._fov = 45.0
        self._aspect = 1.0
        self._near = 1.0
        self._far = 100000.0                  # RAPID coords in mm, paths can span meters

    def view_matrix(self) -> np.ndarray:
        """Returns 4x4 view matrix as float32."""
        rot_matrix = pyrr.Matrix44.create_from_quaternion(self._rotation)
        eye = rot_matrix @ np.array([0, 0, self._distance, 1.0])
        eye = eye[:3] + self._pan
        target = self._pan
        up = (rot_matrix @ np.array([0, 1, 0, 0]))[:3]
        return pyrr.matrix44.create_look_at(eye, target, up, dtype=np.float32)

    def projection_matrix(self) -> np.ndarray:
        """Returns 4x4 projection matrix as float32."""
        return pyrr.matrix44.create_perspective_projection(
            self._fov, self._aspect, self._near, self._far, dtype=np.float32
        )

    def mvp(self) -> np.ndarray:
        """Full MVP (model is identity for toolpath scene)."""
        return self.projection_matrix() @ self.view_matrix()

# Upload uniform:
mvp = camera.mvp()
loc = glGetUniformLocation(shader_program, "u_mvp")
glUniformMatrix4fv(loc, 1, GL_FALSE, mvp.flatten())
```

### Pattern 5: Solid Line Shader (MoveL)

**Vertex shader:**
```glsl
#version 330 core
// Source: standard OpenGL 3.3 VBO pattern

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;

uniform mat4 u_mvp;

out vec3 vColor;

void main() {
    gl_Position = u_mvp * vec4(aPos, 1.0);
    vColor = aColor;
}
```

**Fragment shader:**
```glsl
#version 330 core

in vec3 vColor;
out vec4 fragColor;

void main() {
    fragColor = vec4(vColor, 1.0);
}
```

**Draw call:**
```python
glBindVertexArray(solid_vao)
glDrawArrays(GL_LINES, 0, solid_vertex_count)
```

### Pattern 6: Dashed Line Shader (MoveJ)

**What:** No `glLineStipple` in Core Profile. Use a fragment shader that discards fragments based on accumulated distance along the line.

**Two approaches:**

**Option A -- NDC-space distance (GL_LINES, simpler):** Compute distance between start/end NDC positions in the fragment shader. Works for separate line segments (each pair is one segment).

**Option B -- Pre-computed distance attribute (GL_LINE_STRIP, more accurate):** CPU computes cumulative path distance per vertex; passes it as a float attribute; fragment shader discards by `fract(dist)`. More accurate because distance is in world units, not screen pixels.

**Recommendation: Use Option A for MoveJ** -- each MoveJ segment is a separate start-to-end segment (GL_LINES, not GL_LINE_STRIP), so NDC-space distance works well and requires no extra CPU math.

```glsl
// Vertex shader -- dashed lines
#version 330 core
// Source: https://rabbid76.github.io/graphics-snippets/documentation/dashed_line_shader.html

layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;

uniform mat4 u_mvp;

flat out vec3 vStartPos;   // flat = no interpolation -- passes start vertex NDC to all frags
out vec3 vPos;
out vec3 vColor;

void main() {
    vec4 clip = u_mvp * vec4(aPos, 1.0);
    gl_Position = clip;
    vPos = clip.xyz / clip.w;
    vStartPos = vPos;
    vColor = aColor;
}
```

```glsl
// Fragment shader -- dashed lines
#version 330 core
// Source: https://rabbid76.github.io/graphics-snippets/documentation/dashed_line_shader.html

flat in vec3 vStartPos;
in vec3 vPos;
in vec3 vColor;

out vec4 fragColor;

uniform vec2  u_resolution;   // viewport size in pixels
uniform float u_dashSize;     // e.g. 10.0 pixels
uniform float u_gapSize;      // e.g. 6.0 pixels

void main() {
    vec2 dir = (vPos.xy - vStartPos.xy) * u_resolution / 2.0;
    float dist = length(dir);
    if (fract(dist / (u_dashSize + u_gapSize)) > u_dashSize / (u_dashSize + u_gapSize))
        discard;
    fragColor = vec4(vColor, 1.0);
}
```

**Critical: the `flat` qualifier on `vStartPos`** is essential. Without it, the start position would be interpolated, making it useless as a fixed reference.

### Pattern 7: MoveC Arc Tessellation (CPU-side geometry)

**What:** MoveC defines a circular arc through three points: the previous move's endpoint (start), the `circle_point` (via), and the `target` (end). The renderer must convert this to a polyline of N points.

**Algorithm (3-point circumcircle):**

```python
# Source: derived from https://meshlogic.github.io/posts/jupyter/curve-fitting/
# and standard 3D geometry (circumcircle of triangle in 3D)
import numpy as np

def tessellate_arc(
    start: np.ndarray,      # shape (3,) -- previous move's endpoint
    via: np.ndarray,        # shape (3,) -- MoveC circle_point.pos
    end: np.ndarray,        # shape (3,) -- MoveC target.pos
    n_segments: int = 32,
) -> np.ndarray:
    """
    Returns (N+1, 3) array of points along the circular arc from start to end
    passing through via. N = n_segments.

    If points are collinear (degenerate arc), falls back to a straight line.
    """
    # 1. Plane normal from cross product of edge vectors
    v1 = via - start
    v2 = end - start
    normal = np.cross(v1, v2)
    norm_len = np.linalg.norm(normal)
    if norm_len < 1e-6:
        # Collinear fallback: straight line start -> end
        return np.linspace(start, end, n_segments + 1)
    normal = normal / norm_len

    # 2. Circumcenter of triangle (start, via, end)
    # Use the formula: C = start + s*(v1) + t*(v2) where s,t solve the system
    # This gives the circumcenter in 3D
    ax, ay = np.dot(v1, v1), np.dot(v1, v2)
    bx, by = np.dot(v1, v2), np.dot(v2, v2)
    cx = np.dot(v1, v1) / 2
    cy = np.dot(v2, v2) / 2
    det = ax * by - bx * bx
    if abs(det) < 1e-10:
        return np.linspace(start, end, n_segments + 1)
    s = (cx * by - cy * bx) / det
    t = (ax * cy - bx * cx) / det
    center = start + s * v1 + t * v2
    radius = np.linalg.norm(start - center)

    # 3. Parametric arc
    u = (start - center) / np.linalg.norm(start - center)
    v_perp = np.cross(normal, u)

    # Angle from start to end (signed, going through via)
    start_angle = 0.0
    via_angle = np.arctan2(
        np.dot(via - center, v_perp),
        np.dot(via - center, u)
    )
    end_angle = np.arctan2(
        np.dot(end - center, v_perp),
        np.dot(end - center, u)
    )

    # Ensure arc goes through via (not the reflex arc)
    # Normalize end_angle relative to via_angle
    if via_angle < 0:
        via_angle += 2 * np.pi
    if end_angle < via_angle:
        end_angle += 2 * np.pi

    angles = np.linspace(start_angle, end_angle, n_segments + 1)
    points = (
        center[:, np.newaxis]
        + radius * np.cos(angles) * u[:, np.newaxis]
        + radius * np.sin(angles) * v_perp[:, np.newaxis]
    ).T  # shape (N+1, 3)
    return points
```

**Important ABB MoveC geometry facts:**
- ABB's MoveC error "50063 circle uncertain" fires when circle_point is too close to start or end (< ~1mm), or when the arc exceeds 240 degrees. The tessellator should handle degenerate cases gracefully with a straight-line fallback.
- The robot's TCP starts from the previous move's endpoint -- not from `circle_point`. The `circle_point` is only a via-point that shapes the arc.

### Pattern 8: Waypoint Markers

**What:** Render a visible marker at each robtarget position.

**Option A -- `GL_POINTS` with `gl_PointSize`:** Simple, cheap. Point sprites are square by default; can be rounded with a fragment shader distance check. Glitches at oblique angles on some drivers.

**Option B -- Small billboard (2 triangles, always face camera):** More robust visibility. Requires computing the camera right/up vectors per frame.

**Recommendation: GL_POINTS with fragment shader circle discard.** Simplest implementation, sufficient for Phase 2. Phase 3 can upgrade to billboard if needed.

```glsl
// Vertex shader addition for markers
gl_PointSize = u_point_size;   // uniform, e.g. 8.0
```

```glsl
// Fragment shader for round markers
void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (dot(coord, coord) > 0.25)  // 0.5 * 0.5
        discard;
    fragColor = vec4(u_marker_color, 1.0);
}
```

```python
# Requires enabling point size from shader
glEnable(GL_PROGRAM_POINT_SIZE)
```

### Pattern 9: XYZ Axes Indicator

**What:** A small fixed-size axes triad (X=red, Y=green, Z=blue) rendered in a corner of the viewport, rotated with the camera but not translated/zoomed.

**Implementation:** After drawing the main scene, set a small viewport in the corner, then render the 6-vertex axes VAO using only the rotation component of the view matrix (no translation, no perspective zoom effect):

```python
def _draw_axes_indicator(self):
    w, h = self.width(), self.height()
    size = 80  # pixels
    padding = 10
    glViewport(padding, padding, size, size)

    # Axes MVP: rotation only (no translation, orthographic-ish)
    rot_only = pyrr.Matrix44.create_from_quaternion(self._camera.rotation)
    ortho = pyrr.matrix44.create_orthogonal_projection(
        -1.5, 1.5, -1.5, 1.5, -10, 10, dtype=np.float32
    )
    axes_mvp = ortho @ rot_only
    glUniformMatrix4fv(axes_mvp_loc, 1, GL_FALSE, axes_mvp.flatten())

    glBindVertexArray(self._axes_vao)
    glDrawArrays(GL_LINES, 0, 6)  # 3 axes * 2 verts

    # Restore full viewport
    glViewport(0, 0, w, h)
```

**Axes geometry (3 unit-length lines from origin):**

```python
axes_verts = np.array([
    # X axis -- red
    0, 0, 0,  1, 0, 0,   # start: origin, color red
    1, 0, 0,  1, 0, 0,   # end: +X, color red
    # Y axis -- green
    0, 0, 0,  0, 1, 0,
    0, 1, 0,  0, 1, 0,
    # Z axis -- blue
    0, 0, 0,  0, 0, 1,
    0, 0, 1,  0, 0, 1,
], dtype=np.float32).reshape(-1, 6)
```

### Pattern 10: Arcball Camera (Mouse Controls)

**What:** Left-drag rotates, middle-drag pans, scroll zooms.

**Arcball math:** Map mouse position to a point on a unit sphere; the rotation is the quaternion that rotates the start sphere point to the end sphere point.

```python
# Source: Ken Shoemake arcball algorithm (1992), standard implementation
import pyrr
import numpy as np

class ArcballCamera:
    def __init__(self):
        self._rotation = pyrr.Quaternion()   # accumulated rotation
        self._distance = 1000.0              # camera distance from target
        self._pan_offset = np.zeros(3, dtype=np.float32)
        self._fov = 45.0
        self._aspect = 1.0

    def _screen_to_sphere(self, x: float, y: float, w: float, h: float) -> np.ndarray:
        """Map mouse (x,y) in pixel coords to a point on the unit arcball sphere.
        Returns normalized 3D vector."""
        sx = (2.0 * x - w) / w
        sy = (h - 2.0 * y) / h
        d2 = sx * sx + sy * sy
        if d2 <= 1.0:
            sz = np.sqrt(1.0 - d2)
        else:
            n = np.sqrt(d2)
            sx, sy, sz = sx / n, sy / n, 0.0
        return np.array([sx, sy, sz], dtype=np.float64)

    def orbit_start(self, x: float, y: float, w: float, h: float):
        self._orbit_start_vec = self._screen_to_sphere(x, y, w, h)
        self._orbit_start_rot = pyrr.Quaternion(self._rotation)

    def orbit_update(self, x: float, y: float, w: float, h: float):
        v1 = self._orbit_start_vec
        v2 = self._screen_to_sphere(x, y, w, h)
        dot = np.clip(np.dot(v1, v2), -1.0, 1.0)
        axis = np.cross(v1, v2)
        axis_len = np.linalg.norm(axis)
        if axis_len < 1e-6:
            return
        axis = axis / axis_len
        angle = np.arccos(dot)
        # delta quaternion from this frame's drag
        delta = pyrr.Quaternion.from_axis(axis, angle * 2.0)
        self._rotation = pyrr.Quaternion(
            (delta * self._orbit_start_rot).normalized
        )

    def pan_start(self, x: float, y: float):
        self._pan_start_mouse = np.array([x, y], dtype=np.float32)
        self._pan_start_offset = self._pan_offset.copy()

    def pan_update(self, x: float, y: float, w: float, h: float):
        dx = (x - self._pan_start_mouse[0]) / w
        dy = (y - self._pan_start_mouse[1]) / h
        # Pan in camera-space right/up directions, scaled by distance
        pan_speed = self._distance * 2.0
        # Camera right = first row of rotation matrix; up = second row
        rot_mat = pyrr.Matrix44.create_from_quaternion(self._rotation)
        right = rot_mat[0, :3]
        up = rot_mat[1, :3]
        self._pan_offset = (
            self._pan_start_offset
            - right * dx * pan_speed
            + up * dy * pan_speed
        )

    def zoom(self, delta: float):
        """delta > 0 = zoom in (reduce distance), delta < 0 = zoom out."""
        factor = 1.0 - delta * 0.1
        self._distance = max(10.0, self._distance * factor)

    def set_aspect(self, aspect: float):
        self._aspect = aspect

    @property
    def rotation(self) -> pyrr.Quaternion:
        return self._rotation
```

**Qt mouse event integration:**

```python
def mousePressEvent(self, event):
    from PyQt6.QtCore import Qt
    pos = event.position()
    if event.button() == Qt.MouseButton.LeftButton:
        self._camera.orbit_start(pos.x(), pos.y(), self.width(), self.height())
        self._mouse_mode = "orbit"
    elif event.button() == Qt.MouseButton.MiddleButton:
        self._camera.pan_start(pos.x(), pos.y())
        self._mouse_mode = "pan"

def mouseMoveEvent(self, event):
    pos = event.position()
    if self._mouse_mode == "orbit":
        self._camera.orbit_update(pos.x(), pos.y(), self.width(), self.height())
    elif self._mouse_mode == "pan":
        self._camera.pan_update(pos.x(), pos.y(), self.width(), self.height())
    self.update()

def mouseReleaseEvent(self, event):
    self._mouse_mode = None

def wheelEvent(self, event):
    delta = event.angleDelta().y() / 120.0  # 1.0 per notch
    self._camera.zoom(delta)
    self.update()
```

### Pattern 11: GeometryBuilder (ParseResult to GPU data)

**What:** Convert parsed data into numpy vertex arrays ready for VBO upload. Keep this logic in `renderer/geometry_builder.py`, separate from the GL widget.

```python
from dataclasses import dataclass
import numpy as np
from rapid_viewer.parser.tokens import ParseResult, MoveType

# Color palette (RGB float, 0.0-1.0)
COLOR_MOVEL  = (0.2, 0.8, 0.2)   # solid green
COLOR_MOVEJ  = (0.8, 0.5, 0.1)   # dashed orange
COLOR_MOVEC  = (0.2, 0.6, 1.0)   # arc blue
COLOR_MARKER = (1.0, 1.0, 0.3)   # waypoint yellow

@dataclass
class GeometryBuffers:
    solid_verts: np.ndarray       # (N, 6) float32 [x,y,z,r,g,b] for MoveL + MoveC arcs
    dashed_verts: np.ndarray      # (M, 6) float32 for MoveJ segments
    marker_verts: np.ndarray      # (K, 6) float32 for waypoint dots

def build_geometry(result: ParseResult, arc_segments: int = 32) -> GeometryBuffers:
    """Convert ParseResult into renderable vertex arrays."""
    solid = []
    dashed = []
    markers = []

    prev_pos = None  # track previous endpoint for MoveC arc start

    for move in result.moves:
        if not move.has_cartesian or move.target is None:
            continue  # skip MoveAbsJ

        curr_pos = move.target.pos  # np.ndarray [x,y,z]

        if move.move_type == MoveType.MOVEL:
            if prev_pos is not None:
                _add_line_segment(solid, prev_pos, curr_pos, COLOR_MOVEL)

        elif move.move_type == MoveType.MOVEJ:
            if prev_pos is not None:
                _add_line_segment(dashed, prev_pos, curr_pos, COLOR_MOVEJ)

        elif move.move_type == MoveType.MOVEC:
            if prev_pos is not None and move.circle_point is not None:
                arc_pts = tessellate_arc(prev_pos, move.circle_point.pos, curr_pos, arc_segments)
                _add_polyline(solid, arc_pts, COLOR_MOVEC)

        # Marker at every waypoint
        markers.append([*curr_pos, *COLOR_MARKER])
        prev_pos = curr_pos

    return GeometryBuffers(
        solid_verts=np.array(solid, dtype=np.float32).reshape(-1, 6) if solid else np.empty((0, 6), np.float32),
        dashed_verts=np.array(dashed, dtype=np.float32).reshape(-1, 6) if dashed else np.empty((0, 6), np.float32),
        marker_verts=np.array(markers, dtype=np.float32).reshape(-1, 6) if markers else np.empty((0, 6), np.float32),
    )

def _add_line_segment(buf, p0, p1, color):
    buf.extend([*p0, *color, *p1, *color])

def _add_polyline(buf, points, color):
    for i in range(len(points) - 1):
        buf.extend([*points[i], *color, *points[i+1], *color])
```

### Anti-Patterns to Avoid

- **`glBegin/glEnd` or any immediate mode:** Not available in OpenGL 3.3 Core Profile. Will crash or produce nothing.
- **`glLineStipple`:** Removed in Core Profile. Always use the fragment shader discard approach.
- **`glLoadIdentity`, `glMatrixMode`, `glPushMatrix`:** Deprecated fixed-function. Use shader uniforms and pyrr matrices.
- **Importing `QOpenGLWidget` from `PyQt6.QtWidgets`:** Wrong module. Use `PyQt6.QtOpenGLWidgets`.
- **Creating `QApplication` before `QSurfaceFormat.setDefaultFormat()`:** On some drivers this silently gives a compatibility context.
- **Uploading matrices as `float64`:** OpenGL expects `float32`. Always `dtype=np.float32` before `glUniformMatrix4fv`.
- **Forgetting `glEnable(GL_PROGRAM_POINT_SIZE)`:** Without this, `gl_PointSize` in the vertex shader has no effect on most drivers.
- **Using `repaint()` instead of `update()`:** `repaint()` forces immediate redraw synchronously; `update()` schedules via the event loop (correct pattern for Qt OpenGL).
- **Storing rotation as Euler angles:** Accumulating Euler rotations causes gimbal lock. Always use quaternions.
- **Camera near plane too close to zero:** RAPID coordinates are in mm. A near plane of `0.1` will cause Z-fighting on a 1-meter toolpath. Use `near=1.0` (1mm) and `far=100000.0` (100m).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MVP matrix construction | Custom 4x4 multiply functions | `pyrr.matrix44.create_perspective_projection`, `pyrr.matrix44.create_look_at` | Column-major convention already correct for OpenGL; transposes handled |
| Quaternion accumulation | Euler angle slerp | `pyrr.Quaternion` multiplication and `normalized` | Gimbal lock; Euler angles break at 90-degree singularities |
| Dashed line stippling | `glLineStipple` | Fragment shader `discard` by distance | `glLineStipple` doesn't exist in Core Profile |
| Arc geometry | Custom Bezier | 3-point circumcircle tessellation | Bezier is the wrong curve type for MoveC; ABB uses a true circular arc |
| Color picking | Custom ray-caster from scratch | Pre-build the infrastructure decision now (color-FBO vs ray-cast) | Phase 3 depends on this; wrong choice requires rewrite |

**Key insight:** The fragment-shader discard approach for dashed lines adds one additional shader program. This is the standard solution and is ~20 lines of GLSL.

---

## Common Pitfalls

### Pitfall 1: Wrong Import Path for QOpenGLWidget in PyQt6

**What goes wrong:** `from PyQt6.QtWidgets import QOpenGLWidget` raises `ImportError` or silently imports `None`.
**Why it happens:** PyQt6 moved OpenGL classes to separate modules compared to PyQt5.
**How to avoid:**
```python
from PyQt6.QtOpenGLWidgets import QOpenGLWidget        # correct
from PyQt6.QtOpenGL import QOpenGLShader, QOpenGLShaderProgram  # correct
```
**Warning signs:** `ImportError: cannot import name 'QOpenGLWidget'` from `QtWidgets`.

### Pitfall 2: No OpenGL Context in initializeGL -- Context Not Current Outside Lifecycle Methods

**What goes wrong:** Calling `glGenVertexArrays` or `glCreateShader` from `__init__` or a signal handler crashes with "no current context".
**Why it happens:** Qt's OpenGL context is only made current inside `initializeGL`, `paintGL`, `resizeGL`, and explicitly via `makeCurrent()`.
**How to avoid:** All GL calls must be inside the three lifecycle methods OR preceded by `self.makeCurrent()` / followed by `self.doneCurrent()`.
**Warning signs:** `OpenGL.error.GLError: GLError(err = 1282)` or segfault on GL calls at startup.

### Pitfall 3: Float64 Matrices Passed to glUniformMatrix4fv

**What goes wrong:** The matrix uploads silently but renders nothing (or garbage). The GPU receives the wrong bytes.
**Why it happens:** pyrr and numpy default to `float64`; OpenGL uniforms expect `float32`.
**How to avoid:** Always specify `dtype=np.float32` when constructing matrices, or call `.astype(np.float32)` before upload.
**Warning signs:** Scene renders blank; no GL errors because the bytes are valid, just wrong precision.

### Pitfall 4: Quaternion Drift Over Many Orbit Drags

**What goes wrong:** After hundreds of orbit interactions, the quaternion accumulates floating-point error and the scene shears or scales incorrectly.
**Why it happens:** Floating-point rounding in repeated quaternion multiplications -- unit quaternion constraint drifts.
**How to avoid:** After every orbit update, normalize: `self._rotation = pyrr.Quaternion(self._rotation.normalized)`.
**Warning signs:** Scene slowly stretches or compresses after many drag operations.

### Pitfall 5: MoveC Degenerate Arc (Collinear Points)

**What goes wrong:** If start, via, and end are collinear (or nearly so), the circumcircle radius goes to infinity and the tessellator produces NaN coordinates. The VBO upload succeeds, but the GPU renders nothing or artifacts.
**Why it happens:** Real RAPID files sometimes have MoveC instructions where the robot is moving nearly straight.
**How to avoid:** Check `cross(v1, v2)` magnitude before circumcircle computation; fall back to straight line if below threshold (e.g., `1e-6`).
**Warning signs:** GPU renders a point cloud of NaN-mapped fragments, or the entire scene disappears after loading a particular file.

### Pitfall 6: Near/Far Clipping Plane Miscalibrated for RAPID Coordinates

**What goes wrong:** Toolpath gets clipped at close distances, or Z-fighting causes flickering.
**Why it happens:** RAPID positions are in millimeters. A typical welding or painting path spans 0-3000mm. Default near=0.1 causes extreme Z-buffer precision loss at 2000mm depth.
**How to avoid:** Use `near=1.0` (1mm) and `far=100000.0` (100m). Initial camera distance should be set to bound the scene -- compute the bounding box of all waypoints and set `distance = max_extent * 2`.
**Warning signs:** Scene appears empty at default camera position, or faces flicker with Z-fighting when zoomed in.

### Pitfall 7: glDrawArrays Count Mismatch

**What goes wrong:** `glDrawArrays(GL_LINES, 0, N)` where N is the number of vertices in a (N, 6) array -- but the count must be in vertices, not rows. If you accidentally pass the byte count or the float count, you draw garbage.
**Why it happens:** Confusion between `vertex_array.nbytes`, `vertex_array.shape[0]`, and `vertex_array.size`.
**How to avoid:** Always pass `vertex_array.shape[0]` as the count (number of vertices).
**Warning signs:** Only partial geometry appears, or `GL_INVALID_VALUE` error.

### Pitfall 8: XYZ Axes Indicator Viewport Not Restored

**What goes wrong:** After drawing the corner axes indicator in a small viewport, the main scene in the next frame renders into the small viewport too (everything squished into the corner).
**Why it happens:** The viewport state from `_draw_axes_indicator` persists into the next `paintGL` call.
**How to avoid:** Always restore the full viewport after drawing the axes indicator: `glViewport(0, 0, self.width(), self.height())`.

---

## Color Conventions for Move Types

| Move Type | Color | Rationale |
|-----------|-------|-----------|
| MoveL | Green (0.2, 0.8, 0.2) | Most common; "go" signal color |
| MoveJ | Orange (0.8, 0.5, 0.1) | Joint move warning; dashed pattern adds visual distinction |
| MoveC | Blue (0.2, 0.6, 1.0) | Arc/circular; cool color contrasts with linear paths |
| Marker | Yellow (1.0, 1.0, 0.3) | High visibility waypoint dot |
| X axis | Red (1.0, 0.0, 0.0) | Universal RGB->XYZ convention |
| Y axis | Green (0.0, 1.0, 0.0) | Universal |
| Z axis | Blue (0.0, 0.0, 1.0) | Universal |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `glLineStipple` for dashed lines | Fragment shader `discard` by distance | OpenGL 3.0 deprecation (2008) | All dashed-line tutorials before 2010 are wrong for Core Profile |
| `QGLWidget` | `QOpenGLWidget` | Qt 5.4 (2014), required in Qt 6 | `QGLWidget` is removed in Qt 6; only `QOpenGLWidget` works |
| `QOpenGLWidget` in `QtWidgets` | `QOpenGLWidget` in `QtOpenGLWidgets` | PyQt6 release (2021) | PyQt5 import path is wrong for PyQt6 |
| Euler angles for camera | Quaternion arcball | Industry standard since Shoemake 1992 | Euler causes gimbal lock at 90-degree rotation singularities |
| Perspective projection by hand | `pyrr.matrix44.create_perspective_projection` | Library adoption | Eliminates column/row-major confusion bugs |

**Deprecated/outdated:**
- `glBegin/glEnd`: Removed in Core Profile. Any tutorial using this is pre-2008 and unusable.
- `glLoadIdentity/glMatrixMode/glOrtho`: Same removal. All matrix math now in vertex shaders.
- `Qt.AA_UseDesktopOpenGL`: Replaced by `QSurfaceFormat` default format approach.

---

## Phase 3 Dependency (Color Picking Decision -- Decide Now)

Phase 3 requires clicking waypoints in the 3D view (LINK-01). There are two approaches:

| Approach | Implementation | Pros | Cons |
|----------|---------------|------|------|
| **Color FBO picking** | Render each point with a unique solid color to an offscreen FBO; read pixel at mouse click | GPU-side, handles occlusion correctly | Requires a second render pass + offscreen FBO setup |
| **Ray-cast (CPU)** | Unproject mouse click to a world-space ray; find the nearest waypoint within a threshold | No extra render pass; simpler | Miss-clicks near overlapping points; no occlusion |

**Recommendation for Phase 2:** Do NOT implement picking yet. But choose the approach now so Phase 2 doesn't foreclose either option. Ray-cast is easier to add in Phase 3 without restructuring Phase 2's rendering code. Build the geometry data in a way that preserves the mapping from vertex index to `MoveInstruction` index -- this is required for both approaches.

Store: `marker_index_to_move_index: list[int]` in `GeometryBuffers` alongside the marker vertex array.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.12.9 | -- |
| PyQt6 | QOpenGLWidget | Yes | 6.10.2 | -- |
| PyOpenGL | OpenGL API | No | -- | Must install: `pip install PyOpenGL==3.1.10` |
| PyOpenGL-accelerate | Buffer speedup | No | -- | Must install: `pip install PyOpenGL-accelerate==3.1.10` |
| pyrr | 3D math | No | -- | Must install: `pip install pyrr==0.10.3` |
| numpy | Vertex arrays | Yes | 2.3.5 | -- |
| pytest | Tests | Yes | 9.0.2 | -- |
| pytest-qt | Widget tests | Yes | 4.5.0 | -- |
| OpenGL driver (Win) | Rendering | Yes | (system, DX-bridge) | Windows always provides OpenGL via DXGI |

**Missing dependencies with no fallback:**
- PyOpenGL -- must install before any GL code runs
- PyOpenGL-accelerate -- install alongside PyOpenGL (same version)
- pyrr -- must install before camera code runs

**Wave 0 task:** `pip install PyOpenGL==3.1.10 PyOpenGL-accelerate==3.1.10 pyrr==0.10.3` and update `pyproject.toml`.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-qt 4.5.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (already configured) |
| Quick run command | `pytest tests/test_geometry_builder.py tests/test_camera.py -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REND-01 | `build_geometry()` produces correct vertex arrays for all move types | unit | `pytest tests/test_geometry_builder.py::test_movel_lines -x` | Wave 0 |
| REND-01 | MoveJ segments appear in `dashed_verts`, not `solid_verts` | unit | `pytest tests/test_geometry_builder.py::test_movej_dashed -x` | Wave 0 |
| REND-01 | MoveC arc tessellation produces N+1 points on the circumcircle | unit | `pytest tests/test_geometry_builder.py::test_movec_arc -x` | Wave 0 |
| REND-01 | Degenerate MoveC (collinear) falls back to straight line | unit | `pytest tests/test_geometry_builder.py::test_movec_degenerate -x` | Wave 0 |
| REND-02 | Each Cartesian waypoint has exactly one entry in `marker_verts` | unit | `pytest tests/test_geometry_builder.py::test_marker_count -x` | Wave 0 |
| REND-02 | MoveAbsJ waypoints are excluded from `marker_verts` | unit | `pytest tests/test_geometry_builder.py::test_moveabsj_excluded -x` | Wave 0 |
| REND-03 | Axes VAO geometry has exactly 6 vertices in [x,y,z,r,g,b] layout | unit | `pytest tests/test_geometry_builder.py::test_axes_geometry -x` | Wave 0 |
| REND-05 | QSurfaceFormat requests OpenGL 3.3 Core Profile | unit | `pytest tests/test_gl_widget.py::test_surface_format -x` | Wave 0 |
| REND-05 | `ToolpathGLWidget.initializeGL` runs without GL error | integration | `pytest tests/test_gl_widget.py::test_initialize_no_error -x` | Wave 0 |
| CAM-01 | `orbit_start` + `orbit_update` changes rotation quaternion | unit | `pytest tests/test_camera.py::test_orbit_changes_rotation -x` | Wave 0 |
| CAM-01 | Repeated orbit normalizes quaternion (no drift) | unit | `pytest tests/test_camera.py::test_orbit_no_drift -x` | Wave 0 |
| CAM-02 | `zoom(+1)` decreases camera distance | unit | `pytest tests/test_camera.py::test_zoom_in -x` | Wave 0 |
| CAM-02 | Camera distance clamps at minimum (no negative distance) | unit | `pytest tests/test_camera.py::test_zoom_clamp -x` | Wave 0 |
| CAM-03 | `pan_start` + `pan_update` changes pan offset vector | unit | `pytest tests/test_camera.py::test_pan_changes_offset -x` | Wave 0 |

**Note on REND-05 GL integration test:** `pytest-qt` provides a `qtbot` fixture that creates real Qt widget contexts. The `ToolpathGLWidget.initializeGL` test can be run headless using `QT_QPA_PLATFORM=offscreen` on Windows (if supported) or treated as a manual smoke test. Mark with `@pytest.mark.integration` and exclude from the quick run.

### Sampling Rate

- **Per task commit:** `pytest tests/test_geometry_builder.py tests/test_camera.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_geometry_builder.py` -- covers REND-01, REND-02, REND-03
- [ ] `tests/test_camera.py` -- covers CAM-01, CAM-02, CAM-03
- [ ] `tests/test_gl_widget.py` -- covers REND-05 (requires pytest-qt qtbot)
- [ ] `src/rapid_viewer/renderer/__init__.py` -- package init
- [ ] `src/rapid_viewer/renderer/geometry_builder.py` -- GeometryBuffers, build_geometry, tessellate_arc
- [ ] `src/rapid_viewer/renderer/camera.py` -- ArcballCamera
- [ ] `src/rapid_viewer/renderer/shaders.py` -- shader source strings
- [ ] `src/rapid_viewer/ui/toolpath_gl_widget.py` -- ToolpathGLWidget
- [ ] `pyproject.toml` update -- add PyOpenGL, pyrr dependencies
- [ ] `src/rapid_viewer/main.py` update -- add `QSurfaceFormat.setDefaultFormat()` before `QApplication`

---

## Open Questions

1. **Initial camera distance auto-fitting**
   - What we know: Camera must be positioned to see the entire toolpath on first load. RAPID coordinates are in mm, paths range from 100mm to 5000mm spans.
   - What's unclear: No bounding box computation is specified.
   - Recommendation: Compute bounding box of all waypoint positions in `GeometryBuilder`; set initial camera distance to `max(bounding_box_extent) * 2.5`. Include bounding box in `GeometryBuffers`.

2. **RAPID coordinate system vs OpenGL coordinate system**
   - What we know: ABB RAPID uses a right-handed coordinate system where Z is up. OpenGL default is Y-up.
   - What's unclear: Should the viewer match RAPID convention (Z-up) or OpenGL convention (Y-up)?
   - Recommendation: Apply a fixed 90-degree X-rotation to the model matrix to swap Y/Z, so the viewer shows Z-up (matching the robot's world frame). This is a one-time `model_matrix` constant. Document clearly so Phase 3 doesn't undo it.

3. **Dynamic VBO updates vs full rebuild**
   - What we know: When a file is loaded, all geometry changes. The question is whether to use `glBufferSubData` (partial update) or `glBufferData` (full reallocate).
   - What's unclear: File sizes are small (< 10MB of RAPID text), so even thousands of waypoints produce < 1MB of vertex data.
   - Recommendation: Use `glBufferData` (full reallocate) on file load. It's simpler and data size is small enough that the overhead is negligible. Reserve `glBufferSubData` for future per-frame animation updates (Phase 3+).

4. **Rendering when no file is loaded**
   - What we know: `paintGL` is called immediately when the widget is shown, before any file is loaded.
   - What's unclear: Empty VBOs cause undefined behavior if `glDrawArrays` is called with count=0.
   - Recommendation: Track an `_has_geometry` flag. In `paintGL`, skip all draw calls if `_has_geometry` is False. Show only the XYZ axes indicator and a clear background.

---

## Sources

### Primary (HIGH confidence)

- [Qt QOpenGLWidget documentation](https://doc.qt.io/qt-6/qopenglwidget.html) -- lifecycle methods, QSurfaceFormat, makeCurrent, update() semantics
- [Qt Forum: PyQt6 shader-based OpenGL changes](https://forum.qt.io/topic/137468/a-few-basic-changes-in-pyqt6-and-pyside6-regarding-shader-based-opengl-graphics) -- confirmed import paths (`PyQt6.QtOpenGLWidgets`, `PyQt6.QtOpenGL`), QOpenGLShader enum namespacing
- [Rabbid76 graphics-snippets: dashed line shader](https://rabbid76.github.io/graphics-snippets/documentation/dashed_line_shader.html) -- vertex/fragment shader code for GL_LINES and GL_LINE_STRIP dashed lines with `flat` qualifier
- [pyrr matrix44.py source](https://github.com/adamlwgriffiths/Pyrr/blob/master/pyrr/matrix44.py) -- `create_look_at`, `create_perspective_projection`, `create_from_quaternion` signatures
- [ABB RAPID Instructions Reference](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf) -- MoveC three-point arc geometry definition
- Project CLAUDE.md -- locked tech stack, VBO/VAO requirement, OpenGL 3.3 Core constraint

### Secondary (MEDIUM confidence)

- [Arcball camera algorithm](https://en.wikibooks.org/wiki/OpenGL_Programming/Modern_OpenGL_Tutorial_Arcball) -- sphere projection mapping and quaternion delta computation
- [MeshLogic circle fitting](https://meshlogic.github.io/posts/jupyter/curve-fitting/fitting-a-circle-to-cluster-of-3d-points/) -- 3D circumcircle parametric arc generation; `generate_circle_by_vectors` pattern
- [PyPI PyOpenGL 3.1.10](https://pypi.org/project/PyOpenGL/) -- version confirmation, Aug 2025 release
- [PyPI pyrr 0.10.3](https://pypi.org/project/pyrr/) -- version confirmation

### Tertiary (LOW confidence)

- ABB MoveC degenerate arc threshold (240 degrees maximum, ~1mm minimum circle point separation) -- from ABB forums, not official documentation. Treat as heuristic.
- Z-up vs Y-up convention for RAPID -- inferred from ABB documentation convention, not explicitly stated in viewer context. Verify visually during implementation.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries confirmed on PyPI, versions verified
- Architecture (QOpenGLWidget lifecycle, VBO/VAO, shaders): HIGH -- from Qt official docs + confirmed forum post
- Dashed line shader: HIGH -- complete verified GLSL code from rabbid76 graphics-snippets
- Arcball camera math: HIGH -- well-established algorithm (Shoemake 1992), multiple verified sources
- MoveC arc tessellation: MEDIUM -- algorithm is standard 3D geometry, but specific angle-direction handling (via-point arc direction) needs validation against real RAPID files
- Phase 3 picking decision: MEDIUM -- both approaches are standard; recommendation is based on implementation complexity tradeoff, not measured performance

**Research date:** 2026-03-30
**Valid until:** 2026-05-30 (PyQt6 and pyrr APIs are stable; OpenGL 3.3 Core is a fixed specification)
