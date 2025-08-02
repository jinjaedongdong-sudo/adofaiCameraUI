"""Camera editor utilities using adofaipy.LevelDict."""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Any
import math
import json5
import adofaipy


class CameraEditor:
    """Load and modify MoveCamera events in an ADOFAI level."""

    def __init__(self, adofai_path: Path | str) -> None:
        """Load level data using ``json5`` and populate a ``LevelDict``."""

        with open(adofai_path, "r", encoding="utf-8-sig") as f:
            leveldict = json5.load(f)

        # Build LevelDict manually from the parsed dictionary
        self.level = adofaipy.LevelDict()
        self.level.filename = str(adofai_path)
        self.level.tiles = []
        self.level.nonFloorDecos = []
        self.level.settings = adofaipy.Settings(leveldict.get("settings", {}))

        if "angleData" in leveldict:
            angles = leveldict["angleData"]
        else:
            pathchars = {
                "R": 0, "p": 15, "J": 30, "E": 45, "T": 60, "o": 75, "U": 90,
                "q": 105, "G": 120, "Q": 135, "H": 150, "W": 165, "L": 180,
                "x": 195, "N": 210, "Z": 225, "F": 240, "V": 255, "D": 270,
                "Y": 285, "B": 300, "C": 315, "M": 330, "A": 345, "!": 999,
            }
            angles = [pathchars[ch] for ch in leveldict["pathData"]]

        angles.append(angles[-1] if angles[-1] != 999 else (angles[-2] + 180) % 360)
        self.level.tiles = [adofaipy.Tile(angle) for angle in angles]

        for action in leveldict.get("actions", []):
            self.level.tiles[action["floor"]].actions.append(adofaipy.Action(action))

        decorations = leveldict.get("decorations", [])
        self.level.nonFloorDecos = [
            adofaipy.Decoration(d) for d in decorations if "floor" not in d
        ]
        for deco in decorations:
            if "floor" in deco:
                if deco["floor"] >= len(self.level.tiles):
                    self.level.tiles[-1].decorations.append(adofaipy.Decoration(deco))
                else:
                    self.level.tiles[deco["floor"]].decorations.append(
                        adofaipy.Decoration(deco)
                    )

        # Store existing MoveCamera actions
        self.camera_actions: List[Dict[str, Any]] = [
            dict(action)
            for action in self.level.getActions(
                lambda a: a["eventType"] == "MoveCamera"
            )
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
