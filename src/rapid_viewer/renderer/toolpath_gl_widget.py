"""QOpenGLWidget subclass: renders parsed RAPID toolpaths in 3D.

OpenGL 3.3 Core Profile. All geometry in VBOs. No immediate mode.

Public API consumed by MainWindow:
    widget = ToolpathGLWidget(parent)
    widget.update_scene(parse_result)  # call after file load
"""

from __future__ import annotations

import ctypes

import numpy as np
import pyrr
from OpenGL.GL import (
    GL_ARRAY_BUFFER,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_DYNAMIC_DRAW,
    GL_FALSE,
    GL_FLOAT,
    GL_LINES,
    GL_POINTS,
    GL_PROGRAM_POINT_SIZE,
    glBindBuffer,
    glBindVertexArray,
    glBufferData,
    glClear,
    glClearColor,
    glDeleteBuffers,
    glDeleteVertexArrays,
    glDrawArrays,
    glEnable,
    glEnableVertexAttribArray,
    glGenBuffers,
    glGenVertexArrays,
    glGetUniformLocation,
    glUniform1f,
    glUniform2f,
    glUniformMatrix4fv,
    glUseProgram,
    glVertexAttribPointer,
    glViewport,
)
from OpenGL.GL.shaders import (
    GL_FRAGMENT_SHADER,
    GL_VERTEX_SHADER,
    compileProgram,
    compileShader,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from rapid_viewer.parser.tokens import ParseResult
from rapid_viewer.renderer.camera import ArcballCamera
from rapid_viewer.renderer.geometry_builder import GeometryBuffers, build_geometry
from rapid_viewer.renderer.view_cube import ViewCube
from rapid_viewer.renderer.shaders import (
    AXES_FRAG,
    AXES_VERT,
    DASHED_FRAG,
    DASHED_VERT,
    MARKER_FRAG,
    MARKER_VERT,
    SOLID_FRAG,
    SOLID_VERT,
    TRIAD_FRAG,
    TRIAD_VERT,
)

# Axes geometry: 3 unit-length lines [x,y,z, r,g,b] per vertex
_AXES_VERTS = np.array([
    0, 0, 0, 1, 0, 0,   # X start: origin, red
    1, 0, 0, 1, 0, 0,   # X end: +X, red
    0, 0, 0, 0, 1, 0,   # Y start: origin, green
    0, 1, 0, 0, 1, 0,   # Y end: +Y, green
    0, 0, 0, 0, 0, 1,   # Z start: origin, blue
    0, 0, 1, 0, 0, 1,   # Z end: +Z, blue
], dtype=np.float32).reshape(-1, 6)


class ToolpathGLWidget(QOpenGLWidget):
    """OpenGL 3.3 Core Profile widget for toolpath visualization.

    Renders:
    - Solid lines: MoveL + MoveC arcs (green/blue)
    - Dashed lines: MoveJ segments (orange)
    - Round point markers: all Cartesian waypoints (yellow)
    - XYZ axes indicator: bottom-left corner, rotation-only
    """

    waypoint_picked = pyqtSignal(int, bool, bool)  # index, shift_held, ctrl_held

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._camera = ArcballCamera()
        self._mouse_mode: str | None = None
        self._buffers: GeometryBuffers | None = None

        # Shader program IDs (set in initializeGL)
        self._solid_prog: int = 0
        self._dashed_prog: int = 0
        self._marker_prog: int = 0
        self._axes_prog: int = 0
        self._triad_prog: int = 0

        # VAO / VBO IDs for each geometry type
        self._solid_vao: int = 0
        self._solid_vbo: int = 0
        self._solid_count: int = 0

        self._dashed_vao: int = 0
        self._dashed_vbo: int = 0
        self._dashed_count: int = 0

        self._marker_vao: int = 0
        self._marker_vbo: int = 0
        self._marker_count: int = 0

        self._axes_vao: int = 0
        self._axes_vbo: int = 0

        # Highlight marker (current waypoint)
        self._highlight_vao: int = 0
        self._highlight_vbo: int = 0
        self._highlight_index: int = -1

        # Selected markers (multi-select)
        self._selected_vao: int = 0
        self._selected_vbo: int = 0
        self._selected_count: int = 0
        self._selected_set: frozenset[int] = frozenset()
        self._last_picked_index: int = -1

        # TCP orientation triads
        self._triad_vao: int = 0
        self._triad_vbo: int = 0
        self._triad_count: int = 0

        # Progressive draw: cumulative vertex counts per waypoint
        self._solid_cumulative: list[int] = []
        self._dashed_cumulative: list[int] = []

        # Cached waypoint positions for ray-cast picking
        self._waypoint_positions: np.ndarray | None = None

        # Physical viewport dimensions (set in resizeGL, used for picking)
        self._viewport_w: int = 0
        self._viewport_h: int = 0

        # Mouse press position for click-vs-drag detection
        self._press_pos: tuple[float, float] | None = None

        # Navigation view cube
        self._view_cube = ViewCube()

        # Last loaded scene — used to re-upload geometry after context loss
        self._last_parse_result: ParseResult | None = None

    # ------------------------------------------------------------------
    # QOpenGLWidget lifecycle
    # ------------------------------------------------------------------

    def initializeGL(self) -> None:
        """Called once when context is created (and again after context loss).

        Compiles shaders and creates VAOs/VBOs. If a scene was previously
        loaded (``_last_parse_result`` is set), re-uploads the geometry so
        that context loss does not cause a permanently blank viewport.
        """
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_PROGRAM_POINT_SIZE)
        glClearColor(0.1, 0.1, 0.15, 1.0)

        self._solid_prog = self._compile(SOLID_VERT, SOLID_FRAG)
        self._dashed_prog = self._compile(DASHED_VERT, DASHED_FRAG)
        self._marker_prog = self._compile(MARKER_VERT, MARKER_FRAG)
        self._axes_prog = self._compile(AXES_VERT, AXES_FRAG)

        # Pre-create VAOs/VBOs (empty -- filled on first update_scene)
        self._solid_vao, self._solid_vbo = self._create_vao_vbo(
            np.empty((0, 6), dtype=np.float32)
        )
        self._dashed_vao, self._dashed_vbo = self._create_vao_vbo(
            np.empty((0, 6), dtype=np.float32)
        )
        self._marker_vao, self._marker_vbo = self._create_vao_vbo(
            np.empty((0, 6), dtype=np.float32)
        )
        self._axes_vao, self._axes_vbo = self._create_vao_vbo(_AXES_VERTS)

        # Triad shader + VAO/VBO
        self._triad_prog = self._compile(TRIAD_VERT, TRIAD_FRAG)
        self._triad_vao, self._triad_vbo = self._create_vao_vbo(
            np.empty((0, 6), dtype=np.float32)
        )

        # Highlight marker VAO/VBO (single point)
        self._highlight_vao, self._highlight_vbo = self._create_vao_vbo(
            np.empty((0, 6), dtype=np.float32)
        )

        # Selected markers VAO/VBO (multi-select)
        self._selected_vao, self._selected_vbo = self._create_vao_vbo(
            np.empty((0, 6), dtype=np.float32)
        )
        self._selected_count = 0

        # Reset counts — VAOs are fresh and empty after (re)initialization
        self._solid_count = 0
        self._dashed_count = 0
        self._marker_count = 0
        self._triad_count = 0
        self._highlight_index = -1
        self._solid_cumulative = []
        self._dashed_cumulative = []
        self._waypoint_positions = None

        # Context loss recovery: re-upload geometry if a scene was loaded before
        if self._last_parse_result is not None:
            self._upload_scene(self._last_parse_result)

    def resizeGL(self, w: int, h: int) -> None:
        """Called on resize. Update viewport and camera aspect.

        Note: w, h are physical pixels (scaled by devicePixelRatio) in Qt6.
        """
        glViewport(0, 0, w, h)
        self._camera.set_aspect(w / max(h, 1))
        self._viewport_w = w
        self._viewport_h = h

    def paintGL(self) -> None:
        """Called each frame. Draw toolpath, markers, axes indicator, view cube."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        mvp = self._camera.mvp()
        w, h = self.width(), self.height()

        self._draw_solid(mvp)
        self._draw_dashed(mvp, w, h)
        self._draw_markers(mvp)
        self._draw_selected(mvp)
        self._draw_highlight(mvp)
        self._draw_triads(mvp)
        self._draw_axes_indicator()

        # View cube overlay (QPainter on top of GL)
        painter = QPainter(self)
        self._view_cube.draw(painter, self._camera.view_rotation(), w, h)
        painter.end()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_scene(self, parse_result: ParseResult) -> None:
        """Rebuild GPU geometry from parse result. Call after file load.

        Caches the ParseResult so that geometry can be restored after an
        OpenGL context loss and re-initialization.
        """
        self._last_parse_result = parse_result
        ctx = self.context()
        if ctx is None or not ctx.isValid():
            # Context not yet available — geometry will be uploaded in initializeGL
            return
        self.makeCurrent()
        self._upload_scene(parse_result)
        self.doneCurrent()
        self.update()

    def _upload_scene(self, parse_result: ParseResult) -> None:
        """Upload geometry to GPU. Caller must ensure context is current."""
        buffers = build_geometry(parse_result)
        self._upload_vbo(self._solid_vbo, buffers.solid_verts)
        self._solid_count = len(buffers.solid_verts)
        self._upload_vbo(self._dashed_vbo, buffers.dashed_verts)
        self._dashed_count = len(buffers.dashed_verts)
        self._upload_vbo(self._marker_vbo, buffers.marker_verts)
        self._marker_count = len(buffers.marker_verts)

        # Upload triad geometry
        self._upload_vbo(self._triad_vbo, buffers.triad_verts)
        self._triad_count = len(buffers.triad_verts)

        # Store cumulative arrays for progressive drawing
        self._solid_cumulative = buffers.solid_cumulative or []
        self._dashed_cumulative = buffers.dashed_cumulative or []

        # Cache waypoint positions for ray-cast picking
        if self._marker_count > 0:
            self._waypoint_positions = buffers.marker_verts[:, :3].copy()
        else:
            self._waypoint_positions = None

        # Reset selection state on new scene
        self._selected_count = 0
        self._selected_set = frozenset()

        # Start at first waypoint for progressive drawing
        self._highlight_index = 0

        # Auto-fit camera to scene bounding sphere
        all_pts = buffers.marker_verts[:, :3] if self._marker_count > 0 else None
        if all_pts is not None and len(all_pts) > 0:
            center = all_pts.mean(axis=0)
            radius = float(np.max(np.linalg.norm(all_pts - center, axis=1)))
            self._camera.reset(center, max(radius, 1.0))

    def set_highlight_index(self, index: int) -> None:
        """Highlight a waypoint by index. Pass -1 to clear highlight."""
        if index < 0 or self._waypoint_positions is None or index >= len(self._waypoint_positions):
            self._highlight_index = -1
            return

        self._highlight_index = index
        pos = self._waypoint_positions[index]
        # Magenta when current is also selected, white otherwise
        if index in self._selected_set:
            color = [1.0, 0.3, 1.0]  # magenta: current + selected
        else:
            color = [1.0, 1.0, 1.0]  # white: current only
        vertex = np.array([[pos[0], pos[1], pos[2], *color]], dtype=np.float32)

        self.makeCurrent()
        self._upload_vbo(self._highlight_vbo, vertex)
        self.doneCurrent()
        self.update()

    def set_selected_indices(self, indices: frozenset[int]) -> None:
        """Update selection highlight VBO with cyan-colored markers."""
        if self._waypoint_positions is None or not indices:
            self._selected_count = 0
            self._selected_set = frozenset()
            self.update()
            return
        ctx = self.context()
        if ctx is None or not ctx.isValid():
            return
        valid = [i for i in indices if 0 <= i < len(self._waypoint_positions)]
        if not valid:
            self._selected_count = 0
            self._selected_set = frozenset()
            self.update()
            return
        verts = np.zeros((len(valid), 6), dtype=np.float32)
        for j, idx in enumerate(valid):
            verts[j, :3] = self._waypoint_positions[idx]
            verts[j, 3:] = [0.0, 1.0, 1.0]  # cyan per UI-SPEC
        self.makeCurrent()
        self._upload_vbo(self._selected_vbo, verts)
        self._selected_count = len(valid)
        self._selected_set = frozenset(valid)
        self.doneCurrent()
        self.update()

    # ------------------------------------------------------------------
    # Draw calls
    # ------------------------------------------------------------------

    def _draw_solid(self, mvp: np.ndarray) -> None:
        if self._solid_count == 0:
            return
        # Progressive: only draw up to current waypoint
        count = self._solid_count
        if self._highlight_index >= 0 and self._solid_cumulative:
            idx = min(self._highlight_index, len(self._solid_cumulative) - 1)
            count = self._solid_cumulative[idx]
        if count == 0:
            return
        glUseProgram(self._solid_prog)
        loc = glGetUniformLocation(self._solid_prog, "u_mvp")
        glUniformMatrix4fv(loc, 1, GL_FALSE, mvp.flatten())
        glBindVertexArray(self._solid_vao)
        glDrawArrays(GL_LINES, 0, count)
        glBindVertexArray(0)

    def _draw_dashed(self, mvp: np.ndarray, w: int, h: int) -> None:
        if self._dashed_count == 0:
            return
        # Progressive: only draw up to current waypoint
        count = self._dashed_count
        if self._highlight_index >= 0 and self._dashed_cumulative:
            idx = min(self._highlight_index, len(self._dashed_cumulative) - 1)
            count = self._dashed_cumulative[idx]
        if count == 0:
            return
        glUseProgram(self._dashed_prog)
        glUniformMatrix4fv(
            glGetUniformLocation(self._dashed_prog, "u_mvp"),
            1, GL_FALSE, mvp.flatten(),
        )
        glUniform2f(
            glGetUniformLocation(self._dashed_prog, "u_resolution"),
            float(w), float(h),
        )
        glUniform1f(
            glGetUniformLocation(self._dashed_prog, "u_dash_size"), 10.0,
        )
        glUniform1f(
            glGetUniformLocation(self._dashed_prog, "u_gap_size"), 6.0,
        )
        glBindVertexArray(self._dashed_vao)
        glDrawArrays(GL_LINES, 0, count)
        glBindVertexArray(0)

    def _draw_markers(self, mvp: np.ndarray) -> None:
        if self._marker_count == 0:
            return
        # Progressive: only draw markers up to current waypoint
        count = self._marker_count
        if self._highlight_index >= 0:
            count = min(self._highlight_index + 1, self._marker_count)
        if count == 0:
            return
        glUseProgram(self._marker_prog)
        glUniformMatrix4fv(
            glGetUniformLocation(self._marker_prog, "u_mvp"),
            1, GL_FALSE, mvp.flatten(),
        )
        glUniform1f(
            glGetUniformLocation(self._marker_prog, "u_point_size"), 8.0,
        )
        glBindVertexArray(self._marker_vao)
        glDrawArrays(GL_POINTS, 0, count)
        glBindVertexArray(0)

    def _draw_selected(self, mvp: np.ndarray) -> None:
        """Draw cyan markers for multi-selected waypoints."""
        if self._selected_count == 0:
            return
        glUseProgram(self._marker_prog)
        glUniformMatrix4fv(
            glGetUniformLocation(self._marker_prog, "u_mvp"),
            1, GL_FALSE, mvp.flatten(),
        )
        glUniform1f(
            glGetUniformLocation(self._marker_prog, "u_point_size"), 10.0,
        )
        glBindVertexArray(self._selected_vao)
        glDrawArrays(GL_POINTS, 0, self._selected_count)
        glBindVertexArray(0)

    def _draw_highlight(self, mvp: np.ndarray) -> None:
        """Draw highlight marker (larger white point) at current waypoint."""
        if self._highlight_index < 0:
            return
        glUseProgram(self._marker_prog)
        glUniformMatrix4fv(
            glGetUniformLocation(self._marker_prog, "u_mvp"),
            1, GL_FALSE, mvp.flatten(),
        )
        glUniform1f(
            glGetUniformLocation(self._marker_prog, "u_point_size"), 14.0,
        )
        glBindVertexArray(self._highlight_vao)
        glDrawArrays(GL_POINTS, 0, 1)
        glBindVertexArray(0)

    def _draw_triads(self, mvp: np.ndarray) -> None:
        """Draw TCP orientation triad only for the currently selected waypoint."""
        if self._triad_count == 0 or self._highlight_index < 0:
            return
        # Each waypoint has 6 vertices (3 axes × 2 endpoints)
        start = self._highlight_index * 6
        if start + 6 > self._triad_count:
            return
        glUseProgram(self._triad_prog)
        loc = glGetUniformLocation(self._triad_prog, "u_mvp")
        glUniformMatrix4fv(loc, 1, GL_FALSE, mvp.flatten())
        glBindVertexArray(self._triad_vao)
        glDrawArrays(GL_LINES, start, 6)
        glBindVertexArray(0)

    def _draw_axes_indicator(self) -> None:
        """Draw XYZ axes triad in bottom-left corner (80x80 px)."""
        w, h = self.width(), self.height()
        size, padding = 80, 10
        glViewport(padding, padding, size, size)
        try:
            # Use the view matrix's 3x3 rotation (same source of truth as
            # the view cube) embedded in a 4x4 for the shader.
            rot_3x3 = self._camera.view_rotation()
            rot_only = np.eye(4, dtype=np.float32)
            rot_only[:3, :3] = rot_3x3

            ortho = pyrr.matrix44.create_orthogonal_projection(
                -1.5, 1.5, -1.5, 1.5, -10.0, 10.0, dtype=np.float32,
            )
            axes_mvp = (rot_only @ ortho).astype(np.float32)

            glUseProgram(self._axes_prog)
            glUniformMatrix4fv(
                glGetUniformLocation(self._axes_prog, "u_mvp"),
                1, GL_FALSE, axes_mvp.flatten(),
            )
            glBindVertexArray(self._axes_vao)
            glDrawArrays(GL_LINES, 0, 6)
            glBindVertexArray(0)
        finally:
            glViewport(0, 0, w, h)  # always restore full viewport

    # ------------------------------------------------------------------
    # Mouse events (CAM-01, CAM-02, CAM-03)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        pos = event.position()
        self._press_pos = (pos.x(), pos.y())
        if event.button() == Qt.MouseButton.LeftButton:
            self._camera.orbit_start(pos.x(), pos.y(), self.width(), self.height())
            self._mouse_mode = "orbit"
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._camera.pan_start(pos.x(), pos.y())
            self._mouse_mode = "pan"

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()
        if self._mouse_mode == "orbit":
            self._camera.orbit_update(pos.x(), pos.y(), self.width(), self.height())
        elif self._mouse_mode == "pan":
            self._camera.pan_update(pos.x(), pos.y(), self.width(), self.height())
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            pos = event.position()
            dx = pos.x() - self._press_pos[0]
            dy = pos.y() - self._press_pos[1]
            if dx * dx + dy * dy < 9.0:  # 3px threshold — click, not drag
                # Check view cube first
                snap = self._view_cube.hit_test(
                    pos.x(), pos.y(),
                    self._camera.view_rotation(),
                    self.width(), self.height(),
                )
                if snap is not None:
                    self._camera.set_view(*snap)
                    self.update()
                else:
                    self._last_picked_index = -1
                    self._try_pick(pos.x(), pos.y())
                    if self._last_picked_index >= 0:
                        mods = event.modifiers()
                        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
                        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
                        self.waypoint_picked.emit(
                            self._last_picked_index, shift, ctrl,
                        )
        self._mouse_mode = None
        self._press_pos = None

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y() / 120.0
        self._camera.zoom(delta)
        self.update()

    # ------------------------------------------------------------------
    # Ray-cast picking
    # ------------------------------------------------------------------

    def _try_pick(self, mouse_x: float, mouse_y: float) -> None:
        """Project all waypoints to screen space and pick the nearest within 20px.

        Uses physical pixel coordinates (viewport dimensions from resizeGL,
        mouse coords scaled by devicePixelRatio) to avoid DPI mismatch.
        """
        if self._waypoint_positions is None or len(self._waypoint_positions) == 0:
            return

        vp_w, vp_h = self._viewport_w, self._viewport_h
        if vp_w == 0 or vp_h == 0:
            return

        # Scale mouse coords from logical to physical pixels
        dpr = self.devicePixelRatio()
        mx = mouse_x * dpr
        my = mouse_y * dpr

        mvp = self._camera.mvp().astype(np.float64)
        positions = self._waypoint_positions.astype(np.float64)

        # Project to clip space: [x, y, z] -> [clip_x, clip_y, clip_z, clip_w]
        n = len(positions)
        homogeneous = np.ones((n, 4), dtype=np.float64)
        homogeneous[:, :3] = positions
        clip = homogeneous @ mvp  # row-vector convention: point @ MVP

        # Filter out points behind camera (clip_w <= 0)
        valid = clip[:, 3] > 1e-6
        if not np.any(valid):
            return

        # NDC -> physical screen coordinates (matching viewport)
        ndc_x = clip[:, 0] / clip[:, 3]
        ndc_y = clip[:, 1] / clip[:, 3]
        screen_x = (ndc_x + 1.0) * 0.5 * vp_w
        screen_y = (1.0 - ndc_y) * 0.5 * vp_h  # Y-flip: Qt Y-down, NDC Y-up

        # Distance from mouse position (both in physical pixels)
        dx = screen_x - mx
        dy = screen_y - my
        dist_sq = dx * dx + dy * dy

        # Mask invalid points with large distance
        dist_sq[~valid] = float("inf")

        min_idx = int(np.argmin(dist_sq))
        # Threshold in physical pixels (20 logical * dpr)
        threshold = 20.0 * dpr
        threshold_sq = threshold * threshold

        if dist_sq[min_idx] <= threshold_sq:
            self._last_picked_index = min_idx

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compile(vert_src: str, frag_src: str) -> int:
        """Compile and link a shader program. Returns program ID."""
        return compileProgram(
            compileShader(vert_src, GL_VERTEX_SHADER),
            compileShader(frag_src, GL_FRAGMENT_SHADER),
        )

    @staticmethod
    def _create_vao_vbo(data: np.ndarray) -> tuple[int, int]:
        """Create VAO+VBO with interleaved [x,y,z,r,g,b] layout. Returns (vao, vbo)."""
        vao = glGenVertexArrays(1)
        vbo = glGenBuffers(1)
        glBindVertexArray(vao)
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        arr = data.astype(np.float32)
        glBufferData(GL_ARRAY_BUFFER, arr.nbytes, arr, GL_DYNAMIC_DRAW)
        stride = 6 * 4  # 6 floats * 4 bytes
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, stride, ctypes.c_void_p(12))
        glBindVertexArray(0)
        return int(vao), int(vbo)

    @staticmethod
    def _upload_vbo(vbo: int, data: np.ndarray) -> None:
        """Re-upload VBO contents. Context must be current."""
        glBindBuffer(GL_ARRAY_BUFFER, vbo)
        arr = data.astype(np.float32)
        glBufferData(GL_ARRAY_BUFFER, arr.nbytes, arr, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
