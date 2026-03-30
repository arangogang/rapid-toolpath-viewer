# Pitfalls Research

**Domain:** ABB RAPID Toolpath Viewer (Python + PyQt6 + PyOpenGL)
**Researched:** 2026-03-30
**Confidence:** HIGH (domain-specific, verified against ABB documentation and Qt/OpenGL community sources)

## Critical Pitfalls

### Pitfall 1: RAPID robtarget Declarations Span Multiple Lines and Have Inconsistent Whitespace

**What goes wrong:**
A naive line-by-line parser breaks immediately on real-world .mod files. RobotStudio and hand-edited files routinely split robtarget declarations across multiple lines. A single robtarget like `CONST robtarget p10:=[[500,0,400],[1,0,0,0],[-1,0,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];` may appear as 1 line, 2 lines, or 6 lines depending on how the file was generated. Regex-per-line approaches miss split declarations entirely, producing silent data loss (points simply disappear from the viewer with no error).

**Why it happens:**
Developers test against clean, machine-generated files. Real production .mod files are edited by hand, merged from multiple sources, or exported by different RobotStudio versions with different formatting preferences.

**How to avoid:**
- Parse the entire file content as a single string, not line-by-line.
- Use semicolon (`;`) as the statement terminator to split statements first, then parse each statement.
- Strip all newlines and normalize whitespace within each statement before extracting data.
- Build a minimal statement-level tokenizer: read characters until `;`, accumulate into a statement buffer, then parse each complete statement.

**Warning signs:**
- Parser works on tutorial examples but fails on customer files.
- Point count from parser is lower than expected (some robtargets silently dropped).
- Test files are all single-line formatted.

**Phase to address:**
Phase 1 (Parser foundation). This is the very first thing to get right. Design the parser around statement boundaries from day one.

---

### Pitfall 2: ABB Quaternion Convention Differs from Common 3D Libraries

**What goes wrong:**
ABB RAPID uses quaternion order `[q1, q2, q3, q4]` where `q1` is the scalar (w) component: `orient := [q1, q2, q3, q4]` maps to `[w, x, y, z]`. However, many Python libraries (scipy.spatial.transform.Rotation, some numpy-quaternion builds) expect `[x, y, z, w]` order. Silently swapping scalar/vector components produces orientations that look "almost right" but are rotated incorrectly -- tool Z-axes point in wrong directions, making the viewer subtly wrong and hard to debug.

**Why it happens:**
There is no universal quaternion convention. ABB uses scalar-first `[w, x, y, z]`. scipy.spatial.transform.Rotation.from_quat() expects scalar-last `[x, y, z, w]`. Developers copy quaternion values directly without reordering and get wrong but plausible-looking orientations.

**How to avoid:**
- Define a single internal quaternion convention in the codebase (recommend `[w, x, y, z]` to match ABB natively).
- At every boundary where quaternions enter or leave the system (parsing, rendering, any library call), document and enforce the convention with explicit conversion functions.
- Write a unit test with a known orientation: `[1, 0, 0, 0]` = identity (no rotation), `[0, 1, 0, 0]` = 180-degree rotation around X. Verify the visual result matches.
- Use `scipy.spatial.transform.Rotation.from_quat([q2, q3, q4, q1])` -- note the reorder putting ABB's q1 last.

**Warning signs:**
- Tool orientation markers point in unexpected directions but positions are correct.
- Rotations "look close" but are off by 90 or 180 degrees on certain axes.
- Identity quaternion `[1,0,0,0]` does not render as "no rotation."

**Phase to address:**
Phase 1 (Parser) and Phase 2 (3D Viewer). Must be locked down before any orientation visualization. Add a reference test fixture with known ABB quaternion values and expected Euler angles.

---

### Pitfall 3: PyOpenGL Immediate Mode Renders 10x Slower Than VBOs

**What goes wrong:**
Using `glBegin()`/`glEnd()` immediate mode to draw toolpath lines and markers works fine for 50 points but becomes unusably slow (sub-10 FPS) at 500+ points. Real production .mod files can contain 2,000-10,000+ points. The app appears to work during development with small test files, then performs terribly with real data.

**Why it happens:**
PyOpenGL 3.x uses ctypes under the hood, and each `glVertex3f()` call incurs Python-to-C overhead. Immediate mode makes thousands of these calls per frame. VBOs batch the data into GPU memory and draw with a single call.

**How to avoid:**
- Use VBOs (Vertex Buffer Objects) from the start. Build numpy arrays of vertex data (`dtype=numpy.float32` -- this is critical), upload once to GPU, draw with `glDrawArrays()`.
- Install `OpenGL_accelerate` (pip install PyOpenGL-accelerate) for ctypes optimization.
- Set `OpenGL.ERROR_ON_COPY = True` before importing GL modules to catch accidental dtype conversions that cause silent performance degradation.
- For dynamic highlight (current step marker), use a small separate VBO or uniform, not rebuild the entire buffer.

**Warning signs:**
- Frame rate drops as point count increases linearly.
- Camera orbit/zoom feels sluggish even with moderate file sizes.
- Profiler shows most time in `glVertex` or `glColor` calls.

**Phase to address:**
Phase 2 (3D Viewer foundation). Choose VBO architecture from the first OpenGL code. Retrofitting VBOs into immediate-mode code requires a complete rewrite of the rendering pipeline.

---

### Pitfall 4: QOpenGLWidget Context Not Current Outside paintGL/initializeGL/resizeGL

**What goes wrong:**
Calling OpenGL functions (buffer creation, texture upload, shader compilation) outside the three protected methods without calling `makeCurrent()` first produces silent failures or crashes. Common scenario: user loads a new .mod file, parser finishes, code tries to update VBO data from a slot connected to a signal -- OpenGL context is not current, `glBufferData()` silently does nothing or segfaults.

**Why it happens:**
Qt only guarantees the OpenGL context is current inside `initializeGL()`, `resizeGL()`, and `paintGL()`. Any other method (button click handlers, file load callbacks, timer slots) does NOT have a current context. The Qt documentation states this clearly but it is easy to miss.

**How to avoid:**
- Call `self.makeCurrent()` at the start of any method that touches OpenGL state outside the three protected methods.
- Better pattern: never call OpenGL functions directly from UI callbacks. Instead, set a flag/queue the data update and call `self.update()` to trigger `paintGL()`, where the context is guaranteed current.
- For cleanup, use `hideEvent()` instead of `__del__` -- Python destructor timing is unreliable and the context may already be destroyed.

**Warning signs:**
- OpenGL errors appear only when loading a second file (first file loads in initializeGL where context is current).
- Crashes on file reload but not on initial load.
- Black screen after data update but orbit/zoom still works.

**Phase to address:**
Phase 2 (3D Viewer). Establish the update pattern in the very first QOpenGLWidget implementation. Document the rule: "OpenGL calls only in paintGL or after makeCurrent()."

---

### Pitfall 5: MoveC Circular Interpolation Requires Arc Geometry, Not Just Two Points

**What goes wrong:**
MoveC takes a CirPoint (intermediate point on the arc) and a ToPoint (endpoint). Unlike MoveL (start-to-end line) and MoveJ (start-to-end joint interpolation), MoveC requires computing a circular arc through three points (previous position, CirPoint, ToPoint). Developers who build the viewer as "connect the dots with lines" will render MoveC as a straight line or two line segments, which is visually wrong and defeats the purpose of a toolpath verifier.

**Why it happens:**
MoveL and MoveJ are straightforward (line between two points). MoveC is fundamentally different -- it defines a circular arc, and the visual representation must show the actual curved path. Developers defer MoveC handling and never implement it properly.

**How to avoid:**
- Implement three-point circle arc computation: given P1 (current pos), P2 (CirPoint), P3 (ToPoint), compute the center and radius of the circle passing through all three, then generate interpolated points along the arc from P1 through P2 to P3.
- Use numpy for the geometry: find the plane of the three points, compute the circumcenter, then parametrically sample the arc.
- Render the arc as a polyline with 20-50 segments (sufficient visual smoothness).
- Handle the degenerate case where three points are collinear (fall back to straight line).

**Warning signs:**
- MoveC paths render as straight lines or V-shapes.
- Circular weld paths look like polygons.
- No test case specifically validates MoveC rendering against known arc geometry.

**Phase to address:**
Phase 1 (Parser) must capture the CirPoint + ToPoint structure. Phase 2 (3D Viewer) must implement arc interpolation. Do not defer -- MoveC is a core requirement per the project spec.

---

### Pitfall 6: Coordinate Frame Chain Ignored -- Rendering Everything in World Frame

**What goes wrong:**
RAPID robtargets are defined relative to a work object (wobj), which itself is defined by a user frame and object frame relative to the world frame. The full transform chain is: `World -> UserFrame -> ObjectFrame -> robtarget`. If the parser ignores `wobj` and `tooldata` references in Move instructions, all points render in world coordinates. This works when `wobj0` (identity) is used, but production programs frequently use custom work objects. Points appear in completely wrong positions.

**Why it happens:**
For v1 with `wobj0`, ignoring coordinate frames works perfectly. The problem only surfaces when a user loads a file that references a custom `wobj`. The developer never encounters this during development because test files use `wobj0`.

**How to avoid:**
- In v1, parse the `wobj` parameter from Move instructions. If it is `wobj0`, proceed normally. If it is a custom wobj, either:
  (a) Parse the wobjdata definition and apply the transform chain, or
  (b) Display a clear warning: "Custom work object 'myWobj' detected -- positions shown in work object frame, not world frame."
- Store the wobj reference with each parsed move instruction even if you do not resolve it yet -- this prevents a parser redesign later.
- The transform chain is: `P_world = T_user * T_object * P_robtarget` where T_user and T_object come from the wobjdata.

**Warning signs:**
- Viewer works perfectly on some files but shows points in bizarre locations on others.
- Points cluster near origin when they should be spread across a large workpiece.
- No wobj parameter captured in the parser's move instruction data structure.

**Phase to address:**
Phase 1 (Parser) should capture wobj references. Phase 3 or later can implement full coordinate frame resolution. But the data model must support it from Phase 1.

---

### Pitfall 7: Step Playback Index Desyncs from Code Line Mapping

**What goes wrong:**
The step playback feature (forward/back through toolpath points) and the code-line highlighting feature are built as separate systems. The playback index maps to a list of 3D points, while the code highlight maps to line numbers. When the parser skips unparseable lines, encounters comments, or handles multi-line declarations, the index-to-line mapping silently breaks. Clicking point 47 highlights line 52 instead of line 47's actual source line.

**Why it happens:**
Point index and source line number are not the same thing. A .mod file has comments, blank lines, variable declarations, procedure headers, and non-movement instructions between move commands. Developers assume `point_index == line_number` or maintain two separate lists that drift apart.

**How to avoid:**
- During parsing, create a single data structure that binds each parsed move instruction to its source line number(s): `MoveInstruction(type, target, line_start, line_end)`.
- The playback controller indexes into the list of MoveInstructions, and each instruction carries its source location.
- Never maintain separate "list of points" and "list of line numbers" -- they will desync.
- For multi-line declarations, store the range (line_start to line_end).

**Warning signs:**
- Highlighting is off by a few lines and gets progressively worse later in the file.
- Adding comments to the .mod file shifts all subsequent highlights.
- No explicit line number stored in the parsed instruction data structure.

**Phase to address:**
Phase 1 (Parser) must capture line numbers. Phase 3 (Step Playback + Code Sync) depends on this. If Phase 1 does not store line numbers, Phase 3 requires parser rework.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Regex-only parsing (no tokenizer) | Fast to implement for simple cases | Cannot handle nested brackets, multiline, escapes; breaks on edge cases | Never for production; OK for a 1-hour prototype only |
| Immediate mode OpenGL | Easier to understand, no buffer management | 10-50x slower rendering, must rewrite entirely for VBO | Never -- VBO code is barely more complex |
| Hardcoded `wobj0` assumption | Skip coordinate frame math | Breaks on any file using custom work objects; requires parser redesign to add later | Acceptable in Phase 1 MVP if wobj data is still captured in the data model |
| Single numpy dtype for all GL data | Simpler array construction | Silent dtype conversion causes copies, 2-5x perf hit | Never -- always specify `dtype=np.float32` explicitly |
| `QTimer(0)` for animation | Simple playback implementation | Framerate depends on system load, inconsistent speed | Phase 1 prototype only; replace with elapsed-time-based stepping |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| PyOpenGL + QOpenGLWidget | Using `glBindFramebuffer(GL_FRAMEBUFFER, 0)` to unbind | Use `self.defaultFramebufferObject()` -- Qt renders to an FBO, not FBO 0 |
| PyOpenGL + numpy | Passing `float64` arrays to GL functions | Always use `np.float32`. Set `OpenGL.ERROR_ON_COPY = True` to catch this |
| QOpenGLWidget + file loading | Updating GL buffers in file-open callback | Set dirty flag, call `self.update()`, do GL work in `paintGL()` |
| QTextEdit + 3D viewer selection | Blocking signals during programmatic highlight changes | Use `blockSignals(True)` or a guard flag to prevent highlight-change triggering re-selection loops |
| scipy Rotation + ABB quaternions | Passing `[q1,q2,q3,q4]` directly to `Rotation.from_quat()` | Reorder to `[q2,q3,q4,q1]` (scipy expects `[x,y,z,w]`, ABB gives `[w,x,y,z]`) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Rebuilding VBO every frame | FPS drops linearly with point count | Upload VBO once on file load; only update highlight uniform per frame | >200 points |
| Python-side arc interpolation per frame | MoveC arcs recalculated on every repaint | Pre-compute arc polyline segments at parse time, store in VBO | >10 MoveC instructions |
| Full scene redraw on step change | Noticeable lag on step forward/back | Only update the "current position" marker; static geometry stays in GPU | >500 points |
| `glGetError()` in render loop | Each call forces GPU sync, kills pipeline parallelism | Only use `glGetError()` in debug mode, remove from production render path | Always a problem, masks other perf issues |
| Large .mod file string operations | Parser hangs on multi-MB files | Use compiled regex (`re.compile()`), avoid repeated string concatenation, process statement-by-statement | >1MB .mod files (10,000+ points) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No visual distinction between MoveJ and MoveL | Cannot verify motion type correctness | Dashed line for MoveJ, solid for MoveL, curved for MoveC (project spec already requires this) |
| Camera starts at origin looking at origin | User sees nothing if toolpath is at [1500, 800, 400] | Auto-fit camera to bounding box of parsed points on file load |
| No error feedback on parse failure | User opens file, sees empty viewer, assumes app is broken | Show parse error dialog with line number and partial results: "Parsed 47/50 points, error at line 203" |
| Step playback has no speed control | Too fast or too slow for different path lengths | Provide speed slider; use constant mm/sec interpolation rather than constant time per step |
| Orientation markers too large/small | Clutter the view or invisible | Scale orientation axes relative to bounding box size, provide a slider |
| No coordinate readout on hover/click | User cannot verify actual position values | Tooltip or status bar showing `[x, y, z]` and `[q1, q2, q3, q4]` of selected point |

## "Looks Done But Isn't" Checklist

- [ ] **Parser:** Handles multiline robtarget declarations -- test with hand-formatted files, not just RobotStudio exports
- [ ] **Parser:** Handles `PERS`, `VAR`, and `CONST` robtarget declarations -- all three storage classes
- [ ] **Parser:** Captures CirPoint for MoveC, not just ToPoint -- verify with a file containing circular moves
- [ ] **Parser:** Stores source line numbers with each instruction -- verify by checking highlight accuracy on a 200+ line file
- [ ] **3D Viewer:** Camera auto-fits to data on file load -- test with toolpaths at various scales and positions
- [ ] **3D Viewer:** Works with files containing only MoveAbsJ (joint targets, no Cartesian position) -- must either skip gracefully or convert
- [ ] **Quaternion handling:** `[1,0,0,0]` renders as identity (no rotation) -- if tool axis points wrong direction, convention is swapped
- [ ] **Step playback:** First and last steps are reachable -- off-by-one errors are extremely common in index-based navigation
- [ ] **Code sync:** Highlighting correct line after scrolling the code view -- selection and scroll position interact in Qt text widgets
- [ ] **MoveC rendering:** Arcs visually curved, not straight lines or V-shapes -- test with a known circular path

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Regex-only parser fails on real files | HIGH | Rewrite parser with statement-level tokenizer; design change, not a fix |
| Immediate mode rendering too slow | HIGH | Rewrite all rendering code to use VBOs; cannot incrementally fix |
| Quaternion convention wrong | LOW | Add reorder function at parse boundary; fix is localized if architecture is clean |
| Missing wobj support | MEDIUM | If wobj reference was captured in data model: add transform math. If not captured: parser rework needed |
| Step-to-line desync | MEDIUM | If line numbers stored in parse result: fix mapping logic. If not stored: parser rework needed |
| QOpenGLWidget context crashes | LOW | Add `makeCurrent()` calls; localized fix once pattern is understood |
| MoveC renders as straight line | MEDIUM | Add arc computation math; self-contained geometry module, moderate effort |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Multiline robtarget parsing | Phase 1 (Parser) | Test with 5+ real .mod files from different sources; count parsed points vs expected |
| Quaternion convention mismatch | Phase 1 (Parser) + Phase 2 (Viewer) | Unit test: ABB `[1,0,0,0]` = identity orientation in viewer; `[0,0.707,0,0.707]` = known 90-degree rotation |
| Immediate mode performance | Phase 2 (3D Viewer) | Load 2000-point file, measure FPS during orbit; must sustain 30+ FPS |
| QOpenGLWidget context management | Phase 2 (3D Viewer) | Load file, then load a second file; no crash, no black screen |
| MoveC arc rendering | Phase 1 (Parser) + Phase 2 (Viewer) | Visual comparison: MoveC path should trace a smooth curve matching the three defining points |
| Coordinate frame chain (wobj) | Phase 1 (data model) + Phase 3+ (implementation) | Load file with custom wobj; verify warning or correct transform |
| Step-to-line desync | Phase 1 (Parser) + Phase 3 (Playback) | Step to point N, verify highlighted line contains the corresponding Move instruction |

## Sources

- [ABB RAPID Technical Reference Manual](https://library.e.abb.com/public/688894b98123f87bc1257cc50044e809/Technical%20reference%20manual_RAPID_3HAC16581-1_revJ_en.pdf) -- RAPID syntax, data types, instruction reference
- [ABB RAPID Instructions Reference](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf) -- MoveL, MoveJ, MoveC, MoveAbsJ specifications
- [Qt 6 QOpenGLWidget Documentation](https://doc.qt.io/qt-6/qopenglwidget.html) -- Context management, FBO handling, cleanup patterns
- [PySide6 QOpenGLWidget Documentation](https://doc.qt.io/qtforpython-6/PySide6/QtOpenGLWidgets/QOpenGLWidget.html) -- Python-specific context and cleanup guidance
- [PyOpenGL for OpenGL Programmers](https://pyopengl.sourceforge.net/documentation/opengl_diffs.html) -- Performance characteristics, dtype handling, ERROR_ON_COPY
- [ABB Quaternion Orientation Forum Discussion](https://forums.robotstudio.com/discussion/9435/quaternion-orientation) -- ABB quaternion convention `[q1=w, q2=x, q3=y, q4=z]`
- [ABB Quaternion Calculator](https://quat2euler.com/) -- Euler-to-quaternion conversion verification tool
- [ABB User and Object Frame Discussion](https://forums.robotstudio.com/discussion/2606/user-and-object-frame) -- wobj coordinate frame hierarchy
- [PyOpenGL VBO and numpy dtype issue](https://github.com/mcfletch/pyopengl/issues/5) -- Memory allocation on dtype mismatch

---
*Pitfalls research for: ABB RAPID Toolpath Viewer (Python + PyQt6 + PyOpenGL)*
*Researched: 2026-03-30*
