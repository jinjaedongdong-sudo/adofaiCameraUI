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

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import pygame
from tkinter import Tk, filedialog, simpledialog

# Use adofaipy for reading and writing ADOFAI levels
from adofaipy import LevelDict

from easing import (
    EASING_FUNCTIONS,
    BackParams,
    BounceParams,
    ElasticParams,
    cubic_bezier,
    elastic,
    ease_in_back,
    ease_in_bounce,
    ease_in_out_back,
    ease_in_out_bounce,
    ease_out_back,
    ease_out_bounce,
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
    back_params: BackParams = field(default_factory=BackParams)
    bounce_params: BounceParams = field(default_factory=BounceParams)
    # Control points for custom bezier easing (p1x, p1y) and (p2x, p2y)
    bezier_p1: Tuple[float, float] = (0.25, 0.25)
    bezier_p2: Tuple[float, float] = (0.75, 0.75)
    custom_ease: List[float] | None = None


class CameraTrack:
    """Maintains a list of keyframes and interpolates between them."""

    def __init__(self) -> None:
        self.keyframes: List[Keyframe] = []
        self.selected_index: int | None = None

    def add_keyframe(
        self, time: int, x: float, y: float, zoom: float, angle: float,
        ease: str = "Linear"
    ) -> None:
        """Add a keyframe and select it."""
        kf = Keyframe(time, x, y, zoom, angle, ease)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.time)
        self.selected_index = self.keyframes.index(kf)

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
                if b.custom_ease:
                    idx = min(int(alpha * (len(b.custom_ease) - 1)), len(b.custom_ease) - 1)
                    alpha = b.custom_ease[idx]
                else:
                    if b.ease == "Elastic":
                        alpha = elastic(alpha, b.elastic_params)
                    elif "Back" in b.ease:
                        if b.ease == "EaseInBack":
                            alpha = ease_in_back(alpha, b.back_params)
                        elif b.ease == "EaseOutBack":
                            alpha = ease_out_back(alpha, b.back_params)
                        else:
                            alpha = ease_in_out_back(alpha, b.back_params)
                    elif "Bounce" in b.ease:
                        if b.ease == "EaseInBounce":
                            alpha = ease_in_bounce(alpha, b.bounce_params)
                        elif b.ease == "EaseOutBounce":
                            alpha = ease_out_bounce(alpha, b.bounce_params)
                        else:
                            alpha = ease_in_out_bounce(alpha, b.bounce_params)
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

    def current(self) -> Keyframe | None:
        if self.selected_index is None:
            return None
        return self.keyframes[self.selected_index]

    def move_selected(self, dx: float, dy: float) -> None:
        if self.selected_index is None:
            return
        kf = self.keyframes[self.selected_index]
        kf.x += dx
        kf.y += dy

    def move_time_selected(self, dt: int) -> None:
        """Shift the selected keyframe in time."""
        if self.selected_index is None:
            return
        kf = self.keyframes[self.selected_index]
        kf.time = max(0, kf.time + dt)
        self.keyframes.sort(key=lambda k: k.time)
        self.selected_index = self.keyframes.index(kf)

    def delete_selected(self) -> None:
        if self.selected_index is None:
            return
        del self.keyframes[self.selected_index]
        if self.keyframes:
            self.selected_index = min(self.selected_index, len(self.keyframes) - 1)
        else:
            self.selected_index = None

    def duplicate_selected(self, offset_ms: int = 100) -> None:
        if self.selected_index is None:
            return
        src = self.keyframes[self.selected_index]
        dup = Keyframe(
            src.time + offset_ms,
            src.x,
            src.y,
            src.zoom,
            src.angle,
            src.ease,
            ElasticParams(src.elastic_params.oscillations, src.elastic_params.decay),
            BackParams(src.back_params.overshoot),
            BounceParams(src.bounce_params.n1, src.bounce_params.d1),
            src.bezier_p1,
            src.bezier_p2,
            src.custom_ease[:] if src.custom_ease else None,
        )
        self.keyframes.append(dup)
        self.keyframes.sort(key=lambda k: k.time)
        self.selected_index = self.keyframes.index(dup)

    def select_next(self) -> None:
        if not self.keyframes:
            return
        if self.selected_index is None:
            self.selected_index = 0
        else:
            self.selected_index = min(self.selected_index + 1, len(self.keyframes) - 1)

    def select_prev(self) -> None:
        if not self.keyframes:
            return
        if self.selected_index is None:
            self.selected_index = len(self.keyframes) - 1
        else:
            self.selected_index = max(self.selected_index - 1, 0)

    def cycle_ease(self, direction: int = 1) -> None:
        if self.selected_index is None:
            return
        kf = self.keyframes[self.selected_index]
        keys = list(EASING_FUNCTIONS.keys()) + ["Elastic", "Bezier"]
        try:
            idx = keys.index(kf.ease)
        except ValueError:
            idx = 0
        kf.ease = keys[(idx + direction) % len(keys)]
        kf.custom_ease = None


# ---------------------------------------------------------------------------
# Pygame visualisation
# ---------------------------------------------------------------------------


class ParamSlider:
    def __init__(self, label: str, min_val: float, max_val: float,
                 getter, setter) -> None:
        self.label = label
        self.min = min_val
        self.max = max_val
        self.getter = getter
        self.setter = setter
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.dragging = False

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self._update(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update(event.pos[0])

    def _update(self, mx: int) -> None:
        pos = (mx - self.rect.x) / self.rect.width
        pos = max(0.0, min(1.0, pos))
        val = self.min + pos * (self.max - self.min)
        self.setter(val)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font,
             x: int, y: int) -> None:
        value = self.getter()
        label = f"{self.label}: {value:.2f}" if isinstance(value, float) else f"{self.label}: {value}"
        txt = font.render(label, True, (230, 230, 230))
        surface.blit(txt, (x, y))
        y += 18
        width = 160
        self.rect = pygame.Rect(x, y, width, 8)
        pygame.draw.rect(surface, (80, 80, 80), self.rect)
        pos = (value - self.min) / (self.max - self.min)
        knob_x = self.rect.x + pos * self.rect.width
        pygame.draw.rect(surface, (200, 200, 0), pygame.Rect(knob_x - 4, y - 4, 8, 16))


class Button:
    def __init__(self, rect: pygame.Rect, text: str, callback) -> None:
        self.rect = rect
        self.text = text
        self.callback = callback

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, (70, 70, 70), self.rect)
        txt = font.render(self.text, True, (255, 255, 255))
        surface.blit(txt, txt.get_rect(center=self.rect.center))


class BezierEditor:
    """Simple editor for a cubic Bezier easing curve."""

    SIZE = 160

    def __init__(self, kf: Keyframe, render_cb) -> None:
        self.kf = kf
        self.render_cb = render_cb
        self.rect = pygame.Rect(0, 0, self.SIZE, self.SIZE)
        self.dragging: int | None = None

    def set_keyframe(self, kf: Keyframe) -> None:
        self.kf = kf
        self.kf.custom_ease = self.render_cb(self.kf)

    def _p1_pixel(self) -> Tuple[float, float]:
        return (
            self.rect.x + self.kf.bezier_p1[0] * self.rect.width,
            self.rect.y + (1 - self.kf.bezier_p1[1]) * self.rect.height,
        )

    def _p2_pixel(self) -> Tuple[float, float]:
        return (
            self.rect.x + self.kf.bezier_p2[0] * self.rect.width,
            self.rect.y + (1 - self.kf.bezier_p2[1]) * self.rect.height,
        )

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                p1 = self._p1_pixel()
                p2 = self._p2_pixel()
                if (event.pos[0] - p1[0]) ** 2 + (event.pos[1] - p1[1]) ** 2 <= 100:
                    self.dragging = 1
                elif (event.pos[0] - p2[0]) ** 2 + (event.pos[1] - p2[1]) ** 2 <= 100:
                    self.dragging = 2
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = None
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            x = (event.pos[0] - self.rect.x) / self.rect.width
            y = 1 - (event.pos[1] - self.rect.y) / self.rect.height
            x = max(0.0, min(1.0, x))
            y = max(0.0, min(1.0, y))
            if self.dragging == 1:
                self.kf.bezier_p1 = (x, y)
            else:
                self.kf.bezier_p2 = (x, y)
            self.kf.custom_ease = self.render_cb(self.kf)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, x: int, y: int) -> None:
        self.rect.topleft = (x, y)
        pygame.draw.rect(surface, (80, 80, 80), self.rect, 1)
        # Draw curve
        func = cubic_bezier(
            self.kf.bezier_p1[0],
            self.kf.bezier_p1[1],
            self.kf.bezier_p2[0],
            self.kf.bezier_p2[1],
        )
        pts = []
        for i in range(21):
            t = i / 20
            px = x + t * self.rect.width
            py = y + (1 - func(t)) * self.rect.height
            pts.append((px, py))
        pygame.draw.lines(surface, (200, 200, 0), False, pts, 2)
        # Draw control points and handles
        p1 = self._p1_pixel()
        p2 = self._p2_pixel()
        start = (self.rect.x, self.rect.y + self.rect.height)
        end = (self.rect.x + self.rect.width, self.rect.y)
        pygame.draw.line(surface, (150, 150, 150), start, p1)
        pygame.draw.line(surface, (150, 150, 150), end, p2)
        pygame.draw.circle(surface, (0, 255, 0), p1, 5)
        pygame.draw.circle(surface, (0, 255, 0), p2, 5)


class ParamPanel:
    BG = (45, 45, 45)

    def __init__(self, render_cb) -> None:
        self.kf: Keyframe | None = None
        self.sliders: list[ParamSlider] = []
        self.render_cb = render_cb
        self.bezier_editor: BezierEditor | None = None

    def set_keyframe(self, kf: Keyframe | None) -> None:
        if self.kf is kf and (kf is None or self.kf.ease == kf.ease):
            return
        self.kf = kf
        self.sliders.clear()
        self.bezier_editor = None
        if kf is None:
            return
        if kf.ease == "Elastic":
            self.sliders.append(
                ParamSlider(
                    "Oscillations", 1, 10,
                    lambda: kf.elastic_params.oscillations,
                    lambda v: setattr(kf.elastic_params, "oscillations", int(v)),
                )
            )
            self.sliders.append(
                ParamSlider(
                    "Decay", 0.1, 10.0,
                    lambda: kf.elastic_params.decay,
                    lambda v: setattr(kf.elastic_params, "decay", v),
                )
            )
        elif "Back" in kf.ease:
            self.sliders.append(
                ParamSlider(
                    "Overshoot", 0.0, 5.0,
                    lambda: kf.back_params.overshoot,
                    lambda v: setattr(kf.back_params, "overshoot", v),
                )
            )
        elif "Bounce" in kf.ease:
            self.sliders.append(
                ParamSlider(
                    "n1", 5.0, 10.0,
                    lambda: kf.bounce_params.n1,
                    lambda v: setattr(kf.bounce_params, "n1", v),
                )
            )
            self.sliders.append(
                ParamSlider(
                    "d1", 2.0, 4.0,
                    lambda: kf.bounce_params.d1,
                    lambda v: setattr(kf.bounce_params, "d1", v),
                )
            )
        elif kf.ease == "Bezier":
            self.bezier_editor = BezierEditor(kf, self.render_cb)
            kf.custom_ease = self.render_cb(kf)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.bezier_editor:
            self.bezier_editor.handle_event(event)
        for s in self.sliders:
            s.handle_event(event)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if self.kf is None:
            return
        width = 220
        rect = pygame.Rect(surface.get_width() - width, 0, width, surface.get_height())
        pygame.draw.rect(surface, self.BG, rect)
        y = 20
        txt = font.render(f"Ease: {self.kf.ease}", True, (255, 255, 255))
        surface.blit(txt, (rect.x + 10, y))
        y += 40
        for s in self.sliders:
            s.draw(surface, font, rect.x + 10, y)
            y += 40
        if self.bezier_editor:
            self.bezier_editor.draw(surface, font, rect.x + 10, y)
class Editor:
    TILE_COLOUR = (200, 200, 200)
    KEYFRAME_COLOUR = (255, 0, 0)
    CAM_COLOUR = (0, 0, 255)
    RENDER_CAM_COLOUR = (255, 150, 0)

    def __init__(self, adofai_path: Path, audio_path: Path) -> None:
        pygame.init()
        pygame.mixer.init()
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("ADOFAI Camera Editor")
        self.clock = pygame.time.Clock()

        # Load level and audio
        self.level = LevelDict(str(adofai_path))
        self.audio_path = audio_path
        pygame.mixer.music.load(str(audio_path))
        self.track = CameraTrack()
        self.tile_pos, self.tile_time = self._parse_tiles()
        self._init_keyframes_from_level()

        # state
        self.playing = False
        self.play_start_ms = 0
        self.current_ms = 0
        self.font = pygame.font.SysFont("arial", 16)
        self.param_panel = ParamPanel(self._render_custom_ease)
        # ui buttons
        self.buttons: list[Button] = [
            Button(pygame.Rect(10, 10, 100, 30), "Open Level", self._open_level),
            Button(pygame.Rect(120, 10, 100, 30), "Open Audio", self._open_audio),
            Button(pygame.Rect(230, 10, 100, 30), "Save", self._save_dialog),
        ]
        # timeline state
        self.timeline_height = 120
        self.timeline_rect = pygame.Rect(0, 0, 0, 0)
        self.timeline_scrubbing = False

    # ------------------------------------------------------------------
    # Level parsing
    # ------------------------------------------------------------------
    def _parse_tiles(self) -> Tuple[List[Tuple[float, float]], List[int]]:
        tile_pos: List[Tuple[float, float]] = []
        tile_time: List[int] = []
        bpm = self.level.settings.get("bpm", 120)
        spb = 60_000 / bpm
        t = 0
        x = y = 0.0
        angles = self.level.getAngles()[:-1]
        for ang in angles:
            tile_pos.append((x, y))
            tile_time.append(int(t))
            rad = math.radians(ang)
            x += math.cos(rad) * 50
            y += math.sin(rad) * 50
            t += spb
        return tile_pos, tile_time

    def _init_keyframes_from_level(self) -> None:
        for act in self.level.getActions(lambda a: a.get("eventType") == "MoveCamera"):
            floor = act.get("floor", 1)
            t = self.tile_time[min(floor - 1, len(self.tile_time) - 1)]
            pos = act.get("position", [0, 0])
            zoom = act.get("zoom", 100)
            angle = act.get("angleOffset", 0)
            ease = act.get("ease", "Linear")
            kf = Keyframe(t, pos[0], pos[1], zoom, angle, ease)
            if "bezier" in act:
                bez = act["bezier"]
                kf.ease = "Bezier"
                kf.bezier_p1 = (bez[0], bez[1])
                kf.bezier_p2 = (bez[2], bez[3])
            if "customEase" in act:
                kf.custom_ease = act["customEase"]
            else:
                kf.custom_ease = self._render_custom_ease(kf)
            if ease == "Elastic" and "elasticParams" in act:
                ep = act["elasticParams"]
                kf.elastic_params = ElasticParams(ep.get("oscillations", 3), ep.get("decay", 3.0))
            if "Back" in ease and "backParams" in act:
                bp = act["backParams"]
                kf.back_params = BackParams(bp.get("overshoot", 1.70158))
            if "Bounce" in ease and "bounceParams" in act:
                bp2 = act["bounceParams"]
                kf.bounce_params = BounceParams(bp2.get("n1", 7.5625), bp2.get("d1", 2.75))
            self.track.keyframes.append(kf)
        self.track.keyframes.sort(key=lambda k: k.time)

    # ------------------------------------------------------------------
    # Main loop and drawing
    # ------------------------------------------------------------------
    def run(self) -> None:
        while True:
            self.clock.tick(60)
            self._handle_events()
            if self.playing:
                pos = pygame.mixer.music.get_pos()
                if pos == -1:
                    self._stop_playback()
                else:
                    self.current_ms = self.play_start_ms + pos
                    if self.current_ms >= self.tile_time[-1]:
                        self._stop_playback()
            self._draw()

    # ------------------------------------------------------------------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            self.param_panel.handle_event(event)
            for btn in self.buttons:
                btn.handle_event(event)
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self._toggle_play()
                elif event.key == pygame.K_n:
                    x, y, z, a = self.track.get_state_at(self.current_ms)
                    self.track.add_keyframe(self.current_ms, x, y, z, a)
                elif event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
                    self.track.delete_selected()
                elif event.key == pygame.K_d and event.mod & pygame.KMOD_CTRL:
                    self.track.duplicate_selected()
                elif event.key == pygame.K_COMMA:
                    self.track.select_prev()
                    self._jump_to_selected()
                elif event.key == pygame.K_PERIOD:
                    self.track.select_next()
                    self._jump_to_selected()
                elif event.key == pygame.K_TAB:
                    direction = -1 if event.mod & pygame.KMOD_SHIFT else 1
                    self.track.cycle_ease(direction)
                elif event.key == pygame.K_a:
                    self.track.move_selected(-1, 0)
                elif event.key == pygame.K_d:
                    self.track.move_selected(1, 0)
                elif event.key == pygame.K_w:
                    self.track.move_selected(0, -1)
                elif event.key == pygame.K_s:
                    self.track.move_selected(0, 1)
                elif event.key == pygame.K_LEFT and event.mod & pygame.KMOD_SHIFT:
                    self.track.move_time_selected(-50)
                elif event.key == pygame.K_RIGHT and event.mod & pygame.KMOD_SHIFT:
                    self.track.move_time_selected(50)
                elif event.key == pygame.K_x and event.mod & pygame.KMOD_CTRL:
                    self._prompt_selected("x")
                elif event.key == pygame.K_y and event.mod & pygame.KMOD_CTRL:
                    self._prompt_selected("y")
                elif event.key == pygame.K_z and event.mod & pygame.KMOD_CTRL:
                    self._prompt_selected("zoom")
                elif event.key == pygame.K_a and event.mod & pygame.KMOD_CTRL:
                    self._prompt_selected("angle")
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if self.timeline_rect.collidepoint(event.pos):
                    self._set_time_from_timeline(mx)
                    self.timeline_scrubbing = True
                    self._stop_playback()
                elif mx < self.screen.get_width() - 220:
                    self.track.select_by_pos((mx, my))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.timeline_scrubbing = False
            elif event.type == pygame.MOUSEMOTION and self.timeline_scrubbing:
                self._set_time_from_timeline(event.pos[0])
        self.param_panel.set_keyframe(self.track.current())

    def _stop_playback(self) -> None:
        if self.playing:
            pygame.mixer.music.stop()
            self.playing = False

    def _toggle_play(self) -> None:
        if self.playing:
            self.current_ms = self.play_start_ms + max(0, pygame.mixer.music.get_pos())
            pygame.mixer.music.stop()
            self.playing = False
        else:
            self.play_start_ms = self.current_ms
            pygame.mixer.music.play(start=self.current_ms / 1000.0)
            self.playing = True

    def _jump_to_selected(self) -> None:
        if self.track.selected_index is None:
            return
        self.current_ms = self.track.keyframes[self.track.selected_index].time

    def _set_time_from_timeline(self, mx: int) -> None:
        panel_w = 220
        width = self.screen.get_width() - panel_w
        total = self.tile_time[-1] if self.tile_time else 1
        pos = max(0, min(width, mx))
        self.current_ms = int(pos / max(1, width) * total)

    # ------------------------------------------------------------------
    def _draw(self) -> None:
        self.screen.fill((30, 30, 30))
        # Grid for easier spatial editing
        panel_w = 220
        width = self.screen.get_width() - panel_w
        height = self.screen.get_height() - self.timeline_height
        for gx in range(0, width, 50):
            pygame.draw.line(self.screen, (45, 45, 45), (gx, 0), (gx, height))
        for gy in range(0, height, 50):
            pygame.draw.line(self.screen, (45, 45, 45), (0, gy), (width, gy))

        # Draw tiles
        if self.tile_pos:
            pygame.draw.lines(self.screen, self.TILE_COLOUR, False, self.tile_pos, 2)
        # Draw keyframes
        for i, kf in enumerate(self.track.keyframes):
            colour = (255, 255, 0) if i == self.track.selected_index else self.KEYFRAME_COLOUR
            pygame.draw.circle(self.screen, colour, (int(kf.x), int(kf.y)), 5)
        # Draw camera position
        cam_x, cam_y, _z, _a = self.track.get_state_at(self.current_ms)
        cam_col = self.RENDER_CAM_COLOUR if self.playing else self.CAM_COLOUR
        pygame.draw.circle(self.screen, cam_col, (int(cam_x), int(cam_y)), 7)
        pygame.draw.line(self.screen, cam_col, (int(cam_x) - 10, int(cam_y)), (int(cam_x) + 10, int(cam_y)))
        pygame.draw.line(self.screen, cam_col, (int(cam_x), int(cam_y) - 10), (int(cam_x), int(cam_y) + 10))

        # Timeline at bottom
        self._draw_timeline()

        # Easing preview for selected pair
        self._draw_easing_preview()
        # Parameter panel
        self.param_panel.draw(self.screen, self.font)
        for btn in self.buttons:
            btn.draw(self.screen, self.font)
        pygame.display.flip()

    def _draw_timeline(self) -> None:
        panel_w = 220
        width = self.screen.get_width() - panel_w
        y = self.screen.get_height() - self.timeline_height
        self.timeline_rect = pygame.Rect(0, y, width, self.timeline_height)
        pygame.draw.rect(self.screen, (60, 60, 60), self.timeline_rect)
        total = self.tile_time[-1] if self.tile_time else 1
        row_h = self.timeline_height // 4
        params = [
            ("x", (255, 80, 80)),
            ("y", (80, 255, 80)),
            ("zoom", (80, 80, 255)),
            ("angle", (255, 255, 80)),
        ]
        for idx, (attr, colour) in enumerate(params):
            row_top = y + idx * row_h
            pygame.draw.line(
                self.screen, (80, 80, 80), (0, row_top + row_h // 2), (width, row_top + row_h // 2)
            )
            vals = [getattr(kf, attr) for kf in self.track.keyframes]
            if not vals:
                continue
            vmin, vmax = min(vals), max(vals)
            if vmin == vmax:
                vmin -= 1
                vmax += 1
            sample = 200
            points: list[tuple[int, float]] = []
            for i in range(sample):
                t = i / (sample - 1) * total
                x, y_val, z, a = self.track.get_state_at(int(t))
                value = {"x": x, "y": y_val, "zoom": z, "angle": a}[attr]
                px = int(i / (sample - 1) * width)
                py = row_top + row_h - (value - vmin) / (vmax - vmin) * row_h
                points.append((px, py))
            if points:
                pygame.draw.lines(self.screen, colour, False, points, 2)
            for kf in self.track.keyframes:
                px = int(kf.time / total * width)
                val = getattr(kf, attr)
                py = row_top + row_h - (val - vmin) / (vmax - vmin) * row_h
                pygame.draw.circle(self.screen, colour, (px, int(py)), 3)
            label = self.font.render(attr, True, colour)
            self.screen.blit(label, (5, row_top + 2))
        scrub_x = int(self.current_ms / total * width)
        pygame.draw.line(
            self.screen,
            (230, 230, 230),
            (scrub_x, y),
            (scrub_x, y + self.timeline_height),
            2,
        )
        time_txt = self.font.render(f"{self.current_ms/1000:.2f}s", True, (255, 255, 255))
        self.screen.blit(time_txt, (scrub_x + 5, y + 5))

    def _draw_easing_preview(self) -> None:
        idx = self.track.selected_index
        if idx is None or idx == 0:
            return
        a = self.track.keyframes[idx - 1]
        b = self.track.keyframes[idx]
        rect = pygame.Rect(10, 10, 200, 100)
        pygame.draw.rect(self.screen, (50, 50, 50), rect, 1)
        curve = self._render_custom_ease(b, samples=100)
        points = []
        for i, y in enumerate(curve):
            t = i / (len(curve) - 1)
            px = rect.left + t * rect.width
            py = rect.bottom - y * rect.height
            points.append((px, py))
        if points:
            pygame.draw.lines(self.screen, (0, 255, 0), False, points, 2)


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

    def save(self, out_path: Path) -> None:
        self.level.removeActions(lambda a: a.get("eventType") == "MoveCamera")
        for kf in self.track.keyframes:
            floor = self._floor_for_time(kf.time)
            curve = self._render_custom_ease(kf)
            kf.custom_ease = curve
            ease_val = kf.ease if kf.ease != "Bezier" else "Linear"
            act = {
                "floor": floor,
                "eventType": "MoveCamera",
                "duration": 0,
                "relativeTo": "World",
                "position": [kf.x, kf.y],
                "zoom": kf.zoom,
                "angleOffset": kf.angle,
                "ease": ease_val,
                "customEase": curve,
            }
            if kf.ease == "Bezier":
                act["bezier"] = [
                    kf.bezier_p1[0],
                    kf.bezier_p1[1],
                    kf.bezier_p2[0],
                    kf.bezier_p2[1],
                ]
            if kf.ease == "Elastic":
                act["elasticParams"] = {
                    "oscillations": kf.elastic_params.oscillations,
                    "decay": kf.elastic_params.decay,
                }
            if "Back" in kf.ease:
                act["backParams"] = {
                    "overshoot": kf.back_params.overshoot,
                }
            if "Bounce" in kf.ease:
                act["bounceParams"] = {
                    "n1": kf.bounce_params.n1,
                    "d1": kf.bounce_params.d1,
                }
            self.level.addAction(act)
        self.level.writeToFile(str(out_path))

    def _floor_for_time(self, t: int) -> int:
        for i, tm in enumerate(self.tile_time):
            if tm >= t:
                return i + 1
        return len(self.tile_time)

    def _render_custom_ease(self, kf: Keyframe, samples: int = 60) -> List[float]:
        """Render the easing curve for ``kf`` using only built-in functions."""
        t_values = [i / (samples - 1) for i in range(samples)]
        if kf.ease == "Elastic":
            func = lambda t: elastic(t, kf.elastic_params)
        elif "Back" in kf.ease:
            if kf.ease == "EaseInBack":
                func = lambda t: ease_in_back(t, kf.back_params)
            elif kf.ease == "EaseOutBack":
                func = lambda t: ease_out_back(t, kf.back_params)
            else:
                func = lambda t: ease_in_out_back(t, kf.back_params)
        elif "Bounce" in kf.ease:
            if kf.ease == "EaseInBounce":
                func = lambda t: ease_in_bounce(t, kf.bounce_params)
            elif kf.ease == "EaseOutBounce":
                func = lambda t: ease_out_bounce(t, kf.bounce_params)
            else:
                func = lambda t: ease_in_out_bounce(t, kf.bounce_params)
        elif kf.ease == "Bezier":
            func = cubic_bezier(
                kf.bezier_p1[0],
                kf.bezier_p1[1],
                kf.bezier_p2[0],
                kf.bezier_p2[1],
            )
        else:
            func = EASING_FUNCTIONS.get(kf.ease, linear)
        return [func(t) for t in t_values]

    # ------------------------------------------------------------------
    # File operations and prompts
    # ------------------------------------------------------------------

    def _open_level(self) -> None:
        self._stop_playback()
        root = Tk(); root.withdraw()
        path = filedialog.askopenfilename(filetypes=[("ADOFAI", "*.adofai")])
        root.destroy()
        if not path:
            return
        try:
            self.level = LevelDict(path)
        except Exception as exc:
            print(f"Failed to load level: {exc}")
            return
        self.track = CameraTrack()
        self.tile_pos, self.tile_time = self._parse_tiles()
        self._init_keyframes_from_level()
        self.current_ms = 0

    def _open_audio(self) -> None:
        self._stop_playback()
        root = Tk(); root.withdraw()
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.ogg *.mp3 *.wav")])
        root.destroy()
        if not path:
            return
        try:
            pygame.mixer.music.load(path)
            self.audio_path = Path(path)
        except pygame.error as exc:
            print(f"Failed to load audio: {exc}")

    def _save_dialog(self) -> None:
        root = Tk(); root.withdraw()
        path = filedialog.asksaveasfilename(defaultextension=".adofai", filetypes=[("ADOFAI", "*.adofai")])
        root.destroy()
        if not path:
            return
        self.save(Path(path))

    def _prompt_selected(self, field: str) -> None:
        kf = self.track.current()
        if kf is None:
            return
        root = Tk(); root.withdraw()
        current = getattr(kf, field)
        val = simpledialog.askfloat("Set value", f"Enter {field}", initialvalue=current)
        root.destroy()
        if val is not None:
            setattr(kf, field, val)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ADOFAI camera editor")
    parser.add_argument("adofai", type=Path, nargs="?", help="Path to .adofai file")
    parser.add_argument("audio", type=Path, nargs="?", help="Path to audio file")
    args = parser.parse_args()

    if args.adofai and args.audio:
        editor = Editor(args.adofai, args.audio)
    else:
        root = Tk(); root.withdraw()
        adofai_path = filedialog.askopenfilename(filetypes=[("ADOFAI", "*.adofai")])
        audio_path = filedialog.askopenfilename(filetypes=[("Audio", "*.ogg *.mp3 *.wav")])
        root.destroy()
        if not adofai_path or not audio_path:
            print("No files selected")
            return
        editor = Editor(Path(adofai_path), Path(audio_path))
    editor.run()


if __name__ == "__main__":
    main()

