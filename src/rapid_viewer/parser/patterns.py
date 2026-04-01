"""Compiled regex patterns for ABB RAPID .mod file syntax.

All patterns are compiled at module level for performance (5-10x faster
than re-compiling on each call). All patterns use re.IGNORECASE because
RAPID keywords are case-insensitive in practice.

Number pattern note: RAPID uses scientific notation for unused external axes
(e.g. 9E+09). The _NUM pattern handles this.
"""

import re

# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------

# Number pattern: handles integers, decimals, and scientific notation.
# Covers: 500, 0.5, .5, 9E+09, 9e9, -1.23e-4, etc.
_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"

# Target reference: named variable OR Offs(name, dx, dy, dz) OR inline [[...]]
# This appears as the first argument to MoveL/MoveJ/MoveAbsJ (or first two for MoveC).
_TARGET_REF = r"(\w+|Offs\s*\([^)]+\)|\[.+?\])"

# ---------------------------------------------------------------------------
# Data declaration patterns
# ---------------------------------------------------------------------------

# Matches: [LOCAL] CONST|PERS|VAR robtarget name := [nested bracket data]
# Applied to normalized, whitespace-collapsed, comment-stripped statements.
# Group 1: target name, Group 2: full bracket data string
RE_ROBTARGET_DECL = re.compile(
    r"(?:LOCAL\s+)?"
    r"(?:CONST|PERS|VAR)\s+"
    r"robtarget\s+"
    r"(\w+)"           # group 1: name
    r"\s*:=\s*"
    r"(\[.+\])",       # group 2: full bracket data
    re.IGNORECASE,
)

# Matches: [LOCAL] CONST|PERS|VAR jointtarget name := [[j1..j6],[eax...]]
# Group 1: target name, Group 2: full bracket data string
RE_JOINTTARGET_DECL = re.compile(
    r"(?:LOCAL\s+)?"
    r"(?:CONST|PERS|VAR)\s+"
    r"jointtarget\s+"
    r"(\w+)"           # group 1: name
    r"\s*:=\s*"
    r"(\[.+\])",       # group 2: full bracket data
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Move instruction patterns
# ---------------------------------------------------------------------------

# MoveL target, speed, zone, tool [\WObj:=wobj]
# Group 1: target ref, Group 2: speed, Group 3: zone, Group 4: tool
RE_MOVEL = re.compile(
    r"MoveL\s+" + _TARGET_REF + r"\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)",
    re.IGNORECASE,
)

# MoveJ target, speed, zone, tool [\WObj:=wobj]
# Group 1: target ref, Group 2: speed, Group 3: zone, Group 4: tool
RE_MOVEJ = re.compile(
    r"MoveJ\s+" + _TARGET_REF + r"\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)",
    re.IGNORECASE,
)

# MoveC cirpoint, topoint, speed, zone, tool [\WObj:=wobj]
# Group 1: circle_point ref, Group 2: to_point ref, Group 3: speed, Group 4: zone, Group 5: tool
RE_MOVEC = re.compile(
    r"MoveC\s+"
    + _TARGET_REF
    + r"\s*,\s*"
    + _TARGET_REF
    + r"\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)",
    re.IGNORECASE,
)

# MoveAbsJ jointtarget, speed, zone, tool [\WObj:=wobj]
# Group 1: joint target ref, Group 2: speed, Group 3: zone, Group 4: tool
RE_MOVEABSJ = re.compile(
    r"MoveAbsJ\s+" + _TARGET_REF + r"\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Offs() function pattern
# ---------------------------------------------------------------------------

# Offs(base_target, dx, dy, dz)
# Group 1: base name, Group 2: dx, Group 3: dy, Group 4: dz
RE_OFFS = re.compile(
    r"Offs\s*\(\s*(\w+)\s*,\s*(" + _NUM + r")\s*,\s*(" + _NUM + r")\s*,\s*(" + _NUM + r")\s*\)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Optional parameter patterns
# ---------------------------------------------------------------------------

# \WObj:=wobj_name -- optional work object override on any Move instruction
# Group 1: wobj name
RE_WOBJ = re.compile(r"\\WObj\s*:=\s*(\w+)", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Module and procedure boundary patterns
# ---------------------------------------------------------------------------

# MODULE ModuleName
# Group 1: module name
RE_MODULE = re.compile(r"MODULE\s+(\w+)", re.IGNORECASE)

# PROC procname(...)
# Group 1: procedure name
RE_PROC = re.compile(r"PROC\s+(\w+)\s*\(", re.IGNORECASE)

# ENDPROC (no capture group needed)
RE_ENDPROC = re.compile(r"ENDPROC", re.IGNORECASE)

# ENDMODULE (no capture group needed)
RE_ENDMODULE = re.compile(r"ENDMODULE", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Utility patterns
# ---------------------------------------------------------------------------

# CONST|PERS num name := value
# Group 1: variable name, Group 2: numeric value
RE_NUM_DECL = re.compile(
    r"(?:LOCAL\s+)?"
    r"(?:CONST|PERS)\s+"
    r"num\s+"
    r"(\w+)"                   # group 1: name
    r"\s*:=\s*"
    r"(" + _NUM + r")",        # group 2: value
    re.IGNORECASE,
)

# VAR robtarget assignment (runtime): name := Offs(base, dx, dy, dz) OR name := expr
# Group 1: variable name, Group 2: RHS expression
RE_ROBTARGET_ASSIGN = re.compile(
    r"^(\w+)\s*:=\s*(Offs\s*\(.+\))",
    re.IGNORECASE,
)

# Offs() with potentially non-literal arguments (variable names or numbers)
# Group 1: base name, Group 2: arg2, Group 3: arg3, Group 4: arg4
_OFFS_ARG = r"([\w.+\-eE]+)"
RE_OFFS_FLEX = re.compile(
    r"Offs\s*\(\s*(\w+)\s*,\s*" + _OFFS_ARG + r"\s*,\s*" + _OFFS_ARG + r"\s*,\s*" + _OFFS_ARG + r"\s*\)",
    re.IGNORECASE,
)

# SetDO signal_name, value  (digital output on/off)
# Group 1: signal name, Group 2: value (0 or 1)
RE_SETDO = re.compile(
    r"SetDO\s+(\w+)\s*,\s*(\d+)",
    re.IGNORECASE,
)

# Extract innermost bracket groups: [content without nested brackets]
# Used to pull pos, orient, confdata, extjoint from robtarget bracket data.
RE_BRACKET_GROUP = re.compile(r"\[([^\[\]]+)\]")
