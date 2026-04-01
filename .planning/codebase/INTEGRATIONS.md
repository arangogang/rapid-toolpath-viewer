# External Integrations

**Analysis Date:** 2026-03-31

## APIs & External Services

**None.** This is a fully offline desktop application with zero network dependencies. No REST APIs, no cloud services, no telemetry, no update checking.

## Data Storage

**Databases:**
- None. No database of any kind.

**File Storage:**
- Local filesystem only
- Input: ABB RAPID `.mod` files (read-only, never modified)
- Output: None (viewer only, no file writing at runtime)

**Caching:**
- None. Parsed data lives in memory only (`ParseResult` dataclass in `src/rapid_viewer/parser/tokens.py`)

## Input File Format: ABB RAPID .mod

The sole external data integration is parsing ABB RAPID robot program files (`.mod`). This is the core value proposition of the application.

**File format details:**
- Extension: `.mod`
- Encoding: UTF-8 with latin-1/Windows-1252 fallback (`src/rapid_viewer/parser/rapid_parser.py` `read_mod_file()`)
- Origin: ABB RobotStudio IDE or ABB robot controllers
- Structure: Text-based, semicolon-delimited statements with `!` line comments

**Parsed constructs:**
- `MODULE` / `ENDMODULE` boundaries (`src/rapid_viewer/parser/patterns.py` `RE_MODULE`)
- `PROC` / `ENDPROC` procedure boundaries (`RE_PROC`, `RE_ENDPROC`)
- `robtarget` declarations: Cartesian pose `[[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax...]]` (`RE_ROBTARGET_DECL`)
- `jointtarget` declarations: Joint angles `[[j1..j6],[eax...]]` (`RE_JOINTTARGET_DECL`)
- `MoveL` / `MoveJ` / `MoveC` / `MoveAbsJ` instructions with target resolution (`RE_MOVEL`, `RE_MOVEJ`, `RE_MOVEC`, `RE_MOVEABSJ`)
- `Offs()` function for offset targets (`RE_OFFS`)
- `\WObj` optional work object parameter (`RE_WOBJ`)
- Inline robtarget literals (bracket data without named declaration)

**Parser architecture (two-pass):**
- Pass 1: Tokenize statements, extract all target declarations into lookup dicts (`src/rapid_viewer/parser/rapid_parser.py`)
- Pass 2: Extract move instructions, resolve target references against Pass 1 lookup dicts
- All regex patterns compiled at module level for performance (`src/rapid_viewer/parser/patterns.py`)

**Data model types (`src/rapid_viewer/parser/tokens.py`):**
- `RobTarget` - frozen dataclass: name, pos (ndarray shape 3), orient (ndarray shape 4), confdata, extjoint, source_line
- `JointTarget` - frozen dataclass: name, robax, extax, source_line
- `MoveInstruction` - frozen dataclass: move_type (enum), target, circle_point, joint_target, speed, zone, tool, wobj, source_line
- `ParseResult` - mutable dataclass: module_name, moves list, target dicts, source_text, procedures list, proc_ranges dict

## Authentication & Identity

**Auth Provider:**
- Not applicable. No user accounts, no authentication, no authorization.

## Monitoring & Observability

**Error Tracking:**
- None. Errors shown via `QMessageBox.critical()` in `src/rapid_viewer/ui/main_window.py` line 209

**Logs:**
- No logging framework configured
- No `logging` module imports detected anywhere in the codebase
- Errors are caught and displayed to the user via Qt message boxes

## CI/CD & Deployment

**Hosting:**
- Not hosted. Distributed as a standalone Windows `.exe` file.

**CI Pipeline:**
- None detected. No `.github/workflows/`, no CI configuration files.

**Build Process:**
- Manual: run `build.bat` which invokes PyInstaller with `rapid_viewer.spec`
- Output: `dist/rapid_viewer.exe` (single-file executable)
- Distribution: direct file sharing (a `.lnk` shortcut file exists: `SURPHASE Rapid Viewer.lnk`)

## Environment Configuration

**Required env vars:**
- None. The application has zero environment variable dependencies.

**Secrets location:**
- Not applicable. No secrets, API keys, or credentials of any kind.

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## OpenGL Integration

While not an "external service," OpenGL is a significant system-level integration:

**OpenGL Version:** 3.3 Core Profile (enforced in `src/rapid_viewer/main.py`)
**Shaders:** 5 shader programs defined in `src/rapid_viewer/renderer/shaders.py`:
- Solid line shader (MoveL + MoveC arc segments)
- Dashed line shader (MoveJ segments, fragment-based dash pattern)
- Marker shader (GL_POINTS with circular discard in fragment shader)
- Axes indicator shader (reuses solid shader with rotation-only MVP)
- TCP triad shader (reuses solid shader for RGB axis lines at waypoints)

**Vertex Layout:** Interleaved `[x, y, z, r, g, b]` float32, stride 24 bytes
- Location 0: `vec3 aPos`
- Location 1: `vec3 aColor`

**GPU Resource Management:**
- VAOs/VBOs created in `initializeGL()`, re-uploaded on scene change via `GL_DYNAMIC_DRAW`
- Context loss recovery: `_last_parse_result` cached and re-uploaded if `initializeGL` is called again
- Cleanup: `glDeleteBuffers` / `glDeleteVertexArrays` not explicitly called (relies on context destruction)

---

*Integration audit: 2026-03-31*
