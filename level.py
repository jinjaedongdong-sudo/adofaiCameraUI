from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class Level:
    """Minimal representation of an ADOFAI level used by the editor.

    Only the parts of the file that are required by the camera editor are
    stored: ``pathData`` describing the tile layout, ``settings`` for timing
    information and ``actions`` containing event data.
    """

    pathData: str
    settings: Dict[str, Any]
    actions: List[Dict[str, Any]]

    @classmethod
    def load(cls, path: str | Path) -> "Level":
        """Load a level from ``path``."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            pathData=data.get("pathData", ""),
            settings=data.get("settings", {}),
            actions=data.get("actions", []),
        )

    def dict(self) -> Dict[str, Any]:
        """Return the level as a plain dictionary suitable for ``json``."""
        return {
            "pathData": self.pathData,
            "settings": self.settings,
            "actions": self.actions,
        }
