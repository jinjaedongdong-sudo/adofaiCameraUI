"""Camera editor utilities using adofaipy.LevelDict."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Any
import math
import adofaipy


class CameraEditor:
    """Load and modify MoveCamera events in an ADOFAI level."""

    def __init__(self, adofai_path: Path | str) -> None:
        # Load level using LevelDict instead of adofaipy.load
        self.level = adofaipy.LevelDict(str(adofai_path))
        # Store existing MoveCamera actions
        self.camera_actions: List[Dict[str, Any]] = [
            dict(action)
            for action in self.level.getActions(lambda a: a["eventType"] == "MoveCamera")
        ]

    # --- Tile position helpers -------------------------------------------------
    def tile_positions(self) -> List[Tuple[float, float]]:
        """Return cartesian positions for each tile based on angles.

        The final tile in ``LevelDict.tiles`` duplicates the last angle, so it
        is ignored when computing the path."""
        x, y = 0.0, 0.0
        positions = [(x, y)]
        for tile in self.level.tiles[:-1]:
            rad = math.radians(tile.angle)
            x += math.cos(rad)
            y += math.sin(rad)
            positions.append((x, y))
        return positions

    # --- Save logic ------------------------------------------------------------
    def save(self, out_path: Path | str) -> None:
        """Write the current level to ``out_path``.

        Existing MoveCamera actions are removed and then re-added from
        ``self.camera_actions`` prior to writing."""
        # Remove any existing MoveCamera events
        self.level.removeActions(lambda a: a["eventType"] == "MoveCamera")
        # Rebuild from stored actions
        for action in self.camera_actions:
            self.level.addAction(adofaipy.Action(action))
        # Export to file
        self.level.writeToFile(str(out_path))
