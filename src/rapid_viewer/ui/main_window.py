"""Main application window for ABB RAPID Toolpath Viewer.

Provides the QMainWindow with:
  - File > Open menu action (Ctrl+O) to load .mod files via native dialog
  - File > Exit menu action (Ctrl+Q) to close the application
  - Edit > Undo (Ctrl+Z) and Redo (Ctrl+Y) via EditModel's QUndoStack
  - QSplitter layout: GL widget (left) | code panel + property panel (right)
  - PlaybackToolbar at bottom with PROC selector QComboBox
  - Bidirectional linking: 3D click <-> code panel scroll
  - PlaybackState wiring for step-through navigation
  - EditModel + SelectionState for Phase 4 edit infrastructure
  - Phase 5: PropertyPanel edit signals -> EditModel mutations -> geometry rebuild
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
)

APP_TITLE = "ABB RAPID Toolpath Viewer"


class MainWindow(QMainWindow):
    """Main window of the ABB RAPID Toolpath Viewer application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(1024, 700)
        self._parse_result = None
        self._current_file_path: Path | None = None
        self._file_encoding: str = "utf-8"
        self._last_open_dir: str = ""

        # Lazy imports (isolate OpenGL from parser-only tests)
        from rapid_viewer.renderer.toolpath_gl_widget import ToolpathGLWidget
        from rapid_viewer.ui.code_panel import CodePanel
        from rapid_viewer.ui.edit_model import EditModel
        from rapid_viewer.ui.playback_state import PlaybackState
        from rapid_viewer.ui.playback_toolbar import PlaybackToolbar
        from rapid_viewer.ui.property_panel import PropertyPanel
        from rapid_viewer.ui.selection_state import SelectionState

        # Core state
        self._playback_state = PlaybackState(self)
        self._selection_state = SelectionState(self)
        self._edit_model = EditModel(self)

        # Menus (must be after EditModel for Edit menu)
        self._setup_menu()
        self._setup_edit_menu()

        # Widgets
        self._gl_widget = ToolpathGLWidget(self)
        self._code_panel = CodePanel(self)
        self._property_panel = PropertyPanel(self)

        # Right pane: vertical splitter with code panel (top) + property panel (bottom)
        right_splitter = QSplitter(Qt.Orientation.Vertical, self)
        right_splitter.addWidget(self._code_panel)
        right_splitter.addWidget(self._property_panel)
        right_splitter.setSizes([500, 200])

        # Main splitter: GL widget (left) | right_splitter (right)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._gl_widget)
        splitter.addWidget(right_splitter)
        splitter.setSizes([700, 300])
        self.setCentralWidget(splitter)

        # Playback toolbar at bottom
        self._toolbar = PlaybackToolbar(self._playback_state, self)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self._toolbar)

        # PROC selector QComboBox in toolbar
        self._proc_combo = QComboBox(self)
        self._proc_combo.addItem("All PROCs")
        self._proc_combo.currentTextChanged.connect(self._on_proc_changed)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(self._proc_combo)

        # Wire signals
        self._wire_signals()

    def _setup_menu(self) -> None:
        """Build the menu bar with File menu entries."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _setup_edit_menu(self) -> None:
        """Build the Edit menu with Undo/Redo actions from QUndoStack."""
        menu_bar = self.menuBar()
        edit_menu = menu_bar.addMenu("&Edit")
        undo_action = self._edit_model.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut("Ctrl+Z")
        edit_menu.addAction(undo_action)
        redo_action = self._edit_model.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut("Ctrl+Y")
        edit_menu.addAction(redo_action)

    def _wire_signals(self) -> None:
        """Connect signals for bidirectional 3D-to-code linking and Phase 4 models."""
        # 3D pick -> route through MainWindow for selection logic
        self._gl_widget.waypoint_picked.connect(self._on_waypoint_picked)

        # Current waypoint changed -> update 3D highlight + code panel + property panel
        self._playback_state.current_changed.connect(self._on_waypoint_changed)

        # Code panel click -> find matching move -> select in 3D
        self._code_panel.line_clicked.connect(self._on_code_line_clicked)

        # Selection changed -> update GL multi-select + property panel
        self._selection_state.selection_changed.connect(self._on_selection_changed)

        # Dirty state -> title bar asterisk
        self._edit_model.dirty_changed.connect(self._on_dirty_changed)

        # Phase 5: PropertyPanel edit signals -> MainWindow handlers
        self._property_panel.offset_applied.connect(self._on_offset_applied)
        self._property_panel.speed_changed.connect(self._on_speed_changed)
        self._property_panel.zone_changed.connect(self._on_zone_changed)
        self._property_panel.laser_changed.connect(self._on_laser_changed)
        self._property_panel.delete_requested.connect(self._on_delete_requested)
        self._property_panel.insert_requested.connect(self._on_insert_requested)

        # EditModel data change -> rebuild geometry
        self._edit_model.points_changed.connect(self._on_points_changed)

    # -- Slots ---------------------------------------------------------------

    def _gl_ready(self) -> bool:
        """Check whether the GL widget has a valid OpenGL context.

        Returns False if the widget hasn't been shown yet (no context created),
        which prevents makeCurrent() from hanging in tests.
        """
        ctx = self._gl_widget.context()
        return ctx is not None and ctx.isValid()

    def _on_waypoint_picked(self, index: int, shift: bool, ctrl: bool) -> None:
        """Route waypoint pick to selection and playback state per D-02."""
        if shift or ctrl:
            self._selection_state.toggle(index)
        else:
            self._selection_state.select_single(index)
        self._playback_state.set_index(index)

    def _on_waypoint_changed(self, index: int) -> None:
        """Update GL highlight, code panel, and property panel."""
        if self._gl_ready():
            self._gl_widget.set_highlight_index(index)
        move = self._playback_state.current_move
        if move is not None:
            self._code_panel.highlight_line(move.source_line)
        self._update_property_panel()

    def _on_selection_changed(self, selected: frozenset) -> None:
        """Update GL selection rendering and property panel."""
        if self._gl_ready():
            self._gl_widget.set_selected_indices(selected)
        self._update_property_panel()

    def _update_property_panel(self) -> None:
        """Refresh property panel from current PlaybackState index + SelectionState count."""
        idx = self._playback_state.current_index
        point = self._edit_model.point_at(idx) if idx >= 0 else None
        count = len(self._selection_state.selected_indices)
        self._property_panel.update_from_point(point, count)

    def _on_dirty_changed(self, dirty: bool) -> None:
        """Add or remove asterisk prefix from title bar."""
        title = self.windowTitle()
        if title.startswith("* "):
            title = title[2:]
        if dirty:
            self.setWindowTitle(f"* {title}")
        else:
            self.setWindowTitle(title)

    # -- Phase 5: Edit signal handlers ------------------------------------------

    def _on_offset_applied(self, dx: float, dy: float, dz: float) -> None:
        """Apply XYZ offset to all selected points (D-12)."""
        indices = sorted(self._selection_state.selected_indices)
        if not indices:
            return
        delta = np.array([dx, dy, dz], dtype=np.float64)
        self._edit_model.apply_offset(indices, delta)

    def _on_speed_changed(self, new_speed: str) -> None:
        """Set speed on all selected points (D-13)."""
        indices = sorted(self._selection_state.selected_indices)
        if not indices:
            return
        self._edit_model.set_property(indices, "speed", new_speed)

    def _on_zone_changed(self, new_zone: str) -> None:
        """Set zone on all selected points (D-13)."""
        indices = sorted(self._selection_state.selected_indices)
        if not indices:
            return
        self._edit_model.set_property(indices, "zone", new_zone)

    def _on_laser_changed(self, laser_on: bool) -> None:
        """Set laser state on all selected points (D-13)."""
        indices = sorted(self._selection_state.selected_indices)
        if not indices:
            return
        self._edit_model.set_property(indices, "laser_on", laser_on)

    def _on_delete_requested(self, mode: str) -> None:
        """Delete all selected points with reconnect/break (D-14)."""
        indices = sorted(self._selection_state.selected_indices)
        if not indices:
            return
        self._edit_model.delete_points(indices, mode)
        self._selection_state.clear()

    def _on_insert_requested(self, dx: float, dy: float, dz: float) -> None:
        """Insert new point after selected point (D-09, D-10, D-15)."""
        indices = sorted(self._selection_state.selected_indices)
        if len(indices) != 1:
            return
        source_index = indices[0]
        delta = np.array([dx, dy, dz], dtype=np.float64)
        new_index = self._edit_model.insert_after(source_index, delta)
        # Auto-select the new point for chaining (D-10)
        self._selection_state.select_single(new_index)

    def _on_points_changed(self) -> None:
        """Rebuild geometry from EditModel and refresh all views."""
        if self._parse_result is None:
            return
        edited_moves = self._edit_model.build_edited_moves()
        synthetic_result = replace(self._parse_result, moves=edited_moves)
        if self._gl_ready():
            self._gl_widget.update_scene(synthetic_result)
        # Update moves list without resetting current index (preserves scroll position)
        self._playback_state.update_moves(edited_moves)
        # Refresh property panel for current selection
        self._update_property_panel()

    def _on_code_line_clicked(self, line: int) -> None:
        """Find a move matching the clicked source line and select it."""
        for i, move in enumerate(self._playback_state._moves):
            if move.source_line == line:
                self._selection_state.select_single(i)
                self._playback_state.set_index(i)
                return

    def _on_proc_changed(self, proc_name: str) -> None:
        """Filter moves by selected PROC and update state + geometry."""
        if self._parse_result is None:
            return
        self._selection_state.clear()
        self._apply_proc_filter(proc_name)

    def _apply_proc_filter(self, proc_name: str) -> None:
        """Filter moves by PROC name and update PlaybackState + GL widget.

        Uses EditModel's edited moves as the base list so that modifications
        (deleted points, changed positions) are reflected when switching PROCs.

        Preserves the current playback position by matching source_line
        after the filter is applied.
        """
        if self._parse_result is None:
            return

        # Remember current position
        cur_move = self._playback_state.current_move
        cur_source_line = cur_move.source_line if cur_move is not None else -1

        # Use edited moves from EditModel as the canonical source
        all_moves = self._edit_model.build_edited_moves()

        if proc_name == "All PROCs":
            filtered_moves = all_moves
        else:
            proc_range = self._parse_result.proc_ranges.get(proc_name)
            if proc_range is None:
                filtered_moves = all_moves
            else:
                start_line, end_line = proc_range
                filtered_moves = [
                    m for m in all_moves
                    if start_line <= m.source_line <= end_line
                ]

        self._playback_state.set_moves(filtered_moves)

        # Create a filtered ParseResult copy and update GL scene
        filtered_result = replace(self._parse_result, moves=filtered_moves)
        self._gl_widget.update_scene(filtered_result)

        # Restore position: find matching source_line, or clamp to last index
        if filtered_moves and cur_source_line >= 0:
            restore_idx = len(filtered_moves) - 1  # default: last
            for i, m in enumerate(filtered_moves):
                if m.source_line >= cur_source_line:
                    restore_idx = i
                    break
            self._playback_state.set_index(restore_idx)

    # -- File loading --------------------------------------------------------

    def _save_as(self) -> None:
        """Export modified .mod file via Save As dialog."""
        if self._parse_result is None:
            return
        # Default filename: originalname_modified.mod
        default_name = ""
        if self._current_file_path is not None:
            default_name = str(self._current_file_path.with_stem(
                self._current_file_path.stem + "_modified"
            ))
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save As", default_name,
            "RAPID Module (*.mod);;All Files (*)",
        )
        if not file_path:
            return
        save_path = Path(file_path).resolve()
        # Prevent overwriting the original
        if self._current_file_path is not None and save_path == self._current_file_path:
            QMessageBox.warning(
                self, "Warning",
                "Cannot overwrite the original file. Choose a different name.",
            )
            return
        try:
            from rapid_viewer.export.mod_writer import export_mod

            patched = export_mod(
                source_text=self._parse_result.source_text,
                points=self._edit_model._points,
                targets=self._parse_result.targets,
            )
            save_path.write_text(patched, encoding=self._file_encoding)
            # Mark undo stack as clean (removes dirty indicator)
            self._edit_model.undo_stack.setClean()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Export Error", f"Failed to save file:\n{e}")

    def _open_file(self) -> None:
        """Open a native file dialog and load the selected .mod file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open RAPID Module",
            self._last_open_dir,
            "RAPID Module (*.mod);;All Files (*)",
        )
        if file_path:
            self._last_open_dir = str(Path(file_path).parent)
            self.load_file(file_path)

    def load_file(self, file_path: str) -> None:
        """Load and parse a .mod file. Public method also used by tests.

        Reads the file with UTF-8 / latin-1 encoding fallback (read_mod_file
        handles Windows-1252 encoded files from RobotStudio), parses the content,
        stores the ParseResult internally, and updates the title bar with the
        filename.

        Args:
            file_path: Absolute or relative path to the .mod file.
        """
        path = Path(file_path)
        try:
            from rapid_viewer.parser.rapid_parser import parse_module, read_mod_file

            source, encoding = read_mod_file(path)
            self._current_file_path = path.resolve()
            self._file_encoding = encoding
            self._last_open_dir = str(path.resolve().parent)
            self._parse_result = parse_module(source)

            # Clear selection before loading new data (Pitfall 4)
            self._selection_state.clear()
            # Initialize EditModel with parsed moves (Pitfall 3)
            self._edit_model.load(self._parse_result.moves)

            self.setWindowTitle(f"{path.name} - {APP_TITLE}")

            # Populate code panel with source text
            self._code_panel.set_source(self._parse_result.source_text)

            # Update PROC combo box
            self._proc_combo.blockSignals(True)
            self._proc_combo.clear()
            self._proc_combo.addItem("All PROCs")
            for proc in self._parse_result.procedures:
                self._proc_combo.addItem(proc)
            self._proc_combo.blockSignals(False)

            # Set moves in PlaybackState
            self._playback_state.set_moves(self._parse_result.moves)

            # Update GL scene (update_scene handles context-not-ready internally)
            self._gl_widget.update_scene(self._parse_result)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{e}")

    @property
    def parse_result(self):
        """The ParseResult from the most recently loaded file, or None."""
        return self._parse_result
