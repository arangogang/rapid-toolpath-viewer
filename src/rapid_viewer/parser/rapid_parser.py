"""RAPID .mod file parser.

Implements a two-pass architecture:
  Pass 1: Tokenize statements (semicolon-based) and extract all target declarations
          into lookup dictionaries (RobTarget, JointTarget).
  Pass 2: Extract all move instructions, resolving target references against
          the lookup dictionaries built in Pass 1.

Entry points:
  parse_module(source)  -- parse string content, return ParseResult
  read_mod_file(path)   -- read file with UTF-8 / latin-1 fallback, return string
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from rapid_viewer.parser.patterns import (
    RE_BRACKET_GROUP,
    RE_JOINTTARGET_DECL,
    RE_MODULE,
    RE_MOVEC,
    RE_MOVEABSJ,
    RE_MOVEJ,
    RE_MOVEL,
    RE_OFFS,
    RE_PROC,
    RE_ROBTARGET_DECL,
    RE_WOBJ,
)
from rapid_viewer.parser.tokens import (
    JointTarget,
    MoveInstruction,
    MoveType,
    ParseResult,
    RobTarget,
)


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def read_mod_file(path: Path) -> str:
    """Read a RAPID .mod file with encoding fallback.

    Tries UTF-8 first. If that fails, falls back to latin-1, which is a
    superset of Windows-1252 and never raises a decode error. ABB RobotStudio
    sometimes generates files with Windows codepage encoding (e.g., byte 0x96
    for en-dash in Swedish/German comments).

    Args:
        path: Path to the .mod file.

    Returns:
        File content as a string.
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------


def tokenize_statements(source: str) -> list[tuple[str, int]]:
    """Split RAPID source into (statement_text, start_line_number) tuples.

    Statements in RAPID are delimited by semicolons. This tokenizer:
      - Strips line comments (everything after '!' on a line).
      - Accumulates content across multiple lines until a ';' is found.
      - Tracks the line number where each statement's first non-empty content
        appeared (the line number a user would expect to see highlighted).
      - Returns whitespace-normalized statement strings.

    Args:
        source: Full text content of the .mod file.

    Returns:
        List of (normalized_statement, start_line_number) tuples. Line numbers
        are 1-indexed to match text editor conventions.
    """
    statements: list[tuple[str, int]] = []
    current_parts: list[str] = []
    start_line: int = 1

    for line_num, line in enumerate(source.splitlines(), start=1):
        # Strip RAPID line comment: '!' terminates meaningful content
        code = line.split("!", 1)[0]

        # Split on ';' to detect statement boundaries
        parts = code.split(";")
        for i, part in enumerate(parts):
            stripped = part.strip()
            is_last_part = i == len(parts) - 1

            if not is_last_part:
                # A semicolon was found after this part -- complete the statement
                if stripped or current_parts:
                    current_parts.append(stripped)
                    full_stmt = " ".join(p for p in current_parts if p).strip()
                    if full_stmt:
                        statements.append((full_stmt, start_line))
                # Reset accumulator
                current_parts = []
                start_line = line_num + 1  # Next statement will start at least on next line
            else:
                # No semicolon terminator yet -- accumulate
                if stripped:
                    if not current_parts:
                        # First content of a new statement
                        start_line = line_num
                    current_parts.append(stripped)

    return statements


# ---------------------------------------------------------------------------
# Data parsers
# ---------------------------------------------------------------------------


def parse_robtarget_data(
    bracket_str: str,
) -> tuple[np.ndarray, np.ndarray, tuple[int, ...], tuple[float, ...]]:
    """Parse the nested bracket data section of a robtarget declaration.

    Expected format: [[x,y,z],[q1,q2,q3,q4],[cf1,cf4,cf6,cfx],[eax_a..eax_f]]

    Uses RE_BRACKET_GROUP to extract innermost bracket contents, then parses
    each group as numbers. Scientific notation (e.g. 9E+09) is handled by
    Python's float().

    Args:
        bracket_str: The full bracket data string from the robtarget declaration.

    Returns:
        Tuple of (pos, orient, confdata, extjoint).

    Raises:
        ValueError: If fewer than 4 bracket groups are found or component
                    counts are wrong.
    """
    groups = RE_BRACKET_GROUP.findall(bracket_str)
    if len(groups) < 4:
        raise ValueError(
            f"Expected at least 4 bracket groups in robtarget data, "
            f"got {len(groups)}: {bracket_str!r}"
        )

    pos = np.array([float(x.strip()) for x in groups[0].split(",")], dtype=np.float64)
    orient = np.array([float(x.strip()) for x in groups[1].split(",")], dtype=np.float64)
    # confdata values may appear as "0.0" in some RobotStudio exports
    confdata: tuple[int, ...] = tuple(int(float(x.strip())) for x in groups[2].split(","))
    extjoint: tuple[float, ...] = tuple(float(x.strip()) for x in groups[3].split(","))

    if len(pos) != 3:
        raise ValueError(f"pos must have 3 components, got {len(pos)}")
    if len(orient) != 4:
        raise ValueError(f"orient must have 4 components, got {len(orient)}")

    return pos, orient, confdata, extjoint


def try_parse_robtarget_decl(stmt: str, line_num: int) -> RobTarget | None:
    """Attempt to parse a robtarget declaration statement.

    Matches: [LOCAL] CONST|PERS|VAR robtarget name := [[...][...][...][...]]

    Args:
        stmt: Whitespace-normalized, comment-stripped statement string.
        line_num: 1-indexed line number where this statement starts.

    Returns:
        RobTarget if the statement is a robtarget declaration, else None.
    """
    m = RE_ROBTARGET_DECL.search(stmt)
    if m is None:
        return None
    name = m.group(1)
    bracket_data = m.group(2)
    try:
        pos, orient, confdata, extjoint = parse_robtarget_data(bracket_data)
    except (ValueError, IndexError):
        return None
    return RobTarget(
        name=name,
        pos=pos,
        orient=orient,
        confdata=confdata,
        extjoint=extjoint,
        source_line=line_num,
    )


def try_parse_jointtarget_decl(stmt: str, line_num: int) -> JointTarget | None:
    """Attempt to parse a jointtarget declaration statement.

    Matches: [LOCAL] CONST|PERS|VAR jointtarget name := [[j1..j6],[eax...]]

    Args:
        stmt: Whitespace-normalized, comment-stripped statement string.
        line_num: 1-indexed line number where this statement starts.

    Returns:
        JointTarget if the statement is a jointtarget declaration, else None.
    """
    m = RE_JOINTTARGET_DECL.search(stmt)
    if m is None:
        return None
    name = m.group(1)
    bracket_data = m.group(2)
    groups = RE_BRACKET_GROUP.findall(bracket_data)
    if len(groups) < 2:
        return None
    try:
        robax: tuple[float, ...] = tuple(float(x.strip()) for x in groups[0].split(","))
        extax: tuple[float, ...] = tuple(float(x.strip()) for x in groups[1].split(","))
    except (ValueError, IndexError):
        return None
    return JointTarget(name=name, robax=robax, extax=extax, source_line=line_num)


# ---------------------------------------------------------------------------
# Target reference resolution
# ---------------------------------------------------------------------------


def resolve_target_ref(
    ref_str: str,
    targets: dict[str, RobTarget],
    line_num: int,
) -> RobTarget | None:
    """Resolve a target reference string to a RobTarget.

    Handles three cases:
      1. Offs(base_name, dx, dy, dz) -- look up base, return clone with offset pos.
      2. Inline robtarget starting with '[' -- parse bracket data directly.
      3. Named reference -- look up in targets dict.

    Args:
        ref_str: The raw target reference string from the move instruction.
        targets: Lookup dict built during Pass 1.
        line_num: Source line number of the move instruction.

    Returns:
        Resolved RobTarget, or None if resolution fails.
    """
    ref_str = ref_str.strip()

    # Case 1: Offs() function
    offs_m = RE_OFFS.search(ref_str)
    if offs_m is not None:
        base_name = offs_m.group(1)
        dx = float(offs_m.group(2))
        dy = float(offs_m.group(3))
        dz = float(offs_m.group(4))
        base = targets.get(base_name)
        if base is None:
            return None
        new_pos = base.pos + np.array([dx, dy, dz], dtype=np.float64)
        return RobTarget(
            name=f"Offs({base_name},{dx},{dy},{dz})",
            pos=new_pos,
            orient=base.orient,
            confdata=base.confdata,
            extjoint=base.extjoint,
            source_line=line_num,
        )

    # Case 2: Inline robtarget
    if ref_str.startswith("["):
        try:
            pos, orient, confdata, extjoint = parse_robtarget_data(ref_str)
            return RobTarget(
                name="<inline>",
                pos=pos,
                orient=orient,
                confdata=confdata,
                extjoint=extjoint,
                source_line=line_num,
            )
        except (ValueError, IndexError):
            return None

    # Case 3: Named reference
    return targets.get(ref_str)


# ---------------------------------------------------------------------------
# Move instruction parser
# ---------------------------------------------------------------------------


def try_parse_move(
    stmt: str,
    line_num: int,
    targets: dict[str, RobTarget],
    joint_targets: dict[str, JointTarget],
) -> MoveInstruction | None:
    """Attempt to parse a move instruction statement.

    Tries RE_MOVEL, RE_MOVEJ, RE_MOVEC, RE_MOVEABSJ in order. For each match,
    resolves target references via resolve_target_ref() and extracts the optional
    WObj parameter (defaults to "wobj0" if absent).

    Args:
        stmt: Whitespace-normalized statement string.
        line_num: 1-indexed line number where this statement starts.
        targets: RobTarget lookup dict from Pass 1.
        joint_targets: JointTarget lookup dict from Pass 1.

    Returns:
        MoveInstruction if a move pattern matched, else None.
    """
    # Extract optional \WObj parameter (present on any move type)
    wobj_m = RE_WOBJ.search(stmt)
    wobj = wobj_m.group(1) if wobj_m is not None else "wobj0"

    # --- MoveL ---
    m = RE_MOVEL.search(stmt)
    if m is not None:
        target = resolve_target_ref(m.group(1), targets, line_num)
        return MoveInstruction(
            move_type=MoveType.MOVEL,
            target=target,
            circle_point=None,
            joint_target=None,
            speed=m.group(2),
            zone=m.group(3),
            tool=m.group(4),
            wobj=wobj,
            source_line=line_num,
            has_cartesian=True,
        )

    # --- MoveJ ---
    m = RE_MOVEJ.search(stmt)
    if m is not None:
        target = resolve_target_ref(m.group(1), targets, line_num)
        return MoveInstruction(
            move_type=MoveType.MOVEJ,
            target=target,
            circle_point=None,
            joint_target=None,
            speed=m.group(2),
            zone=m.group(3),
            tool=m.group(4),
            wobj=wobj,
            source_line=line_num,
            has_cartesian=True,
        )

    # --- MoveC ---
    m = RE_MOVEC.search(stmt)
    if m is not None:
        cir_target = resolve_target_ref(m.group(1), targets, line_num)
        to_target = resolve_target_ref(m.group(2), targets, line_num)
        return MoveInstruction(
            move_type=MoveType.MOVEC,
            target=to_target,
            circle_point=cir_target,
            joint_target=None,
            speed=m.group(3),
            zone=m.group(4),
            tool=m.group(5),
            wobj=wobj,
            source_line=line_num,
            has_cartesian=True,
        )

    # --- MoveAbsJ ---
    m = RE_MOVEABSJ.search(stmt)
    if m is not None:
        jt_ref = m.group(1).strip()
        jt = joint_targets.get(jt_ref)
        return MoveInstruction(
            move_type=MoveType.MOVEABSJ,
            target=None,
            circle_point=None,
            joint_target=jt,
            speed=m.group(2),
            zone=m.group(3),
            tool=m.group(4),
            wobj=wobj,
            source_line=line_num,
            has_cartesian=False,
        )

    return None


# ---------------------------------------------------------------------------
# Top-level parser
# ---------------------------------------------------------------------------


def parse_module(source: str) -> ParseResult:
    """Parse a RAPID .mod file source string and return a ParseResult.

    Architecture:
      1. Tokenize: split source into (statement, line_num) tuples using
         semicolons as delimiters, stripping RAPID '!' comments.
      2. Pass 1: Extract all robtarget and jointtarget declarations into
         lookup dictionaries. Also record module name and procedure names.
      3. Pass 2: Extract all move instructions, resolving target references
         using the lookup dictionaries from Pass 1.

    Args:
        source: Full text content of the .mod file as a string.

    Returns:
        ParseResult containing module name, move list, target dicts, and
        the original source text.
    """
    statements = tokenize_statements(source)

    # Extract module name from raw source (not statement-level)
    mod_m = RE_MODULE.search(source)
    module_name = mod_m.group(1) if mod_m is not None else "Unknown"

    # Extract procedure names from raw source
    procedures: list[str] = [m.group(1) for m in RE_PROC.finditer(source)]

    # Pass 1: Build target lookup tables
    targets: dict[str, RobTarget] = {}
    joint_targets: dict[str, JointTarget] = {}
    for stmt_text, line_num in statements:
        rt = try_parse_robtarget_decl(stmt_text, line_num)
        if rt is not None:
            targets[rt.name] = rt
            continue
        jt = try_parse_jointtarget_decl(stmt_text, line_num)
        if jt is not None:
            joint_targets[jt.name] = jt

    # Pass 2: Extract move instructions
    moves: list[MoveInstruction] = []
    for stmt_text, line_num in statements:
        move = try_parse_move(stmt_text, line_num, targets, joint_targets)
        if move is not None:
            moves.append(move)

    return ParseResult(
        module_name=module_name,
        moves=moves,
        targets=targets,
        joint_targets=joint_targets,
        source_text=source,
        procedures=procedures,
    )
