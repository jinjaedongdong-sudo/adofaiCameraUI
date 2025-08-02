from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List


PATH_CHARS = {
    "R": 0, "p": 15, "J": 30, "E": 45, "T": 60, "o": 75, "U": 90,
    "q": 105, "G": 120, "Q": 135, "H": 150, "W": 165, "L": 180,
    "x": 195, "N": 210, "Z": 225, "F": 240, "V": 255, "D": 270,
    "Y": 285, "B": 300, "C": 315, "M": 330, "A": 345, "!": 999,
}


@dataclass
class Level:
    """Minimal container for the subset of an ADOFAI level used by the editor."""

    settings: dict
    actions: List[dict]
    angle_data: List[int]

    @classmethod
    def load(cls, path: Path) -> "Level":
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        if "angleData" in data:
            angles = list(data["angleData"])
        else:
            angles = [PATH_CHARS[ch] for ch in data.get("pathData", "")]
        # Append final angle following adofaipy's behaviour
        if angles:
            last = angles[-1]
            if last != 999:
                angles.append(last)
            else:
                angles.append((angles[-2] + 180) % 360)
        return cls(settings=data.get("settings", {}),
                   actions=list(data.get("actions", [])),
                   angle_data=angles)

    # Access helpers -----------------------------------------------------
    def get_angles(self) -> List[int]:
        return self.angle_data

    def get_actions(self, predicate: Callable[[dict], bool]) -> List[dict]:
        return [a for a in self.actions if predicate(a)]

    def remove_actions(self, predicate: Callable[[dict], bool]) -> List[dict]:
        removed = [a for a in self.actions if predicate(a)]
        self.actions = [a for a in self.actions if not predicate(a)]
        return removed

    def add_action(self, action: dict) -> None:
        self.actions.append(action)

    def save(self, path: Path) -> None:
        out = {
            "angleData": self.angle_data[:-1] if self.angle_data else [],
            "settings": self.settings,
            "actions": self.actions,
            "decorations": [],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=4)
