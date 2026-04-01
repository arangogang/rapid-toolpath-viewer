# Feature Landscape: Toolpath Editing (Milestone v1.1)

**Domain:** Toolpath editor for ABB RAPID robot programs (.mod files)
**Researched:** 2026-04-01
**Confidence:** MEDIUM-HIGH
**Context:** Extending an existing read-only toolpath viewer into an editing tool. The viewer already has 3D rendering, arcball camera, playback, code panel with syntax highlighting, bidirectional click-to-code linking, and PROC filtering.

## Table Stakes

Features users expect when a tool claims "toolpath editing." Missing any of these makes the product feel broken or incomplete for a robot engineer doing pre-upload verification and correction.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Single waypoint selection in 3D | Every editor needs selection before action. Already partially built (ray-cast picking exists for playback highlighting). | Low | Extend existing `waypoint_clicked` signal. Need visual distinction between "playback highlight" and "edit selection." |
| Waypoint info panel | Engineers must see coordinates, speed, zone, tool, wobj, laser state at a glance. RobotStudio and RoboDK both show target properties on selection. | Low | Read-only panel displaying MoveInstruction + RobTarget fields. Dock widget or side panel below the code panel. |
| Coordinate modification (X, Y, Z offset) | The most common edit: adjusting waypoint position. ABB forum threads confirm this is the #1 request for simple program editors. Must support both absolute coordinate entry and relative offset. | Medium | Requires mutable data model (current tokens are frozen dataclasses). "Continuous add" means applying same offset repeatedly to shift a group of points. |
| Speed/zone property modification | Second most common edit after position. Engineers routinely need to change v100 to v500 or zone z10 to fine. | Low | Dropdown or text input for speed/zone fields. Changes propagate to in-memory MoveInstruction. |
| Laser on/off toggle | Domain-specific table stake for this application (laser welding/cutting). Engineers need to toggle SetDO state for segments. | Low | Toggle button in info panel. Must insert/modify SetDO statement in source. |
| Save As / Export modified .mod | Without export, editing is pointless. "Save As" (not overwrite) is safer for robot programs -- engineers keep the original. | Medium | Must regenerate valid RAPID source text from modified data model. Line-level text replacement strategy recommended. |
| Undo/Redo | Universal expectation for any editor. Qt provides QUndoStack (Command pattern) specifically for this. Without undo, users fear making changes. | Medium | QUndoStack with QUndoCommand subclasses for each edit type. Must be wired from the start -- retrofitting undo is extremely painful. |
| Delete waypoint | Engineers remove unnecessary or erroneous points. Must handle the "connect or disconnect" question: after deleting point B from A-B-C, should A connect to C or leave a gap? | Medium | Requires removing MoveInstruction from list, optionally adjusting adjacent segment connectivity, and updating all indices. |

## Differentiators

Features that set the product apart from just opening the file in a text editor. Not expected, but significantly increase value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-select waypoints | Select 2+ waypoints and batch-modify (offset all, change speed for all). Saves massive time vs. one-by-one editing. Professional CAM tools (Mastercam, BobCAD) all support this. | Medium | Shift+click or drag-box selection. Batch operations on selected set. |
| Batch offset with preview | Apply X/Y/Z offset to selection, see the result in 3D before confirming. "Continuous add" from requirements fits here -- apply same delta repeatedly. | Medium | Ghost/preview geometry showing proposed new positions. Confirm applies the change. |
| Real-time 3D update on edit | When user changes coordinate values in the info panel, the 3D view updates live (not after clicking "Apply"). | Low | Bind spinbox/input valueChanged signals to geometry rebuild. Must be performant -- partial VBO update, not full rebuild. |
| Visual diff: original vs modified | Show original path as faded/ghost overlay, modified path as solid. Engineers can visually verify their edits are correct. | Medium | Render original geometry with alpha blending alongside current geometry. Toggle on/off. |
| Dirty state indicator | Title bar shows "*" when unsaved changes exist. Prompt "Save changes?" on close. Standard editor behavior. | Low | Track modified flag, connect to QUndoStack cleanChanged signal. |
| Insert waypoint | Add a new waypoint between two existing ones (interpolated position). Less common than delete but valuable for path refinement. | High | Requires creating new robtarget declaration + new MoveInstruction, inserting at correct position in source text. Complex source regeneration. |
| Coordinate system display in info panel | Show coordinates in both world frame and active wobj frame. Engineers think in workobject coordinates. | Low | Transform pos by inverse wobj if wobj is defined. Display both. |

## Anti-Features

Features to explicitly NOT build in v1.1. Each has a clear reason for exclusion.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| In-place RAPID code editing (text editor mode) | Scope creep into IDE territory. Parsing modified RAPID text back into the data model is error-prone. The code panel is a viewer, not an editor. RobotStudio already does this. | Provide structured editing via info panel UI controls. The code panel stays read-only but updates to reflect changes. |
| Drag waypoints in 3D (gizmo/handle manipulation) | 3D gizmo interaction (translate handles, rotation rings) requires complex mouse-ray intersection math, occlusion handling, and axis constraint logic. High effort for v1.1. | Use numeric input fields for coordinate changes. Precise values are what robot engineers actually need (not approximate dragging). |
| Robot arm visualization / inverse kinematics | Massive scope. Requires robot model loading, DH parameter chains, joint limit checking. This is RobotStudio territory. | Show TCP path only (current approach). Engineers validate path geometry, not joint configurations, in this tool. |
| Collision detection | Requires workpiece CAD import, spatial indexing, mesh intersection. Way beyond scope. | Out of scope entirely. Engineers use RobotStudio for collision checks. |
| Path optimization / smoothing | Automatic modification of paths is dangerous for robot programs. Engineers want explicit control. | Provide manual editing tools. Never auto-modify without explicit user action. |
| Multi-file editing (.pgf project support) | .pgf projects reference multiple .mod files. Supporting project-level operations is a separate milestone. | Single .mod file editing only. Load one file, edit, save. |
| Waypoint reordering (drag to rearrange sequence) | Reordering moves changes program semantics (laser state, approach angles). Very error-prone without simulation. | Delete and re-insert if truly needed. Keep sequence integrity. |
| Overwrite save (Save, not Save As) | Robot programs going to production controllers should not be silently overwritten. "Save As" forces the engineer to be explicit about creating a modified copy. | Only provide "Save As" / Export. The original file is preserved. |

## Feature Dependencies

```
Waypoint Selection ──> Info Panel (must select before viewing info)
                   ──> Coordinate Modification (must select before editing)
                   ──> Property Modification (must select before editing)
                   ──> Delete Waypoint (must select before deleting)

Mutable Data Model ──> Coordinate Modification
                   ──> Property Modification
                   ──> Delete Waypoint
                   ──> All editing operations

Undo/Redo (QUndoStack) ──> Coordinate Modification (wrap in QUndoCommand)
                        ──> Property Modification (wrap in QUndoCommand)
                        ──> Delete Waypoint (wrap in QUndoCommand)

Source Regeneration ──> Save As / Export
                   <── All edit operations (must track changes for regeneration)

Coordinate Modification ──> Batch Offset (extends single-point to multi)
Multi-Select ──> Batch Offset (requires selection of multiple points)
```

Dependency chain summary:
1. **Mutable data model** must come first (current frozen dataclasses block all editing)
2. **Selection** and **undo infrastructure** can be built in parallel
3. **Individual edits** (coordinate, property, delete) depend on both selection and mutable model
4. **Save As** depends on source regeneration, which depends on all edit types being defined
5. **Multi-select and batch operations** extend single-edit features

## MVP Recommendation

Prioritize (in build order):

1. **Mutable data model** -- Unfreeze or wrap tokens for editing. Foundation for everything.
2. **Undo/Redo infrastructure** (QUndoStack) -- Wire early because retrofitting is painful. Every edit operation becomes a QUndoCommand from the start.
3. **Waypoint selection** (extend existing picking) -- Low effort, already partially built.
4. **Info panel** (read-only first, then editable) -- Shows immediate value, builds toward editing.
5. **Coordinate modification** with undo -- The highest-value edit operation.
6. **Speed/zone/laser modification** with undo -- Low complexity, high value.
7. **Delete waypoint** with connect/disconnect option -- Medium complexity.
8. **Save As / Export** -- Makes all edits permanent. Ship this as the capstone.

Defer to v1.2:
- **Multi-select and batch operations**: Valuable but adds significant UI complexity. Single-point editing covers 80% of use cases.
- **Insert waypoint**: High complexity (new robtarget generation, source insertion). Delete covers immediate needs.
- **Visual diff (original vs modified)**: Nice to have, not blocking.
- **3D drag gizmos**: High effort, low precision. Engineers prefer numeric input.

## Source Regeneration Strategy Note

The hardest technical problem in this milestone is not the UI -- it is **regenerating valid .mod source text** from modified data. Two approaches:

1. **Line-level text replacement**: Find the source line of the modified robtarget/MoveInstruction, replace just that line's values using regex. Preserves formatting, comments, and unmodified code. Fragile if source structure is unusual but matches how the parser already tracks `source_line` for every token.

2. **Full regeneration from AST**: Rebuild the entire .mod file from the parsed data model. Clean output but loses comments, formatting, and any RAPID code the parser does not understand.

**Recommendation**: Use **line-level replacement** for coordinate/property edits (surgical, preserves context) and handle deletion as line removal with optional reconnection. Full regeneration is overkill and risky for v1.1.

## Sources

- [ABB RobotStudio Suite](https://www.abb.com/global/en/areas/robotics/products/software/robotstudio-suite) -- reference for professional toolpath editing features
- [RoboDK Documentation: Tips and Tricks](https://robodk.com/doc/en/Tips-and-Tricks.html) -- waypoint editing workflows (F3 to modify, mouse wheel coordinate adjust)
- [BobCAD Toolpath Editor](https://bobcad.com/toolpath-editor-cad-cam-quick-tip-video/) -- CAM toolpath editing capabilities (modify, add, move, delete points)
- [Mastercam Transform Toolpath](https://www.engineering.com/mastercams-transform-toolpath/) -- batch transform operations
- [Qt QUndoStack Documentation](https://doc.qt.io/qt-6/qundostack.html) -- undo/redo framework for PyQt6
- [Qt Undo Framework Overview](https://doc.qt.io/qt-6/qundo.html) -- Command pattern implementation
- [ABB Forum: Modify robtarget coordinates](https://forums.robotstudio.com/discussion/10759/is-it-possible-to-modify-the-robtarget-pos-x-coordinate-of-a-robtarget-variable-automatically) -- confirms coordinate modification is a top user need
- [ABB Forum: Adjust robtarget data](https://forums.robotstudio.com/discussion/8547/simple-program-to-adjust-robtarget-data-help) -- community demand for simple target editing tools
- [ABB Developer Center: Undo-Redo](https://developercenter.robotstudio.com/api/robotstudio/articles/Concepts/Undo-Redo.html) -- RobotStudio's own undo/redo approach

---
*Feature research for: ABB RAPID Toolpath Viewer -- Milestone v1.1 Toolpath Editing*
*Researched: 2026-04-01*
