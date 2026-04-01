# Phase 5: Modification Operations - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning

<domain>
## Phase Boundary

User can modify selected waypoints -- adjust coordinates via offset input, change speed/zone/laser properties, delete waypoints with topology options (reconnect or break path), and continuously insert new points by offset -- with all operations undoable via Ctrl+Z/Y.

</domain>

<decisions>
## Implementation Decisions

### Edit UI Entry Points
- **D-01:** Convert PropertyPanel from read-only to inline editable. Position X/Y/Z remain read-only (display current values). Add dX/dY/dZ offset input fields (QLineEdit) below position, with an "Apply Offset" button.
- **D-02:** Speed and zone fields become free-text QLineEdit inputs (not dropdowns). Users type RAPID speeddata/zonedata names directly (v500, vmax, z10, fine, etc.). Supports custom names without validation.
- **D-03:** Laser state becomes a QComboBox toggle (ON/OFF).
- **D-04:** Property changes (speed, zone, laser) commit immediately on Enter key press or dropdown change. Each change creates one QUndoCommand. No "Apply" button needed for property edits -- undo is the safety net.
- **D-05:** Offset fields retain their values after Apply (not reset to zero). Enables rapid repeated offsets at uniform spacing.

### Delete Workflow
- **D-06:** Delete button placed at the bottom of PropertyPanel, styled red, enabled only when points are selected. Keyboard shortcut: Del key.
- **D-07:** Delete triggers a confirmation dialog: "Delete N point(s)?" with three buttons: [Reconnect] (path stays continuous), [Break] (laser-off gap inserted), [Cancel]. One dialog for all selected points -- same topology choice applies to all.
- **D-08:** Reconnect = next move after deleted segment connects to the last move before it. Break = deleted segment becomes a laser-off gap (MoveJ or equivalent non-cutting move).

### Continuous Insertion (MOD-04)
- **D-09:** "Insert After" button in PropertyPanel, enabled when exactly one point is selected. Click opens/reuses the offset input section (dX/dY/dZ).
- **D-10:** Apply creates a new point after the selected point, with position = selected.pos + offset, properties copied from source point. New point becomes selected automatically, enabling chained insertion.
- **D-11:** Offset fields keep values between insertions (per D-05). User clicks Apply repeatedly for uniform spacing. Click elsewhere or select another point to stop inserting.

### Multi-Select Batch Behavior
- **D-12:** Offset Apply with multi-select: same dX/dY/dZ delta applied to ALL selected points. One compound QUndoCommand wrapping all individual moves.
- **D-13:** Speed/zone/laser change with multi-select: new value overwrites ALL selected points. One compound QUndoCommand.
- **D-14:** Delete with multi-select: one dialog for all selected points. Same reconnect/break choice applies to all. One compound QUndoCommand.
- **D-15:** Insert After is disabled during multi-select (only works with single selection per D-09).

### Claude's Discretion
- QUndoCommand subclass naming and internal structure for each operation type
- Exact layout/spacing of new offset input fields within PropertyPanel
- How "reconnect" is implemented internally (whether to modify the next move's target or remap references)
- How "break" inserts a laser-off gap (implementation detail of the gap move)
- Signal names for edit operations (e.g., point_modified, points_deleted)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Model
- `src/rapid_viewer/ui/edit_model.py` -- EditModel with QUndoStack, EditPoint with mutable fields (pos, speed, zone, laser_on, deleted). All mutation methods go here.
- `src/rapid_viewer/parser/tokens.py` -- Frozen MoveInstruction, RobTarget; EditPoint.original references these for diff/export
- `src/rapid_viewer/ui/selection_state.py` -- SelectionState manages selected indices; batch edits read from this

### UI
- `src/rapid_viewer/ui/property_panel.py` -- Currently read-only QLabels; Phase 5 converts to editable inputs
- `src/rapid_viewer/ui/main_window.py` -- Signal wiring hub; connects PropertyPanel edit signals to EditModel mutation methods
- `src/rapid_viewer/ui/playback_state.py` -- PlaybackState.current_index is the "last clicked" point shown in PropertyPanel

### Rendering
- `src/rapid_viewer/renderer/toolpath_gl_widget.py` -- Must refresh geometry after edits; existing update_scene() pattern
- `src/rapid_viewer/renderer/geometry_builder.py` -- Rebuilds vertex buffers from EditModel data after mutations

### Architecture
- `.planning/phases/04-edit-infrastructure-selection-and-inspection/04-CONTEXT.md` -- Phase 4 decisions (D-01 through D-09) that this phase builds on
- `.planning/REQUIREMENTS.md` -- MOD-01, MOD-02, MOD-03, MOD-04 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EditModel.undo_stack` (QUndoStack): Ready to receive QUndoCommands from Phase 5 mutation methods
- `EditPoint` fields (pos, speed, zone, laser_on, deleted): All mutable fields already defined in Phase 4
- `PropertyPanel.update_from_point()`: Pattern for populating panel from EditPoint -- extend for editable mode
- `SelectionState.selected()`: Returns frozenset[int] of selected indices for batch operations

### Established Patterns
- Qt signal/slot for all state changes (no direct method calls between components)
- `EditModel.dirty_changed(bool)` signal updates title bar asterisk
- Full geometry rebuild via `build_geometry()` after data changes (not incremental)
- `blockSignals()` to prevent cascading during programmatic updates

### Integration Points
- PropertyPanel: Convert QLabels to QLineEdit/QComboBox, add offset section and action buttons
- EditModel: Add mutation methods (apply_offset, set_speed, set_zone, set_laser, delete_points, insert_after) each creating QUndoCommands
- MainWindow: Wire PropertyPanel edit signals to EditModel methods, refresh GL widget after mutations
- ToolpathGLWidget: Call update_scene() after EditModel changes to rebuild geometry

</code_context>

<specifics>
## Specific Ideas

No specific requirements -- open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 05-modification-operations*
*Context gathered: 2026-04-01*
