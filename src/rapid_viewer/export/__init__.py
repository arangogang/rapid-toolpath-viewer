"""Export module for saving modified .mod files.

Public API:
    export_mod() -- patch source text with EditModel changes
"""

from __future__ import annotations

from rapid_viewer.export.mod_writer import export_mod

__all__ = ["export_mod"]
