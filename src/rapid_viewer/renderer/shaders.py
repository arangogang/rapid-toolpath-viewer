"""GLSL shader source strings for the toolpath renderer.

All shaders target OpenGL 3.3 Core Profile.
Module-level constants -- no file I/O at runtime.

Vertex layout (location binding):
  location 0: vec3 aPos   (x, y, z)
  location 1: vec3 aColor (r, g, b)

Uniforms:
  u_mvp (mat4): model-view-projection matrix
  u_resolution (vec2): viewport size in pixels (dashed shader only)
  u_dash_size (float): dash length in pixels (dashed shader only, default 10.0)
  u_gap_size (float): gap length in pixels (dashed shader only, default 6.0)
  u_point_size (float): point sprite size in pixels (marker shader only, default 8.0)
"""

# ---------------------------------------------------------------------------
# Solid line shader (MoveL segments, MoveC arc polylines)
# ---------------------------------------------------------------------------

SOLID_VERT = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
uniform mat4 u_mvp;
out vec3 vColor;
void main() {
    gl_Position = u_mvp * vec4(aPos, 1.0);
    vColor = aColor;
}
"""

SOLID_FRAG = """
#version 330 core
in vec3 vColor;
out vec4 fragColor;
void main() {
    fragColor = vec4(vColor, 1.0);
}
"""

# ---------------------------------------------------------------------------
# Dashed line shader (MoveJ segments)
# Discards fragments by NDC-space distance from segment start.
# The 'flat' qualifier on vStartPos is critical: without it the start
# position would be interpolated, destroying the fixed reference point.
# ---------------------------------------------------------------------------

DASHED_VERT = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
uniform mat4 u_mvp;
flat out vec3 vStartPos;
out vec3 vPos;
out vec3 vColor;
void main() {
    vec4 clip = u_mvp * vec4(aPos, 1.0);
    gl_Position = clip;
    vPos = clip.xyz / clip.w;
    vStartPos = vPos;
    vColor = aColor;
}
"""

DASHED_FRAG = """
#version 330 core
flat in vec3 vStartPos;
in vec3 vPos;
in vec3 vColor;
out vec4 fragColor;
uniform vec2 u_resolution;
uniform float u_dash_size;
uniform float u_gap_size;
void main() {
    vec2 dir = (vPos.xy - vStartPos.xy) * u_resolution / 2.0;
    float dist = length(dir);
    float period = u_dash_size + u_gap_size;
    if (fract(dist / period) > u_dash_size / period)
        discard;
    fragColor = vec4(vColor, 1.0);
}
"""

# ---------------------------------------------------------------------------
# Marker shader (GL_POINTS with circular discard)
# Requires glEnable(GL_PROGRAM_POINT_SIZE) before drawing.
# ---------------------------------------------------------------------------

MARKER_VERT = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
uniform mat4 u_mvp;
uniform float u_point_size;
out vec3 vColor;
void main() {
    gl_Position = u_mvp * vec4(aPos, 1.0);
    gl_PointSize = u_point_size;
    vColor = aColor;
}
"""

MARKER_FRAG = """
#version 330 core
in vec3 vColor;
out vec4 fragColor;
void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    if (dot(coord, coord) > 0.25)
        discard;
    fragColor = vec4(vColor, 1.0);
}
"""

# ---------------------------------------------------------------------------
# Axes indicator shader (XYZ triad, drawn with rotation-only MVP)
# Reuses the solid shader pair above -- no separate source needed.
# Export aliases for clarity at the call site.
# ---------------------------------------------------------------------------

AXES_VERT = SOLID_VERT  # same vertex shader, different MVP uniform value
AXES_FRAG = SOLID_FRAG  # same fragment shader

# ---------------------------------------------------------------------------
# TCP orientation triads shader (RGB axis lines at each waypoint)
# Reuses the solid shader pair -- per-vertex color provides R/G/B axes.
# ---------------------------------------------------------------------------

TRIAD_VERT = SOLID_VERT
TRIAD_FRAG = SOLID_FRAG
