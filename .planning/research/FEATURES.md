# Feature Research

**Domain:** Robot Toolpath Visualization / RAPID Code Verification
**Researched:** 2026-03-30
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or unusable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| .mod file loading via file dialog | Entry point to the app; without it nothing works | LOW | Standard file dialog, drag-and-drop is a nice bonus |
| RAPID movement instruction parsing (MoveL, MoveJ, MoveC, MoveAbsJ) | Core data extraction; the 4 move types cover 95%+ of real programs | MEDIUM | MoveC requires CirPoint intermediate target handling; MoveAbsJ has joint-space-only coords |
| robtarget / jointtarget data parsing | Positions are the raw material for visualization | MEDIUM | Quaternion orientation (q1-q4), config data (cf1-cf6), external axes |
| 3D path rendering with move-type distinction | Users need to see linear vs joint moves at a glance; every competitor does this | MEDIUM | MoveL=solid line, MoveJ=dashed/different color, MoveC=arc. Color-coding is standard in G-code viewers |
| Waypoint markers in 3D view | Users need to identify individual positions; dots or small axes at each robtarget | LOW | Small spheres or cross markers at each target position |
| Mouse orbit/zoom/pan camera controls | Standard 3D navigation; users expect this from any 3D viewer | MEDIUM | Trackball or arcball rotation, scroll zoom, middle-click pan. Must feel responsive |
| Coordinate axes indicator | Spatial orientation reference; users need to know which way is X/Y/Z | LOW | Standard XYZ axis widget in corner of viewport |
| Step-through playback (forward/back) | Lets user walk through program instruction by instruction; core verification workflow | MEDIUM | Step forward, step back, highlight current segment |
| Code-to-3D bidirectional linking | The core value proposition per PROJECT.md; click a point to see code, click code to see point | HIGH | This is the killer feature that ties the viewer together. NC Viewer and G-code tools do line-by-line linking |
| Syntax-highlighted RAPID code panel | Users need to read the code alongside the 3D view; plain text is insufficient | MEDIUM | Keyword highlighting for RAPID (MoveL, MoveJ, robtarget, PROC, etc.) |

### Differentiators (Competitive Advantage)

Features that set this tool apart from RobotStudio and general-purpose OLP software. The key differentiator is **speed and simplicity** -- open a .mod file and instantly see the path, no robot model setup, no project creation, no license headaches.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Instant file-to-visualization (zero config) | RobotStudio requires creating a station, importing robot model, setting up controller. This tool: open file, see path. 2 seconds vs 2 minutes | LOW | This is an architecture choice, not a feature to build -- keep the app simple |
| TCP orientation visualization at waypoints | Show tool orientation as small coordinate frames at each point; helps catch orientation errors that are invisible in position-only views | MEDIUM | Render small RGB axis triads from quaternion data. Critical for welding/painting validation |
| Speed/zone data overlay | Show speeddata and zonedata values alongside the path; users catch "why is this segment slow?" or "why isn't this a fine point?" | MEDIUM | Text labels or color gradient mapped to speed values |
| Playback animation with speed control | Animate a marker along the path at adjustable speed (0.25x to 10x); NC Viewer-style playback | MEDIUM | Smooth interpolation along segments, speed slider, play/pause/stop |
| Multi-procedure support | Real .mod files contain multiple PROCs; users need to select which procedure to visualize or see all | MEDIUM | Dropdown or list to select active PROC; highlight only that procedure's path |
| Path statistics panel | Total path length, point count, move type breakdown, estimated cycle time (from speed data) | LOW | Calculated from parsed data; useful for quick validation |
| Search/filter in code panel | Find specific targets or instructions in large programs (500+ lines) | LOW | Standard text search in the code panel |
| Wobj (work object) frame visualization | Show the coordinate frame of the active work object; many programs use non-default wobjs | MEDIUM | Parse WobjData, render as a larger coordinate frame. Transforms all robtargets into the correct frame |
| Export path as CSV/point cloud | Let users export parsed waypoints for use in other tools or spreadsheets | LOW | Simple data export from already-parsed structures |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but are wrong for v1 of a lightweight RAPID viewer.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Robot arm 3D model / kinematic simulation | "I want to see the robot move" | Requires robot model library, DH parameters, IK/FK solver, joint limits, collision meshes. Massive complexity for marginal value in a code verifier | TCP path visualization with orientation frames gives 90% of the validation value at 5% of the cost. Users who need full sim already have RobotStudio |
| RAPID code editing | "Let me fix errors right here" | Turns a viewer into an IDE; undo/redo, syntax validation, file saving with backup, module structure integrity. Feature creep | Open-in-external-editor button. The tool is a viewer, not an editor |
| Collision detection | "Can the robot reach this?" | Requires robot model, cell geometry, physics engine. Full OLP territory | Out of scope entirely. This tool validates path intent, not physical feasibility |
| Real-time robot connection | "Stream positions from the real robot" | Network protocol complexity (EGM/RAPID server), safety implications, latency handling | Completely different product category. Stay offline |
| Multi-file project support (.pgf parsing) | "Load the whole project structure" | ABB project files reference multiple modules, system modules, EIO config. Parsing the full project structure is a rabbit hole | Support loading individual .mod files. Add multi-module loading in v1.x if needed |
| Inverse kinematics / reachability analysis | "Can the robot reach point X?" | Requires specific robot model kinematics, joint limits database | Show raw position coordinates; let users verify reachability in RobotStudio |
| CAD model import (STEP/IGES) | "Show my workpiece alongside the path" | 3D CAD parsing is a major undertaking; format complexity, tessellation, positioning | Maybe v2+ with simple STL import only. Not v1 |

## Feature Dependencies

```
[.mod File Loading]
    +--requires--> [RAPID Parser (move instructions)]
                       +--requires--> [robtarget/jointtarget Data Parsing]
                       +--enables---> [3D Path Rendering]
                       +--enables---> [Code Panel with Syntax Highlight]

[3D Path Rendering]
    +--requires--> [Camera Controls (orbit/zoom/pan)]
    +--requires--> [Coordinate Axes Indicator]
    +--enables---> [Waypoint Markers]
    +--enables---> [TCP Orientation Visualization]
    +--enables---> [Move-Type Color Coding]

[Step-Through Playback]
    +--requires--> [3D Path Rendering]
    +--requires--> [Code Panel]
    +--enables---> [Code-to-3D Bidirectional Linking]
    +--enables---> [Playback Animation with Speed Control]

[Code-to-3D Bidirectional Linking]
    +--requires--> [Step-Through Playback]
    +--requires--> [Code Panel with Syntax Highlight]
    +--requires--> [Waypoint Markers]

[Multi-Procedure Support]
    +--requires--> [RAPID Parser]
    +--enhances--> [Code Panel]
    +--enhances--> [3D Path Rendering]

[Speed/Zone Data Overlay]
    +--requires--> [RAPID Parser (speeddata/zonedata extraction)]
    +--enhances--> [3D Path Rendering]

[Wobj Frame Visualization]
    +--requires--> [robtarget Data Parsing]
    +--requires--> [3D Path Rendering]

[Path Statistics]
    +--requires--> [RAPID Parser]
    +--independent of--> [3D rendering (can be calculated without display)]
```

### Dependency Notes

- **Code-to-3D Linking requires Step-Through + Code Panel + Waypoint Markers:** All three must exist before bidirectional navigation is possible. This is the most dependency-heavy feature and should be the last table-stakes item built.
- **3D Path Rendering requires Camera Controls:** Without orbit/zoom/pan, the 3D view is unusable. Camera controls must be implemented alongside or before path rendering.
- **Multi-Procedure Support requires RAPID Parser:** The parser must understand PROC boundaries, not just individual move instructions. This should be designed into the parser from the start, not retrofitted.
- **Wobj Frame Visualization requires robtarget parsing with WobjData:** If the parser ignores the wobj argument in Move instructions, all positions will be in the wrong coordinate frame for non-default work objects. Design the parser to capture wobj references early.

## MVP Definition

### Launch With (v1)

Minimum viable product -- what's needed for a robot engineer to open a .mod file and verify their toolpath.

- [ ] .mod file loading (file dialog) -- entry point
- [ ] RAPID parser: MoveL, MoveJ, MoveC, MoveAbsJ instruction extraction -- core data
- [ ] RAPID parser: robtarget and jointtarget data type extraction -- position data
- [ ] 3D path rendering with move-type color distinction -- visual output
- [ ] Waypoint markers at each robtarget -- position identification
- [ ] Mouse camera controls (orbit, zoom, pan) -- navigation
- [ ] XYZ coordinate axes indicator -- spatial reference
- [ ] Step forward/back through waypoints -- sequential verification
- [ ] RAPID code panel with syntax highlighting -- code context
- [ ] Bidirectional code-to-3D linking -- the core value proposition

### Add After Validation (v1.x)

Features to add once core viewer is working and users provide feedback.

- [ ] TCP orientation frames at waypoints -- when users report orientation validation needs
- [ ] Playback animation with speed control -- when step-through feels too slow for long programs
- [ ] Speed/zone data text overlay -- when users ask "why is this segment configured this way?"
- [ ] Multi-procedure support (PROC selection) -- when users load files with multiple routines
- [ ] Path statistics panel (length, point count, move breakdown) -- low effort, high info value
- [ ] Search in code panel -- when files exceed ~200 lines and scrolling is painful
- [ ] Drag-and-drop file loading -- convenience enhancement

### Future Consideration (v2+)

Features to defer until the core tool has proven its value.

- [ ] Wobj frame visualization and coordinate transform -- complex but important for multi-wobj programs
- [ ] Export path as CSV/point cloud -- for integration with other tools
- [ ] Simple STL workpiece overlay -- for spatial context without full CAD support
- [ ] Multi-module loading (load several .mod files into one view) -- for programs split across modules
- [ ] Configuration file (.cfg) parsing for tool definitions -- richer metadata

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| .mod file loading | HIGH | LOW | P1 |
| RAPID move instruction parsing | HIGH | MEDIUM | P1 |
| robtarget/jointtarget parsing | HIGH | MEDIUM | P1 |
| 3D path rendering (color-coded) | HIGH | MEDIUM | P1 |
| Waypoint markers | HIGH | LOW | P1 |
| Camera controls (orbit/zoom/pan) | HIGH | MEDIUM | P1 |
| Coordinate axes indicator | MEDIUM | LOW | P1 |
| Step-through playback | HIGH | MEDIUM | P1 |
| Code panel with syntax highlight | HIGH | MEDIUM | P1 |
| Code-to-3D bidirectional linking | HIGH | HIGH | P1 |
| TCP orientation frames | HIGH | MEDIUM | P2 |
| Playback animation + speed | MEDIUM | MEDIUM | P2 |
| Speed/zone overlay | MEDIUM | MEDIUM | P2 |
| Multi-procedure support | MEDIUM | MEDIUM | P2 |
| Path statistics | MEDIUM | LOW | P2 |
| Code search | MEDIUM | LOW | P2 |
| Wobj visualization | MEDIUM | HIGH | P3 |
| CSV/point export | LOW | LOW | P3 |
| STL workpiece overlay | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch (table stakes)
- P2: Should have, add in v1.x
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | RobotStudio (ABB) | Roboguide (Fanuc) | RoboDK | NC Viewer (G-code) | Our Approach |
|---------|-------------------|-------------------|--------|---------------------|-------------|
| File load to path view | Slow: create station, import controller, load module | Slow: similar setup process | Moderate: import then configure | Instant: paste/open G-code | Instant: open .mod, see path |
| 3D path visualization | Full robot + path | Full robot + path | Full robot + path | Toolpath lines only | Toolpath lines + orientation |
| Code-to-path linking | Right-click "Go to declaration" | Limited | Limited | Line-by-line highlight | Click-bidirectional linking |
| Move type distinction | Color-coded in path view | Color-coded | Color-coded | Rapid vs cut moves colored | Color + line style (solid/dash) |
| Playback / animation | Full kinematic simulation | Full simulation | Full simulation | Speed-controlled playback | Step + animated playback |
| Cost | Free (basic) / Licensed | Licensed ($$$) | Licensed ($30/mo+) | Free (web) | Free (desktop) |
| Setup time | 5-15 minutes per station | 5-15 minutes | 2-5 minutes | Instant | Instant |
| RAPID-specific | Yes (native) | No (TP language) | Multi-brand | No (G-code only) | Yes (RAPID-native) |

### Competitive Position

This tool occupies a niche that none of the competitors address well: **instant, zero-config RAPID toolpath visualization**. RobotStudio is powerful but heavyweight. G-code viewers are instant but don't understand RAPID. This tool combines the speed of a G-code viewer with RAPID-native parsing. The target user is someone who already has a .mod file and just wants to see if the path looks right before deploying.

## Sources

- [ABB RobotStudio Desktop](https://www.abb.com/global/en/areas/robotics/products/software/robotstudio-suite/robotstudio-desktop) -- feature overview
- [FANUC ROBOGUIDE](https://www.fanucamerica.com/products/robots/roboguide) -- feature set
- [FANUC ROBOGUIDE v10 announcement](https://www.therobotreport.com/fanuc-unveils-roboguide-v10-robot-simulation-software/) -- latest features
- [RoboDK Documentation - Path Input](https://robodk.com/doc/en/Robot-Machining-Path-input.html) -- toolpath features
- [NC Viewer](https://ncviewer.com/) -- G-code viewer features as closest analog
- [CNC Cookbook NC Viewer Guide](https://www.cnccookbook.com/nc-viewer/) -- G-code viewer feature analysis
- [ABB RAPID Technical Reference Manual](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf) -- MoveL/MoveJ/MoveC/MoveAbsJ specifications
- [abb_motion_program_exec (GitHub)](https://github.com/rpiRobotics/abb_motion_program_exec) -- RAPID motion program parsing reference
- [ABB RAPID Utility Library](https://github.com/ernell/ABB-RAPID-UTILITY-LIBRARY) -- RAPID syntax reference

---
*Feature research for: ABB RAPID Toolpath Viewer*
*Researched: 2026-03-30*
