# Phase 4: Edit Infrastructure, Selection, and Inspection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-01
**Phase:** 04-edit-infrastructure-selection-and-inspection
**Areas discussed:** Selection model design, Property panel placement, Selection visual style, EditModel structure

---

## Selection Model Design

| Option | Description | Selected |
|--------|-------------|----------|
| Separate SelectionState (Recommended) | New SelectionState class alongside PlaybackState. PlaybackState stays as playback cursor, SelectionState manages a set of selected indices. | :heavy_check_mark: |
| Extend PlaybackState | Add selected_indices set directly to PlaybackState. Simpler but mixes concerns. | |
| Replace PlaybackState | New unified model replaces PlaybackState entirely. Clean slate but requires rewiring all consumers. | |

**User's choice:** Separate SelectionState
**Notes:** None

### Follow-up: Click Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Updates both states (Recommended) | Plain click sets current AND replaces selection. Shift/Ctrl toggles selection, current moves to clicked point. | :heavy_check_mark: |
| Selection-first | Click only updates SelectionState. PlaybackState only changed by toolbar. | |
| You decide | Claude chooses simplest approach. | |

**User's choice:** Updates both states
**Notes:** None

---

## Property Panel Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Below code panel (Recommended) | Vertical split in right pane: code on top, properties on bottom. | :heavy_check_mark: |
| Below 3D viewport | Property panel under 3D view on left side. | |
| Collapsible right dock | Separate dockable panel on far right. | |

**User's choice:** Below code panel
**Notes:** None

### Follow-up: Multi-select Display

| Option | Description | Selected |
|--------|-------------|----------|
| Last clicked point (Recommended) | Shows properties of most recently clicked point. Count shown as header. | :heavy_check_mark: |
| Common values only | Shows shared values, different values show "(mixed)". | |
| Scrollable list | Table of all selected point properties. | |

**User's choice:** Last clicked point
**Notes:** None

---

## Selection Visual Style

| Option | Description | Selected |
|--------|-------------|----------|
| Color change (Recommended) | Selected markers turn cyan/white. Current stays red/magenta. Unselected stay yellow. | :heavy_check_mark: |
| Color + size change | Selected change color AND render larger. Current is largest. | |
| You decide | Claude picks simplest approach. | |

**User's choice:** Color change only
**Notes:** None

---

## EditModel Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Mutable wrapper list (Recommended) | EditModel holds list of mutable EditPoint objects wrapping frozen MoveInstructions. | :heavy_check_mark: |
| Overlay/diff approach | Keep ParseResult as-is, store dict of changes. | |
| Deep copy ParseResult | Make tokens non-frozen or deep-copy into mutable versions. | |

**User's choice:** Mutable wrapper list
**Notes:** None

### Follow-up: QUndoStack Ownership

| Option | Description | Selected |
|--------|-------------|----------|
| EditModel owns it (Recommended) | QUndoStack lives inside EditModel. Encapsulates all mutation logic. | :heavy_check_mark: |
| MainWindow owns it | QUndoStack created in MainWindow, passed to EditModel. | |
| You decide | Claude picks based on signal architecture. | |

**User's choice:** EditModel owns it
**Notes:** None

---

## Claude's Discretion

- Signal names for SelectionState
- Exact color values for selected vs current markers
- Internal EditPoint field layout
- QUndoCommand subclass structure

## Deferred Ideas

None -- discussion stayed within phase scope
