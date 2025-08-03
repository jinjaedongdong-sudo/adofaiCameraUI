"""Lightweight wrapper around :mod:`adofaipy` for loading and saving levels.

The original project expected a small ``Level`` helper providing ``load`` and
``dict`` methods.  The previous repository did not include an implementation
and performed JSON parsing manually.  This module re-introduces that helper but
delegates all parsing and serialisation to the `adofaipy` package as requested
by the user instructions.

Only a tiny subset of the full API is implemented – enough for the camera
editor to query settings, actions and path data and to write the modified level
back to disk.  The heavy lifting of validating and writing the ``.adofai`` file
is handled by :class:`adofaipy.LevelDict`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from adofaipy import LevelDict


@dataclass
class Level:
    """Container for an ADOFAI level using :mod:`adofaipy` under the hood."""

    data: Dict[str, Any]
    path: Path | None = None

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def load(cls, filename: Path) -> "Level":
        """Parse ``filename`` using :mod:`adofaipy` and return a :class:`Level`.

        Parameters
        ----------
        filename:
            Path to the ``.adofai`` file.
        """

        ld = LevelDict(str(filename))
        data = ld._getFileDict()  # type: ignore[attr-defined]
        if "pathData" not in data and "angleData" in data:
            # ``LevelDict`` exposes ``angleData`` when the file does not contain
            # ``pathData``.  For the purposes of the editor we fall back to that
            # so existing files continue to load correctly.
            data["pathData"] = data.get("angleData", [])
        return cls(data=data, path=Path(filename))

    # ------------------------------------------------------------------
    # Accessors used by the editor
    # ------------------------------------------------------------------
    @property
    def actions(self) -> List[Dict[str, Any]]:
        return self.data.setdefault("actions", [])

    @actions.setter
    def actions(self, value: List[Dict[str, Any]]) -> None:
        self.data["actions"] = value

    @property
    def settings(self) -> Dict[str, Any]:
        return self.data.setdefault("settings", {})

    @property
    def pathData(self) -> List[Any]:
        return self.data.get("pathData", [])

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def dict(self) -> Dict[str, Any]:
        """Return the internal dictionary representation."""

        return self.data

    def write(self, filename: Path | None = None) -> None:
        """Write the level to ``filename`` using :mod:`adofaipy`.

        If ``filename`` is ``None`` the path supplied to :meth:`load` is used.
        """

        dest = filename or self.path
        if dest is None:
            raise ValueError("No filename supplied for Level.write")
        # ``LevelDict`` exposes a private helper for writing dictionaries.  We
        # create a temporary instance and delegate the heavy lifting to it.
        tmp = LevelDict("", encoding="utf-8")
        tmp._writeDictToFile(self.data, str(dest))  # type: ignore[attr-defined]

