"""Smoke tests for ToolpathGLWidget.

These tests verify that the widget can be instantiated and that update_scene
does not crash. Visual rendering correctness is verified manually (see
02-VALIDATION.md manual verification section).

Requires a real OpenGL context -- pytest-qt provides this via qtbot.
If OpenGL is unavailable in CI, tests are skipped gracefully.
"""

import pytest
import numpy as np

try:
    from rapid_viewer.renderer.toolpath_gl_widget import ToolpathGLWidget
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False


def _has_gl_context(widget) -> bool:
    """Check whether the widget has a usable OpenGL context."""
    widget.makeCurrent()
    ctx = widget.context()
    if ctx is None or not ctx.isValid():
        return False
    widget.doneCurrent()
    return True


@pytest.fixture
def gl_widget(qtbot):
    widget = ToolpathGLWidget()
    qtbot.addWidget(widget)
    widget.show()
    widget.resize(800, 600)
    if not _has_gl_context(widget):
        pytest.skip("No usable OpenGL context (headless / offscreen platform)")
    return widget


def _make_minimal_parse_result():
    """Build a minimal ParseResult with two MoveL moves for smoke testing."""
    from rapid_viewer.parser.tokens import (
        MoveInstruction, MoveType, ParseResult, RobTarget,
    )
    def _rt(name, x, y, z):
        return RobTarget(
            name=name,
            pos=np.array([x, y, z], dtype=np.float64),
            orient=np.array([1.0, 0.0, 0.0, 0.0]),
            confdata=(0, 0, 0, 0),
            extjoint=(9e9,) * 6,
            source_line=1,
        )
    moves = [
        MoveInstruction(
            move_type=MoveType.MOVEL,
            target=_rt("p10", 0, 0, 0),
            circle_point=None, joint_target=None,
            speed="v100", zone="fine", tool="tool0", wobj="wobj0",
            source_line=1, has_cartesian=True,
        ),
        MoveInstruction(
            move_type=MoveType.MOVEL,
            target=_rt("p20", 100, 200, 50),
            circle_point=None, joint_target=None,
            speed="v100", zone="fine", tool="tool0", wobj="wobj0",
            source_line=2, has_cartesian=True,
        ),
    ]
    return ParseResult(
        module_name="TestModule",
        moves=moves,
        targets={"p10": moves[0].target, "p20": moves[1].target},
        joint_targets={},
        source_text="MODULE TestModule\nENDMODULE",
    )


@pytest.mark.skipif(not OPENGL_AVAILABLE, reason="PyOpenGL not installed")
def test_widget_instantiates(qtbot):
    """ToolpathGLWidget can be created without error."""
    widget = ToolpathGLWidget()
    qtbot.addWidget(widget)
    assert widget is not None


@pytest.mark.skipif(not OPENGL_AVAILABLE, reason="PyOpenGL not installed")
def test_widget_shows(gl_widget):
    """Widget is visible after show()."""
    assert gl_widget.isVisible()


@pytest.mark.skipif(not OPENGL_AVAILABLE, reason="PyOpenGL not installed")
def test_update_scene_no_crash(gl_widget):
    """update_scene() with a valid ParseResult does not raise."""
    result = _make_minimal_parse_result()
    gl_widget.update_scene(result)  # must not raise


@pytest.mark.skipif(not OPENGL_AVAILABLE, reason="PyOpenGL not installed")
def test_update_scene_empty_parse_result(gl_widget, qtbot):
    """update_scene() with an empty ParseResult (no moves) does not crash."""
    from rapid_viewer.parser.tokens import ParseResult
    empty = ParseResult(
        module_name="Empty",
        moves=[],
        targets={},
        joint_targets={},
        source_text="",
    )
    gl_widget.update_scene(empty)


@pytest.mark.skipif(not OPENGL_AVAILABLE, reason="PyOpenGL not installed")
def test_widget_resizes(qtbot):
    """Widget handles resize without crash."""
    widget = ToolpathGLWidget()
    qtbot.addWidget(widget)
    widget.show()
    widget.resize(1024, 768)
    widget.resize(400, 300)
