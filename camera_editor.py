"""Pygame based camera editor for ADOFAI levels.

This is a lightweight implementation that demonstrates how a camera editor
could be created using pygame for rendering and user interaction.  The editor
supports loading an existing `.adofai` file, editing MoveCamera events via
keyframes and visualising easing curves in real time.

Due to the size of the project only a minimal subset of the full feature set is
implemented here.  The code is structured so that additional functionality such
as more editing tools or better timeline management can be added easily.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import pygame
import numpy as np
import adofaipy

from easing import (
    EASING_FUNCTIONS,
    ElasticParams,
    elastic,
    linear,
)

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Keyframe:
    time: int
    x: float
    y: float
    zoom: float
    angle: float
    ease: str = "Linear"
    elastic_params: ElasticParams = field(default_factory=ElasticParams)


class CameraTrack:
    """Maintains a list of keyframes and interpolates between them."""

    def __init__(self) -> None:
        self.keyframes: List[Keyframe] = []
        self.selected_index: int | None = None

    def add_keyframe(
        self, time: int, x: float, y: float, zoom: float, angle: float,
        ease: str = "Linear"
    ) -> None:
        kf = Keyframe(time, x, y, zoom, angle, ease)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.time)

    def get_state_at(self, time_ms: int) -> Tuple[float, float, float, float]:
        """Linear interpolation between keyframes with easing applied."""
        if not self.keyframes:
            return (0.0, 0.0, 100.0, 0.0)
        if time_ms <= self.keyframes[0].time:
            kf = self.keyframes[0]
            return kf.x, kf.y, kf.zoom, kf.angle
        if time_ms >= self.keyframes[-1].time:
            kf = self.keyframes[-1]
            return kf.x, kf.y, kf.zoom, kf.angle
        for i in range(1, len(self.keyframes)):
            a = self.keyframes[i - 1]
            b = self.keyframes[i]
            if a.time <= time_ms <= b.time:
                alpha = (time_ms - a.time) / (b.time - a.time)
                # apply easing
                if b.ease == "Elastic":
                    alpha = elastic(alpha, b.elastic_params)
                else:
                    func = EASING_FUNCTIONS.get(b.ease, linear)
                    alpha = func(alpha)
                x = a.x * (1 - alpha) + b.x * alpha
                y = a.y * (1 - alpha) + b.y * alpha
                z = a.zoom * (1 - alpha) + b.zoom * alpha
                ang = a.angle * (1 - alpha) + b.angle * alpha
                return x, y, z, ang
        kf = self.keyframes[-1]
        return kf.x, kf.y, kf.zoom, kf.angle

    # Simple helpers for editing ------------------------------------------------
    def select_by_pos(self, pos: Tuple[float, float], radius: float = 5) -> None:
        px, py = pos
        for i, kf in enumerate(self.keyframes):
            if (kf.x - px) ** 2 + (kf.y - py) ** 2 <= radius ** 2:
                self.selected_index = i
                return
        self.selected_index = None

    def move_selected(self, dx: float, dy: float) -> None:
        if self.selected_index is None:
            return
        kf = self.keyframes[self.selected_index]
        kf.x += dx
        kf.y += dy


# ---------------------------------------------------------------------------
# Pygame visualisation
# ---------------------------------------------------------------------------


class Editor:
    TILE_COLOUR = (200, 200, 200)
    KEYFRAME_COLOUR = (255, 0, 0)
    CAM_COLOUR = (0, 0, 255)

    def __init__(self, adofai_path: Path, audio_path: Path) -> None:
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("ADOFAI Camera Editor")
        self.clock = pygame.time.Clock()

        # Load level and audio
        self.level = adofaipy.load(str(adofai_path))
        self.audio_path = audio_path
        pygame.mixer.music.load(str(audio_path))
        self.track = CameraTrack()
        self.tile_pos, self.tile_time = self._parse_tiles()
        self._init_keyframes_from_level()

        # state
        self.playing = False
        self.current_ms = 0

    # ------------------------------------------------------------------
    # Level parsing
    # ------------------------------------------------------------------
    def _parse_tiles(self) -> Tuple[List[Tuple[float, float]], List[int]]:
        tile_pos: List[Tuple[float, float]] = []
        tile_time: List[int] = []
        path = self.level.pathData
        bpm = self.level.settings.get("bpm", 120)
        spb = 60_000 / bpm
        t = 0
        x = y = ang = 0.0
        DIRS = {
            "D": 0, "E": 45, "W": 90, "Q": 135, "A": 180, "Z": 225,
            "S": 270, "C": 315,
            "R": 0, "T": 30, "Y": 60, "J": 120, "H": 150, "N": 210,
            "M": 240, "V": 270, "B": 300,
        }
        for ch in path:
            tile_pos.append((x, y))
            tile_time.append(int(t))
            d = DIRS.get(ch, 0)
            ang += d
            rad = math.radians(ang)
            x += math.cos(rad) * 50
            y += math.sin(rad) * 50
            t += spb
        return tile_pos, tile_time

    def _init_keyframes_from_level(self) -> None:
        for act in self.level.actions:
            if act.get("eventType") == "MoveCamera":
                floor = act.get("floor", 1)
                t = self.tile_time[min(floor - 1, len(self.tile_time) - 1)]
                pos = act.get("position", [0, 0])
                zoom = act.get("zoom", 100)
                angle = act.get("angleOffset", 0)
                ease = act.get("ease", "Linear")
                kf = Keyframe(t, pos[0], pos[1], zoom, angle, ease)
                self.track.keyframes.append(kf)
        self.track.keyframes.sort(key=lambda k: k.time)

    # ------------------------------------------------------------------
    # Main loop and drawing
    # ------------------------------------------------------------------
    def run(self) -> None:
        while True:
            dt = self.clock.tick(60)
            self._handle_events()
            if self.playing:
                self.current_ms += dt
                if self.current_ms >= self.tile_time[-1]:
                    self.playing = False
            self._draw()

    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self._toggle_play()
                if event.key == pygame.K_a:
                    self.track.move_selected(-1, 0)
                if event.key == pygame.K_d:
                    self.track.move_selected(1, 0)
                if event.key == pygame.K_w:
                    self.track.move_selected(0, -1)
                if event.key == pygame.K_s:
                    self.track.move_selected(0, 1)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                self.track.select_by_pos((mx, my))

    def _toggle_play(self) -> None:
        if self.playing:
            pygame.mixer.music.pause()
        else:
            pygame.mixer.music.play(start=self.current_ms / 1000.0)
        self.playing = not self.playing

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill((30, 30, 30))
        # Draw tiles
        if self.tile_pos:
            pygame.draw.lines(self.screen, self.TILE_COLOUR, False, self.tile_pos, 2)
        # Draw keyframes
        for kf in self.track.keyframes:
            colour = self.KEYFRAME_COLOUR
            pygame.draw.circle(self.screen, colour, (int(kf.x), int(kf.y)), 5)
        # Draw camera position
        cam_x, cam_y, _z, _a = self.track.get_state_at(self.current_ms)
        pygame.draw.circle(self.screen, self.CAM_COLOUR, (int(cam_x), int(cam_y)), 7)

        # Simple timeline at bottom
        tl_height = 40
        pygame.draw.rect(
            self.screen,
            (80, 80, 80),
            pygame.Rect(0, self.screen.get_height() - tl_height,
                        self.screen.get_width(), tl_height),
        )
        total = self.tile_time[-1] if self.tile_time else 1
        x = int(self.current_ms / total * self.screen.get_width())
        pygame.draw.rect(
            self.screen,
            (200, 200, 0),
            pygame.Rect(x - 2, self.screen.get_height() - tl_height, 4, tl_height),
        )

        # Easing preview for selected pair
        self._draw_easing_preview()
        pygame.display.flip()

    def _draw_easing_preview(self) -> None:
        idx = self.track.selected_index
        if idx is None or idx == 0:
            return
        a = self.track.keyframes[idx - 1]
        b = self.track.keyframes[idx]
        rect = pygame.Rect(10, 10, 200, 100)
        pygame.draw.rect(self.screen, (50, 50, 50), rect, 1)
        points = []
        for i in range(100):
            t = i / 99
            if b.ease == "Elastic":
                y = elastic(t, b.elastic_params)
            else:
                func = EASING_FUNCTIONS.get(b.ease, linear)
                y = func(t)
            px = rect.left + t * rect.width
            py = rect.bottom - y * rect.height
            points.append((px, py))
        if points:
            pygame.draw.lines(self.screen, (0, 255, 0), False, points, 2)


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

    def save(self, out_path: Path) -> None:
        actions = [a for a in self.level.actions
                   if a.get("eventType") != "MoveCamera"]
        for kf in self.track.keyframes:
            floor = self._floor_for_time(kf.time)
            act = {
                "floor": floor,
                "eventType": "MoveCamera",
                "duration": 0,
                "relativeTo": "World",
                "position": [kf.x, kf.y],
                "zoom": kf.zoom,
                "angleOffset": kf.angle,
                "ease": kf.ease,
            }
            if kf.ease == "Elastic":
                act["elasticParams"] = {
                    "oscillations": kf.elastic_params.oscillations,
                    "decay": kf.elastic_params.decay,
                }
            actions.append(act)
        self.level.actions = actions
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(self.level.dict(), f, ensure_ascii=False, indent=2)

    def _floor_for_time(self, t: int) -> int:
        for i, tm in enumerate(self.tile_time):
            if tm >= t:
                return i + 1
        return len(self.tile_time)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ADOFAI camera editor")
    parser.add_argument("adofai", type=Path, help="Path to .adofai file")
    parser.add_argument("audio", type=Path, help="Path to audio file")
    args = parser.parse_args()

    editor = Editor(args.adofai, args.audio)
    editor.run()


if __name__ == "__main__":
    main()

