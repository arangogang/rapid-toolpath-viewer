"""Data model contracts for parsed RAPID .mod file content.

All types are defined as frozen dataclasses (or non-frozen for mutable
result containers). These are pure Python with no Qt dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

import numpy as np


class MoveType(Enum):
    """Type of RAPID move instruction."""

    MOVEL = auto()
    MOVEJ = auto()
    MOVEC = auto()
    MOVEABSJ = auto()


@dataclass(frozen=True)
class RobTarget:
    """Parsed robtarget declaration.

    ABB RAPID robtarget stores a full Cartesian pose:
      pos    -- [x, y, z] in mm
      orient -- [q1, q2, q3, q4] quaternion (ABB convention: q1=scalar/w, q2=x, q3=y, q4=z)
      confdata -- [cf1, cf4, cf6, cfx] robot axis configuration (integers)
      extjoint -- [eax_a..eax_f] external axes (9E+09 = unused)
    """

    name: str
    pos: np.ndarray          # shape (3,), dtype float64
    orient: np.ndarray       # shape (4,), dtype float64
    confdata: tuple[int, ...]
    extjoint: tuple[float, ...]
    source_line: int         # 1-indexed line number in .mod file

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, RobTarget):
            return NotImplemented
        return (
            self.name == other.name
            and np.array_equal(self.pos, other.pos)
            and np.array_equal(self.orient, other.orient)
            and self.confdata == other.confdata
            and self.extjoint == other.extjoint
            and self.source_line == other.source_line
        )

    def __hash__(self) -> int:
        # frozen=True requires __hash__; use name + source_line as proxy
        return hash((self.name, self.source_line))


@dataclass(frozen=True)
class JointTarget:
    """Parsed jointtarget declaration (used with MoveAbsJ).

    Stores robot joint angles, NOT Cartesian positions.
    """

    name: str
    robax: tuple[float, ...]  # [j1, j2, j3, j4, j5, j6] in degrees
    extax: tuple[float, ...]  # external axes
    source_line: int

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, JointTarget):
            return NotImplemented
        return (
            self.name == other.name
            and self.robax == other.robax
            and self.extax == other.extax
            and self.source_line == other.source_line
        )

    def __hash__(self) -> int:
        return hash((self.name, self.source_line))


@dataclass(frozen=True)
class MoveInstruction:
    """A single parsed move instruction.

    For MoveAbsJ: target is None, has_cartesian=False, joint_target is populated.
    For MoveC: circle_point holds the intermediate CirPoint robtarget.
    For MoveL/MoveJ: circle_point is None, joint_target is None.
    """

    move_type: MoveType
    target: RobTarget | None          # None for MoveAbsJ
    circle_point: RobTarget | None    # Only for MoveC
    joint_target: JointTarget | None  # Only for MoveAbsJ
    speed: str                        # e.g. "v100", "v1000"
    zone: str                         # e.g. "fine", "z10", "z50"
    tool: str                         # e.g. "tool0", "tPen"
    wobj: str                         # e.g. "wobj0" (default "wobj0" if omitted)
    source_line: int                  # 1-indexed line of Move keyword
    has_cartesian: bool = True        # False for MoveAbsJ
    laser_on: bool = False            # True if digital output (laser) is active


@dataclass
class ParseResult:
    """Complete result of parsing a .mod file.

    Not frozen because the parser builds it incrementally.
    """

    module_name: str
    moves: list[MoveInstruction]
    targets: dict[str, RobTarget]
    joint_targets: dict[str, JointTarget]
    source_text: str
    procedures: list[str] = field(default_factory=list)  # PROC names found
    proc_ranges: dict[str, tuple[int, int]] = field(default_factory=dict)  # PROC name -> (start_line, end_line)
    errors: list[str] = field(default_factory=list)       # Non-fatal parse warnings
