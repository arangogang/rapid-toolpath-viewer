# Phase 1: Parser and File Loading - Research

**Researched:** 2026-03-30
**Domain:** ABB RAPID .mod file parsing, PyQt6 file dialog, Python data modeling
**Confidence:** HIGH

## Summary

Phase 1 builds the foundation layer: a RAPID .mod file parser and file loading dialog. The parser must handle four move instruction types (MoveL, MoveJ, MoveC, MoveAbsJ), extract robtarget position/orientation data from declarations that may span multiple lines, resolve named target references and inline Offs() expressions, and tag every parsed instruction with its source line number for downstream code-linking.

The critical design decision is **semicolon-based statement tokenization before regex parsing**. A naive line-by-line regex approach will fail on real-world .mod files where robtarget declarations are split across multiple lines. The parser must first split the file content into statements (delimited by `;`), normalize whitespace within each statement, then apply regex patterns. This two-pass architecture (Pass 1: extract robtarget declarations into a name lookup table; Pass 2: extract move instructions and resolve target references) is well-documented in the existing architecture research and is the correct approach.

For file loading, PyQt6's `QFileDialog.getOpenFileName()` is straightforward. The main considerations are encoding handling (Windows-1252 fallback for real ABB files) and updating the window title bar after load.

**Primary recommendation:** Build a statement-level tokenizer first (split on `;`, normalize whitespace), then apply regex patterns to complete statements. Use Python dataclasses for all parsed data types. Keep the parser module pure Python with zero Qt dependency for easy unit testing.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FILE-01 | User can open .mod file via file dialog | PyQt6 QFileDialog.getOpenFileName() with filter "RAPID Module (*.mod)" -- see Code Examples section |
| FILE-02 | Filename appears in title bar after load | QMainWindow.setWindowTitle() with filename from path -- trivial integration |
| PARS-01 | Parse MoveL instructions with linear move path extraction | Regex pattern for MoveL capturing target reference, speed, zone, tool -- see regex patterns section |
| PARS-02 | Parse MoveJ instructions with joint move path extraction | Same pattern structure as MoveL, different keyword |
| PARS-03 | Parse MoveC instructions with CirPoint + endpoint | MoveC takes TWO robtarget arguments (circle point + end point); regex must capture both |
| PARS-04 | Parse MoveAbsJ but exclude from 3D rendering (show in code panel) | MoveAbsJ uses jointtarget (joint angles), not robtarget; parse and store with flag `has_cartesian=False` |
| PARS-05 | Parse robtarget data type (pos x/y/z + orient q1-q4) | robtarget = [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax1..eax6]] -- nested bracket extraction |
| PARS-06 | Parse multiline robtarget declarations correctly | Semicolon-based statement tokenization before regex; critical pitfall documented in PITFALLS.md |
| PARS-07 | Store source line number with each Move instruction for code linking | Track line numbers during statement assembly; map statement back to originating line range |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Tech Stack**: Python + PyQt6 + PyOpenGL -- locked choice, no alternatives
- **Platform**: Windows desktop only
- **Scope**: Code verification viewer -- no editing/simulation features
- **GSD Workflow**: All changes must go through GSD commands
- **Parser approach**: Custom regex-based .mod parser (no external parsing library)
- **OpenGL**: Modern shader pipeline (OpenGL 3.3 Core), NOT fixed-function

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.9 | Runtime | Installed on target system |
| PyQt6 | 6.10.2 | QFileDialog, QMainWindow | User-specified; provides file dialog and window management |
| re (stdlib) | built-in | Regex parsing | RAPID syntax is regular enough for regex; no external parser needed |
| dataclasses (stdlib) | built-in | Data structures | ParseResult, RobTarget, MoveInstruction -- clean, typed, immutable-friendly |
| pathlib (stdlib) | built-in | File path handling | Cross-platform path operations |

### Supporting (Phase 1 only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | >=1.26 | Position/orientation arrays | Store robtarget pos as np.ndarray for downstream rendering compatibility |
| pytest | 9.0.2 | Unit testing | Test parser against fixture .mod files |

### Not Needed in Phase 1

| Library | Why Not Yet |
|---------|-------------|
| PyOpenGL | No rendering in Phase 1 |
| pyrr | No 3D math in Phase 1 |
| pytest-qt | No GUI widget tests in Phase 1 (parser is pure Python) |

## Architecture Patterns

### Recommended Project Structure (Phase 1 scope)

```
src/
  rapid_viewer/
    __init__.py
    main.py                    # Minimal: QApplication + QMainWindow with File > Open

    parser/
      __init__.py
      rapid_parser.py          # Top-level parse_module() function
      tokens.py                # Data classes: RobTarget, MoveInstruction, ParseResult, etc.
      patterns.py              # Compiled regex patterns for RAPID syntax

    ui/
      __init__.py
      main_window.py           # QMainWindow with file dialog and title bar update

tests/
  __init__.py
  test_parser.py               # Unit tests for parser
  test_multiline.py            # Multiline robtarget edge cases
  fixtures/
    simple.mod                 # Basic test file: MoveL + MoveJ
    multiline.mod              # Multiline robtarget declarations
    movecircular.mod           # MoveC with CirPoint
    moveabsj.mod               # MoveAbsJ with jointtarget
    multi_proc.mod             # Multiple PROC blocks
    offs_inline.mod            # Inline Offs() expressions
    encoding_win1252.mod       # Windows-1252 encoded file
```

### Pattern 1: Semicolon-Based Statement Tokenizer

**What:** Before any regex parsing, split the entire file content into statements using `;` as delimiter while tracking line numbers.

**When to use:** Always -- this is the foundation of the parser. Every other pattern depends on this.

**Why:** Real .mod files have multiline declarations. A line-by-line parser will miss split robtargets. This is the #1 pitfall documented in project research.

```python
def tokenize_statements(source: str) -> list[tuple[str, int]]:
    """Split source into (statement_text, start_line_number) tuples.

    Statements are delimited by semicolons.
    Line numbers are 1-indexed to match text editor conventions.
    """
    statements = []
    current_stmt = []
    start_line = 1

    for line_num, line in enumerate(source.splitlines(), start=1):
        # Strip comments (! is RAPID line comment)
        code = line.split('!', 1)[0]

        # Handle semicolons within the line
        parts = code.split(';')
        for i, part in enumerate(parts):
            stripped = part.strip()
            if i < len(parts) - 1:
                # Semicolon found -- complete this statement
                if stripped or current_stmt:
                    current_stmt.append(stripped)
                    full_stmt = ' '.join(current_stmt).strip()
                    if full_stmt:
                        statements.append((full_stmt, start_line))
                    current_stmt = []
                    start_line = line_num + 1  # Next statement starts on next line (approx)
            else:
                # No semicolon yet -- accumulate
                if stripped:
                    if not current_stmt:
                        start_line = line_num
                    current_stmt.append(stripped)

    return statements
```

### Pattern 2: Two-Pass Parse Architecture

**What:** Pass 1 extracts all data declarations (robtarget, jointtarget, tooldata, wobjdata). Pass 2 extracts all move instructions and resolves target name references against the declaration table.

**When to use:** Always -- move instructions reference targets by name.

```python
def parse_module(source: str) -> ParseResult:
    statements = tokenize_statements(source)

    # Pass 1: Build target lookup table
    targets: dict[str, RobTarget] = {}
    joint_targets: dict[str, JointTarget] = {}
    for stmt_text, line_num in statements:
        rt = try_parse_robtarget_decl(stmt_text, line_num)
        if rt:
            targets[rt.name] = rt
            continue
        jt = try_parse_jointtarget_decl(stmt_text, line_num)
        if jt:
            joint_targets[jt.name] = jt

    # Pass 2: Extract move instructions
    moves: list[MoveInstruction] = []
    for stmt_text, line_num in statements:
        move = try_parse_move(stmt_text, line_num, targets, joint_targets)
        if move:
            moves.append(move)

    return ParseResult(
        module_name=extract_module_name(source),
        moves=moves,
        targets=targets,
        joint_targets=joint_targets,
        source_text=source,
    )
```

### Pattern 3: Dataclass-Based Token Types

**What:** Use Python dataclasses for all parsed data types. Keep them pure Python (no Qt dependency).

```python
from dataclasses import dataclass, field
from enum import Enum, auto
import numpy as np

class MoveType(Enum):
    MOVEL = auto()
    MOVEJ = auto()
    MOVEC = auto()
    MOVEABSJ = auto()

@dataclass(frozen=True)
class RobTarget:
    """Parsed robtarget declaration."""
    name: str
    pos: np.ndarray          # [x, y, z] in mm
    orient: np.ndarray       # [q1, q2, q3, q4] -- ABB convention: q1=w, q2=x, q3=y, q4=z
    confdata: tuple[int, ...] # [cf1, cf4, cf6, cfx]
    extjoint: tuple[float, ...]  # external axes (9E9 = unused)
    source_line: int         # 1-indexed line number in .mod file

@dataclass(frozen=True)
class JointTarget:
    """Parsed jointtarget declaration (for MoveAbsJ)."""
    name: str
    robax: tuple[float, ...]  # [j1, j2, j3, j4, j5, j6] in degrees
    extax: tuple[float, ...]  # external axes
    source_line: int

@dataclass(frozen=True)
class MoveInstruction:
    """A single parsed move instruction."""
    move_type: MoveType
    target: RobTarget | None        # None for MoveAbsJ
    circle_point: RobTarget | None  # Only for MoveC
    joint_target: JointTarget | None  # Only for MoveAbsJ
    speed: str               # e.g. "v100", "v1000"
    zone: str                # e.g. "fine", "z10", "z50"
    tool: str                # e.g. "tool0", "tPen"
    wobj: str                # e.g. "wobj0" -- capture for future use
    source_line: int         # 1-indexed line of the Move instruction
    has_cartesian: bool = True  # False for MoveAbsJ

@dataclass
class ParseResult:
    """Complete result of parsing a .mod file."""
    module_name: str
    moves: list[MoveInstruction]
    targets: dict[str, RobTarget]
    joint_targets: dict[str, JointTarget]
    source_text: str
    procedures: list[str] = field(default_factory=list)  # PROC names found
    errors: list[str] = field(default_factory=list)       # Non-fatal parse warnings
```

### Anti-Patterns to Avoid

- **Line-by-line regex parsing:** Will fail on multiline robtarget declarations. Use statement tokenizer first.
- **Separate point list and line number list:** Will desync. Store line number inside each MoveInstruction.
- **Ignoring wobj parameter:** Even if not resolving coordinate frames in v1, capture the wobj name for future use.
- **Not storing MoveAbsJ instructions:** Even though they lack Cartesian positions, they need source line tracking for code panel display.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Regex compilation | String patterns rebuilt each call | `re.compile()` at module level in patterns.py | Compiled regex is 5-10x faster on repeated use |
| Quaternion storage | Custom quaternion class | numpy ndarray [q1,q2,q3,q4] | Downstream rendering needs numpy arrays; avoid conversion |
| File dialog | Custom file browser widget | QFileDialog.getOpenFileName() | Qt's native dialog respects OS theme, recent files, etc. |
| Encoding detection | Manual byte inspection | `open(path, encoding='utf-8', errors='replace')` with fallback | Good enough for .mod files; chardet is overkill |

## Common Pitfalls

### Pitfall 1: Multiline robtarget Declarations

**What goes wrong:** A naive per-line regex misses robtargets split across 2-6 lines. Points silently disappear.
**Why it happens:** Developer tests only against machine-generated single-line files.
**How to avoid:** Semicolon-based statement tokenizer BEFORE regex. Test with hand-formatted files.
**Warning signs:** Parser works on clean files but drops points from real customer files.

### Pitfall 2: Line Number Tracking Through Multiline Statements

**What goes wrong:** When a statement spans lines 45-48, which line number do we store? If we store line 45 (start), clicking the point in 3D should scroll to line 45 where the Move instruction keyword appears.
**Why it happens:** Statement tokenizer consumes multiple lines; easy to lose track of where each statement started.
**How to avoid:** Track `start_line` in the tokenizer -- the line where the first non-empty content of the statement appeared. This is the line the user would expect to see highlighted.

### Pitfall 3: Offs() Function Resolution

**What goes wrong:** `MoveL Offs(p10, 0, 100, 0)` requires resolving p10 from the target table and adding the offset to its position. Parser that only handles named targets will fail silently or crash on Offs().
**Why it happens:** Offs() is extremely common in real RAPID programs but rare in tutorial examples.
**How to avoid:** Detect `Offs(name, dx, dy, dz)` pattern in the target argument position. Look up the base target, clone it with modified position `[x+dx, y+dy, z+dz]`. Keep orientation from the base target.

### Pitfall 4: MoveC Has Two Target Arguments

**What goes wrong:** MoveC takes `circle_point, to_point` -- two robtarget arguments instead of one. A regex built for MoveL/MoveJ will only capture the first argument.
**Why it happens:** Copy-paste regex from MoveL pattern without accounting for the extra argument.
**How to avoid:** Separate regex pattern for MoveC with two capture groups for target names. Store both circle_point and end_point in MoveInstruction.

### Pitfall 5: File Encoding

**What goes wrong:** Real .mod files generated by RobotStudio may use Windows-1252 encoding, not UTF-8. Opening with `encoding='utf-8'` crashes on byte 0x96 (en-dash in comments).
**Why it happens:** RobotStudio is a Windows application that uses the system codepage.
**How to avoid:** Try UTF-8 first, fall back to `latin-1` (superset of Windows-1252 that never fails). Use `errors='replace'` as final safety net.

### Pitfall 6: RAPID Comment Syntax

**What goes wrong:** RAPID uses `!` for line comments. A robtarget declaration followed by a comment containing a semicolon could confuse the tokenizer.
**Why it happens:** `CONST robtarget p10 := [...]; ! move to start position; first point` -- the second semicolon is in the comment.
**How to avoid:** Strip comments (everything after `!` on a line) BEFORE semicolon-based statement splitting.

### Pitfall 7: Scientific Notation in External Axes

**What goes wrong:** External axes use `9E+09` or `9E9` for "unused". Regex that expects only digits with optional decimal will fail.
**Why it happens:** Standard RAPID convention for unused external axes.
**How to avoid:** Number pattern must handle scientific notation: `[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?`

## RAPID .mod File Syntax Reference

### robtarget Structure
```
CONST robtarget name := [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax_a,eax_b,eax_c,eax_d,eax_e,eax_f]];
```

Components:
- **pos** (trans): `[x, y, z]` -- position in mm
- **orient**: `[q1, q2, q3, q4]` -- quaternion (q1=scalar/w, q2=x, q3=y, q4=z)
- **confdata**: `[cf1, cf4, cf6, cfx]` -- robot axis configuration (integers)
- **extjoint**: `[eax_a, ..., eax_f]` -- external axes (9E+09 = unused)

Declaration modifiers: `CONST`, `PERS`, `VAR`, `LOCAL` (prefix)
- `CONST`: immutable, most common for taught points
- `PERS`: persistent across program restarts, also very common
- `VAR`: mutable, less common for robtargets
- `LOCAL`: scope modifier, can precede any of the above

### jointtarget Structure (for MoveAbsJ)
```
CONST jointtarget name := [[j1,j2,j3,j4,j5,j6],[eax_a,eax_b,eax_c,eax_d,eax_e,eax_f]];
```

Components:
- **robax**: `[j1, j2, j3, j4, j5, j6]` -- joint angles in degrees
- **extax**: `[eax_a, ..., eax_f]` -- external axes

### Move Instruction Syntax

```rapid
MoveL  target, speed, zone, tool [\WObj:=wobj];
MoveJ  target, speed, zone, tool [\WObj:=wobj];
MoveC  cirpoint, topoint, speed, zone, tool [\WObj:=wobj];
MoveAbsJ jointtarget, speed, zone, tool [\WObj:=wobj];
```

**Optional parameters** (common):
- `\WObj:=wobj0` -- work object (default is wobj0 if omitted)
- `\T:=time` -- motion time override (rare, can ignore in v1)
- `\V:=velocity` -- velocity override (rare)

**Target argument variants:**
1. Named reference: `MoveL p10, v100, fine, tool0;`
2. Inline Offs(): `MoveL Offs(p10, 0, 100, 0), v100, fine, tool0;`
3. Inline robtarget (rare): `MoveL [[500,0,400],[1,0,0,0],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], v100, fine, tool0;`

### Offs() Function
```
Offs(robtarget, XOffset, YOffset, ZOffset) -> robtarget
```
Returns a copy of the robtarget with position offset by (X, Y, Z). Orientation unchanged.

### Module Structure
```rapid
MODULE ModuleName
    ! Data declarations at module level
    CONST robtarget p10 := [...];
    PERS robtarget p20 := [...];

    PROC main()
        MoveJ p10, v1000, z50, tool0;
        MoveL p20, v100, fine, tool0;
    ENDPROC

    PROC subRoutine()
        MoveL p10, v200, z10, tool0;
    ENDPROC
ENDMODULE
```

## Regex Patterns

### Pattern: robtarget Declaration

```python
import re

# Matches: [LOCAL] CONST|PERS|VAR robtarget name := [nested brackets data]
# Applied to normalized statements (whitespace-collapsed, comment-stripped)
RE_ROBTARGET_DECL = re.compile(
    r'(?:LOCAL\s+)?'
    r'(?:CONST|PERS|VAR)\s+'
    r'robtarget\s+'
    r'(\w+)'                          # group 1: name
    r'\s*:=\s*'
    r'(\[.+\])',                      # group 2: full bracket data
    re.IGNORECASE
)

# Extract components from bracket data: [[x,y,z],[q1,q2,q3,q4],[cf...],[eax...]]
RE_BRACKET_GROUP = re.compile(r'\[([^\[\]]+)\]')
```

### Pattern: jointtarget Declaration

```python
RE_JOINTTARGET_DECL = re.compile(
    r'(?:LOCAL\s+)?'
    r'(?:CONST|PERS|VAR)\s+'
    r'jointtarget\s+'
    r'(\w+)'                          # group 1: name
    r'\s*:=\s*'
    r'(\[.+\])',                      # group 2: full bracket data
    re.IGNORECASE
)
```

### Pattern: Move Instructions

```python
# Number pattern including scientific notation
_NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?'

# Target reference: named variable OR Offs(name, dx, dy, dz) OR inline [...]
_TARGET_REF = r'(\w+|Offs\s*\([^)]+\)|\[.+?\])'

# MoveL/MoveJ: instruction target, speed, zone, tool [optional params]
RE_MOVEL = re.compile(
    r'MoveL\s+' + _TARGET_REF + r'\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)',
    re.IGNORECASE
)

RE_MOVEJ = re.compile(
    r'MoveJ\s+' + _TARGET_REF + r'\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)',
    re.IGNORECASE
)

# MoveC: instruction cirpoint, topoint, speed, zone, tool
RE_MOVEC = re.compile(
    r'MoveC\s+' + _TARGET_REF + r'\s*,\s*' + _TARGET_REF + r'\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)',
    re.IGNORECASE
)

# MoveAbsJ: instruction jointtarget, speed, zone, tool
RE_MOVEABSJ = re.compile(
    r'MoveAbsJ\s+' + _TARGET_REF + r'\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)',
    re.IGNORECASE
)

# Offs() extraction
RE_OFFS = re.compile(
    r'Offs\s*\(\s*(\w+)\s*,\s*(' + _NUM + r')\s*,\s*(' + _NUM + r')\s*,\s*(' + _NUM + r')\s*\)',
    re.IGNORECASE
)

# Optional \WObj parameter
RE_WOBJ = re.compile(r'\\WObj\s*:=\s*(\w+)', re.IGNORECASE)
```

### Pattern: Module and Procedure Boundaries

```python
RE_MODULE = re.compile(r'MODULE\s+(\w+)', re.IGNORECASE)
RE_PROC = re.compile(r'PROC\s+(\w+)\s*\(', re.IGNORECASE)
RE_ENDPROC = re.compile(r'ENDPROC', re.IGNORECASE)
RE_ENDMODULE = re.compile(r'ENDMODULE', re.IGNORECASE)
```

## Code Examples

### PyQt6 File Dialog for .mod Loading

```python
from PyQt6.QtWidgets import QMainWindow, QFileDialog
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ABB RAPID Toolpath Viewer")
        self._setup_menu()

    def _setup_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_action = file_menu.addAction("&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)

    def _open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open RAPID Module",
            "",  # Start directory (empty = last used)
            "RAPID Module (*.mod);;All Files (*)"
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path: str):
        path = Path(file_path)

        # Read with encoding fallback
        try:
            source = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            source = path.read_text(encoding='latin-1')

        # Parse
        from rapid_viewer.parser.rapid_parser import parse_module
        result = parse_module(source)

        # Update title bar (FILE-02)
        self.setWindowTitle(f"ABB RAPID Toolpath Viewer - {path.name}")

        # Store result for downstream phases
        self._parse_result = result
```

### Encoding Fallback Strategy

```python
def read_mod_file(path: Path) -> str:
    """Read a .mod file with encoding fallback.

    ABB RobotStudio generates files in various encodings:
    - UTF-8 (newer versions)
    - Windows-1252 / Latin-1 (older versions, Swedish/German comments)

    Strategy: try UTF-8 first, fall back to latin-1 (superset of Win-1252).
    """
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return path.read_text(encoding='latin-1')
```

### Parsing Nested Bracket Data

```python
def parse_robtarget_data(bracket_str: str) -> tuple:
    """Parse robtarget bracket data: [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax...]]

    Returns (pos, orient, confdata, extjoint) or raises ValueError.
    """
    # Find all innermost bracket groups
    groups = RE_BRACKET_GROUP.findall(bracket_str)
    if len(groups) < 4:
        raise ValueError(f"Expected 4 bracket groups in robtarget, got {len(groups)}: {bracket_str}")

    # Parse each group
    pos = np.array([float(x.strip()) for x in groups[0].split(',')], dtype=np.float64)
    orient = np.array([float(x.strip()) for x in groups[1].split(',')], dtype=np.float64)
    confdata = tuple(int(float(x.strip())) for x in groups[2].split(','))
    extjoint = tuple(float(x.strip()) for x in groups[3].split(','))

    if len(pos) != 3:
        raise ValueError(f"Position must have 3 components, got {len(pos)}")
    if len(orient) != 4:
        raise ValueError(f"Orientation must have 4 components, got {len(orient)}")

    return pos, orient, confdata, extjoint
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Line-by-line regex | Statement-level tokenization | Recognized as pitfall #1 | Prevents silent data loss on multiline declarations |
| Custom quaternion class | numpy arrays | Standard practice | Directly compatible with downstream rendering pipeline |
| PyQt5 QFileDialog | PyQt6 QFileDialog | PyQt6 release (2021) | Enum syntax changed (e.g. `QFileDialog.Option.DontUseNativeDialog`) |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | Yes | 3.12.9 | -- |
| pip | Package install | Yes | 24.3.1 | -- |
| uv | Preferred package manager | No | -- | Use pip directly |
| pytest | Parser unit tests | Yes | 9.0.2 | -- |
| ruff | Linting | No | -- | Skip linting or install via pip |

**Missing dependencies with no fallback:**
- None -- all critical dependencies are available or installable via pip.

**Missing dependencies with fallback:**
- uv not installed -- use pip for package management instead of uv
- ruff not installed -- install via `pip install ruff` when needed

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None -- see Wave 0 |
| Quick run command | `pytest tests/test_parser.py -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FILE-01 | File dialog opens and returns path | manual-only | N/A (requires GUI interaction) | N/A |
| FILE-02 | Window title updates with filename | unit | `pytest tests/test_main_window.py::test_title_update -x` | Wave 0 |
| PARS-01 | MoveL parsed correctly | unit | `pytest tests/test_parser.py::test_parse_movel -x` | Wave 0 |
| PARS-02 | MoveJ parsed correctly | unit | `pytest tests/test_parser.py::test_parse_movej -x` | Wave 0 |
| PARS-03 | MoveC parsed with CirPoint + endpoint | unit | `pytest tests/test_parser.py::test_parse_movec -x` | Wave 0 |
| PARS-04 | MoveAbsJ parsed, has_cartesian=False | unit | `pytest tests/test_parser.py::test_parse_moveabsj -x` | Wave 0 |
| PARS-05 | robtarget pos/orient extracted | unit | `pytest tests/test_parser.py::test_parse_robtarget -x` | Wave 0 |
| PARS-06 | Multiline robtarget declaration | unit | `pytest tests/test_parser.py::test_multiline_robtarget -x` | Wave 0 |
| PARS-07 | Source line numbers stored | unit | `pytest tests/test_parser.py::test_line_numbers -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_parser.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/test_parser.py` -- covers PARS-01 through PARS-07
- [ ] `tests/test_main_window.py` -- covers FILE-02 (pytest-qt needed)
- [ ] `tests/fixtures/*.mod` -- sample .mod files for all edge cases
- [ ] `pyproject.toml` -- pytest configuration section
- [ ] Framework install: `pip install pytest pytest-qt` (pytest already available, pytest-qt needed for FILE-02)

## Open Questions

1. **Inline robtargets in Move instructions**
   - What we know: Rare but valid -- `MoveL [[500,0,400],[1,0,0,0],...], v100, fine, tool0;`
   - What's unclear: How common is this in real production files?
   - Recommendation: Support it in the regex but give it LOW priority for testing. Named references + Offs() cover 95%+ of real-world usage.

2. **Multiple PROCs -- which to display?**
   - What we know: PARS-08 (PROC selection) is Phase 3. But Phase 1 parser should still track which PROC each move belongs to.
   - What's unclear: Should Phase 1 parse all PROCs or just main()?
   - Recommendation: Parse ALL PROCs, store proc name in ParseResult.procedures. Default to the first PROC (or "main" if found). Phase 3 adds UI for selection.

3. **LOCAL CONST vs CONST scope**
   - What we know: LOCAL restricts scope to the module. For a single-file viewer, scope differences don't matter.
   - Recommendation: Parse both identically. The LOCAL keyword is just stripped during pattern matching.

4. **MoveAbsJ representation in data model**
   - What we know: jointtargets have joint angles, not Cartesian positions. Cannot render in 3D without forward kinematics.
   - STATE.md flags: "Decide exact behavior during Phase 1 planning"
   - Recommendation: Store MoveAbsJ in the moves list with `has_cartesian=False` and `target=None`. Downstream code skips them for 3D but includes them for code panel line-number mapping. This preserves PARS-07 compliance.

## Sources

### Primary (HIGH confidence)
- [ABB RAPID Technical Reference Manual](https://library.e.abb.com/public/688894b98123f87bc1257cc50044e809/Technical%20reference%20manual_RAPID_3HAC16581-1_revJ_en.pdf) -- robtarget, jointtarget, Move instruction specifications
- [ABB RAPID Instructions Reference](https://library.e.abb.com/public/b227fcd260204c4dbeb8a58f8002fe64/Rapid_instructions.pdf) -- MoveL, MoveJ, MoveC, MoveAbsJ full parameter lists
- [Qt 6 QFileDialog Documentation](https://doc.qt.io/qt-6/qfiledialog.html) -- getOpenFileName API and filter syntax
- Project ARCHITECTURE.md -- two-pass parser design, ParseResult dataclass structure
- Project PITFALLS.md -- multiline parsing, quaternion convention, encoding issues

### Secondary (MEDIUM confidence)
- [PyQt6 QFileDialog examples](https://zetcode.com/pyqt6/dialogs/) -- Python-specific QFileDialog usage patterns
- [ABB RobotStudio Forum](https://forums.robotstudio.com/) -- real-world .mod file formatting patterns

### Tertiary (LOW confidence)
- Offs() inline robtarget frequency estimate (95%+ named refs) -- based on experience, not measured

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries confirmed in STACK.md, versions verified on system
- Architecture: HIGH -- two-pass parser well-documented in ARCHITECTURE.md, regex patterns verified against ABB reference
- Pitfalls: HIGH -- thoroughly documented in PITFALLS.md, cross-referenced with ABB documentation
- Regex patterns: MEDIUM -- patterns constructed from syntax specification, need validation against real .mod files

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable domain, ABB RAPID syntax does not change frequently)
