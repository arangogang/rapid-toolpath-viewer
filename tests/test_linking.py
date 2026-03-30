"""Integration tests for bidirectional 3D-to-code and code-to-3D linking.

Tests the signal chain: PlaybackState <-> CodePanel wiring as done in MainWindow.
GL widget picking is tested indirectly (signal emission only, no context needed).

Requirements covered:
  LINK-01 -- 3D waypoint click -> code panel scrolls to matching source line
  LINK-02 -- Code panel line click -> PlaybackState selects matching move
  PARS-08 -- PROC selector filters moves correctly
"""

from pathlib import Path

import numpy as np
import pytest

from rapid_viewer.parser.tokens import (
    MoveInstruction,
    MoveType,
    ParseResult,
    RobTarget,
)
from rapid_viewer.ui.code_panel import CodePanel
from rapid_viewer.ui.playback_state import PlaybackState

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# -- Helpers -----------------------------------------------------------------

def _make_source(n_lines: int) -> str:
    """Generate a string with n_lines of '! line N' content."""
    return "\n".join(f"! line {i + 1}" for i in range(n_lines))


def _make_robtarget(name: str, x: float = 0.0) -> RobTarget:
    """Create a minimal RobTarget for testing."""
    return RobTarget(
        name=name,
        pos=np.array([x, 0.0, 0.0], dtype=np.float64),
        orient=np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64),
        confdata=(0, 0, 0, 0),
        extjoint=(9e9,) * 6,
        source_line=1,
    )


def _make_moves_with_lines(lines: list[int]) -> list[MoveInstruction]:
    """Create MoveInstruction list with specified source_lines."""
    moves = []
    for i, line in enumerate(lines):
        target = _make_robtarget(f"p{i}", float(i * 100))
        moves.append(
            MoveInstruction(
                move_type=MoveType.MOVEL,
                target=target,
                circle_point=None,
                joint_target=None,
                speed="v100",
                zone="fine",
                tool="tool0",
                wobj="wobj0",
                source_line=line,
                has_cartesian=True,
            )
        )
    return moves


# -- LINK-01: 3D waypoint click -> code panel highlights matching line -------

def test_3d_to_code(qtbot):
    """LINK-01: When PlaybackState index changes, code panel highlights
    the matching source line.
    """
    state = PlaybackState()
    panel = CodePanel()
    qtbot.addWidget(panel)

    # Setup: 3 moves at source lines 5, 10, 15
    moves = _make_moves_with_lines([5, 10, 15])
    source_text = _make_source(20)
    panel.set_source(source_text)
    state.set_moves(moves)

    # Wire signal as MainWindow does
    def on_current_changed(index: int) -> None:
        move = state.current_move
        if move is not None:
            panel.highlight_line(move.source_line)

    state.current_changed.connect(on_current_changed)

    # Select waypoint 1 (source_line=10)
    state.set_index(1)

    # Code panel cursor should be at line 10 (block number 9)
    assert panel.get_cursor_line() == 10


def test_3d_to_code_step_forward(qtbot):
    """LINK-01: Stepping forward updates code panel to next source line."""
    state = PlaybackState()
    panel = CodePanel()
    qtbot.addWidget(panel)

    moves = _make_moves_with_lines([5, 10, 15])
    panel.set_source(_make_source(20))
    state.set_moves(moves)

    state.current_changed.connect(
        lambda idx: panel.highlight_line(state.current_move.source_line)
        if state.current_move else None
    )

    # Step forward from index 0 to index 1
    state.step_forward()
    assert panel.get_cursor_line() == 10

    # Step forward again to index 2
    state.step_forward()
    assert panel.get_cursor_line() == 15


# -- LINK-02: Code panel click -> PlaybackState selects matching move --------

def test_code_to_3d(qtbot):
    """LINK-02: Clicking on a move's source line in code panel selects
    the corresponding move in PlaybackState.
    """
    state = PlaybackState()
    panel = CodePanel()
    qtbot.addWidget(panel)

    moves = _make_moves_with_lines([5, 10, 15])
    panel.set_source(_make_source(20))
    state.set_moves(moves)

    # Wire code panel line_clicked -> search moves as MainWindow does
    def on_line_clicked(line: int) -> None:
        for i, move in enumerate(state._moves):
            if move.source_line == line:
                state.set_index(i)
                return

    panel.line_clicked.connect(on_line_clicked)

    # Simulate cursor move to line 10 by setting cursor position
    block = panel._editor.document().findBlockByLineNumber(9)  # 0-indexed
    from PyQt6.QtGui import QTextCursor
    cursor = QTextCursor(block)
    panel._editor.setTextCursor(cursor)

    # PlaybackState should now point to move index 1 (source_line=10)
    assert state.current_index == 1


# -- PARS-08: PROC filtering ------------------------------------------------

def test_proc_filter_moves(qtbot):
    """PARS-08: Filtering moves by proc_ranges produces correct subset."""
    from rapid_viewer.parser.rapid_parser import parse_module, read_mod_file

    result = parse_module(read_mod_file(FIXTURES_DIR / "multiproc.mod"))

    # Filter to "path2" (lines 13-17)
    proc_range = result.proc_ranges["path2"]
    start_line, end_line = proc_range
    filtered = [
        m for m in result.moves
        if start_line <= m.source_line <= end_line
    ]

    assert len(filtered) == 3
    target_names = [m.target.name for m in filtered]
    assert target_names == ["p30", "p40", "p50"]

    # Verify PlaybackState works with filtered list
    state = PlaybackState()
    state.set_moves(filtered)
    assert state.total == 3


def test_link_after_proc_filter(qtbot):
    """After PROC filter, stepping produces moves within the PROC range."""
    from rapid_viewer.parser.rapid_parser import parse_module, read_mod_file

    result = parse_module(read_mod_file(FIXTURES_DIR / "multiproc.mod"))

    # Filter to "path2"
    start_line, end_line = result.proc_ranges["path2"]
    filtered = [
        m for m in result.moves
        if start_line <= m.source_line <= end_line
    ]

    state = PlaybackState()
    state.set_moves(filtered)

    # Step forward from index 0
    state.step_forward()
    move = state.current_move
    assert move is not None
    assert start_line <= move.source_line <= end_line
    assert move.target.name == "p40"
