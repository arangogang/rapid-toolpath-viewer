"""Tests for the ArcballCamera.

Covers orbit, pan, zoom, matrix generation, and property access.
Requirement IDs: CAM-01, CAM-02, CAM-03.
"""

import numpy as np
import pytest

from rapid_viewer.renderer.camera import ArcballCamera


# ---------------------------------------------------------------------------
# Instantiation
# ---------------------------------------------------------------------------


def test_camera_instantiates():
    """ArcballCamera() with no args raises no exception."""
    camera = ArcballCamera()
    assert camera is not None


def test_initial_distance():
    """Default distance is 1000.0 mm."""
    camera = ArcballCamera()
    assert camera._distance == 1000.0


# ---------------------------------------------------------------------------
# Orbit
# ---------------------------------------------------------------------------


def test_orbit_changes_rotation():
    """orbit_start + orbit_update with distinct positions changes yaw/pitch."""
    camera = ArcballCamera()
    yaw0, pitch0 = camera.yaw, camera.pitch
    camera.orbit_start(100, 100, 800, 600)
    camera.orbit_update(200, 200, 800, 600)
    assert camera.yaw != yaw0 or camera.pitch != pitch0


# ---------------------------------------------------------------------------
# Pan
# ---------------------------------------------------------------------------


def test_pan_changes_offset():
    """pan_start + pan_update with non-zero delta changes _pan_offset from zeros."""
    camera = ArcballCamera()
    camera.pan_start(0, 0)
    camera.pan_update(50, 30, 800, 600)
    assert np.any(camera._pan_offset != 0)


# ---------------------------------------------------------------------------
# Zoom
# ---------------------------------------------------------------------------


def test_zoom_in_reduces_distance():
    """Positive delta zooms in (reduces distance)."""
    camera = ArcballCamera()
    d0 = camera._distance
    camera.zoom(1.0)
    assert camera._distance < d0


def test_zoom_out_increases_distance():
    """Negative delta zooms out (increases distance)."""
    camera = ArcballCamera()
    camera.zoom(-1.0)
    assert camera._distance > 1000.0


def test_zoom_minimum_clamp():
    """Distance is clamped to minimum 0.5 after aggressive zoom-in."""
    camera = ArcballCamera()
    for _ in range(200):
        camera.zoom(10.0)
    assert camera._distance >= 0.5


# ---------------------------------------------------------------------------
# Matrix generation
# ---------------------------------------------------------------------------


def test_view_matrix_shape_dtype():
    """view_matrix() returns np.ndarray shape (4,4) dtype float32."""
    camera = ArcballCamera()
    v = camera.view_matrix()
    assert isinstance(v, np.ndarray)
    assert v.shape == (4, 4)
    assert v.dtype == np.float32


def test_projection_matrix_shape_dtype():
    """projection_matrix() returns shape (4,4) dtype float32."""
    camera = ArcballCamera()
    camera.set_aspect(1.333)
    p = camera.projection_matrix()
    assert isinstance(p, np.ndarray)
    assert p.shape == (4, 4)
    assert p.dtype == np.float32


def test_mvp_shape():
    """mvp() returns shape (4,4)."""
    camera = ArcballCamera()
    m = camera.mvp()
    assert m.shape == (4, 4)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_set_aspect_no_crash():
    """set_aspect(0.5) succeeds and updates _aspect."""
    camera = ArcballCamera()
    camera.set_aspect(0.5)
    assert camera._aspect == 0.5


def test_view_rotation_shape():
    """camera.view_rotation() returns 3x3 float32 array."""
    camera = ArcballCamera()
    rot = camera.view_rotation()
    assert isinstance(rot, np.ndarray)
    assert rot.shape == (3, 3)
