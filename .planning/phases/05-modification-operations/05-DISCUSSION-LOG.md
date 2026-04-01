# Phase 5: Modification Operations - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 05-modification-operations
**Areas discussed:** Edit UI entry points, Delete workflow, Continuous insertion, Multi-select edits

---

## Edit UI Entry Points

### Q1: How should the user edit waypoint properties?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline editable panel | Convert PropertyPanel QLabels to QLineEdit/QComboBox, offset inputs below position | ✓ |
| Separate edit dialog | Keep PropertyPanel read-only, 'Modify' toolbar button opens modal dialog | |
| Toolbar-based inputs | Offset fields in edit toolbar, speed/zone in PropertyPanel dropdowns | |

**User's choice:** Inline editable panel
**Notes:** Feels like a property inspector (Unity Inspector style). All editing in one place.

### Q2: Position editing -- absolute or offset only?

| Option | Description | Selected |
|--------|-------------|----------|
| Offset only | X/Y/Z read-only, user enters dX/dY/dZ delta values and clicks Apply | ✓ |
| Both absolute and offset | X/Y/Z editable for direct entry AND dX/dY/dZ for offset | |

**User's choice:** Offset only
**Notes:** Matches MOD-01 spec ('offset input'), safer against accidental absolute overwrites.

### Q3: Speed and zone input method?

| Option | Description | Selected |
|--------|-------------|----------|
| Free-text input | QLineEdit, user types any RAPID speeddata/zonedata name | ✓ |
| Dropdown with common values | QComboBox pre-filled with common ABB values + editable field | |
| You decide | Claude picks best approach | |

**User's choice:** Free-text input
**Notes:** Supports custom speeddata/zonedata names without validation.

### Q4: Property change commit behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Immediate on Enter/change | Enter key or dropdown change commits; each change = one QUndoCommand | ✓ |
| Apply button for all | Changes staged until user clicks Apply | |

**User's choice:** Immediate on Enter/change
**Notes:** Fast workflow, undo is the safety net.

---

## Delete Workflow

### Q1: Delete confirmation UI?

| Option | Description | Selected |
|--------|-------------|----------|
| Confirmation dialog | Dialog with [Reconnect] [Break] [Cancel] buttons | ✓ |
| Inline panel options | Panel expands with radio buttons + Confirm | |
| Default reconnect, Shift for break | Delete always reconnects, Shift+Delete to break | |

**User's choice:** Confirmation dialog
**Notes:** Clear, no ambiguity, standard UX.

### Q2: Delete button location?

| Option | Description | Selected |
|--------|-------------|----------|
| PropertyPanel bottom | Red Delete button, enabled when selected. Del key shortcut. | ✓ |
| Edit menu only | Delete only in Edit menu + Del key | |
| Both panel and toolbar | Button in PropertyPanel AND toolbar icon | |

**User's choice:** PropertyPanel bottom
**Notes:** Keeps all editing actions in one place.

---

## Continuous Insertion

### Q1: Insertion workflow?

| Option | Description | Selected |
|--------|-------------|----------|
| Insert button + repeat | Insert After button, enter offset, Apply creates point, new point auto-selected for chaining | ✓ |
| Modal insert mode | Toggle insert mode via toolbar, each Apply creates point until Esc | |
| You decide | Claude picks simplest approach | |

**User's choice:** Insert button + repeat
**Notes:** New point becomes selected automatically, enabling chained insertion by repeated Apply.

### Q2: Offset field behavior after Apply?

| Option | Description | Selected |
|--------|-------------|----------|
| Keep values | Offset fields retain dX/dY/dZ values after Apply | ✓ |
| Reset to zero | Offset fields reset to 0/0/0 after Apply | |

**User's choice:** Keep values
**Notes:** Common in CAD tools for repetitive operations at uniform spacing.

---

## Multi-Select Edits

### Q1: Multi-select offset behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Same offset to all | All selected points move by same dX/dY/dZ delta | ✓ |
| Offset relative to first | First point moves by offset, others shift proportionally | |

**User's choice:** Same offset to all
**Notes:** Standard CAD behavior. One compound QUndoCommand.

### Q2: Multi-select property changes?

| Option | Description | Selected |
|--------|-------------|----------|
| Overwrite all selected | New value sets ALL selected points | ✓ |
| Only change current point | Edits only affect last-clicked point | |

**User's choice:** Overwrite all selected
**Notes:** Simple and predictable. One compound QUndoCommand.

### Q3: Multi-select delete dialog?

| Option | Description | Selected |
|--------|-------------|----------|
| One dialog for all | Single dialog, same topology choice for all points | ✓ |
| Per-point choice | Each point gets own reconnect/break decision | |

**User's choice:** One dialog for all
**Notes:** Simple. One compound undo command.

---

## Claude's Discretion

- QUndoCommand subclass naming and structure
- Exact layout/spacing of offset input fields in PropertyPanel
- Internal implementation of "reconnect" and "break" topology operations
- Signal names for edit operations

## Deferred Ideas

None -- discussion stayed within phase scope
