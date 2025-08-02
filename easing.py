"""Collection of easing functions used by the camera editor.

Provides both simple easing functions and parameterised versions such as
elastic where the number of oscillations can be configured.  All easing
functions accept a value ``t`` in the range ``[0, 1]`` and return the eased
value in the same range.

The module is intentionally lightweight so it can be imported without any GUI
initialisation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable

# The goal of this module is to mirror the variety of easing curves commonly
# available in professional animation tools.  Each function accepts a ``t``
# parameter in the range ``[0, 1]`` and returns a value in the same range.

# Only standard library modules are used so the functions can be imported by
# other scripts without pulling in heavy dependencies.

# ---------------------------------------------------------------------------
# Basic easing functions
# ---------------------------------------------------------------------------

def linear(t: float) -> float:
    """Linear interpolation."""
    return t


def ease_in_quad(t: float) -> float:
    return t * t


def ease_out_quad(t: float) -> float:
    return t * (2 - t)


def ease_in_out_quad(t: float) -> float:
    if t < 0.5:
        return 2 * t * t
    return -1 + (4 - 2 * t) * t


def ease_in_cubic(t: float) -> float:
    return t * t * t


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4 * t * t * t
    return 1 - (-2 * t + 2) ** 3 / 2


def ease_in_quart(t: float) -> float:
    return t ** 4


def ease_out_quart(t: float) -> float:
    return 1 - (1 - t) ** 4


def ease_in_out_quart(t: float) -> float:
    if t < 0.5:
        return 8 * t ** 4
    return 1 - (-2 * t + 2) ** 4 / 2


def ease_in_quint(t: float) -> float:
    return t ** 5


def ease_out_quint(t: float) -> float:
    return 1 - (1 - t) ** 5


def ease_in_out_quint(t: float) -> float:
    if t < 0.5:
        return 16 * t ** 5
    return 1 - (-2 * t + 2) ** 5 / 2


def ease_in_sine(t: float) -> float:
    return 1 - math.cos((t * math.pi) / 2)


def ease_out_sine(t: float) -> float:
    return math.sin((t * math.pi) / 2)


def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_expo(t: float) -> float:
    if t == 0:
        return 0.0
    return 2 ** (10 * (t - 1))


def ease_out_expo(t: float) -> float:
    if t == 1:
        return 1.0
    return 1 - 2 ** (-10 * t)


def ease_in_out_expo(t: float) -> float:
    if t == 0:
        return 0.0
    if t == 1:
        return 1.0
    if t < 0.5:
        return 2 ** (20 * t - 10) / 2
    return (2 - 2 ** (-20 * t + 10)) / 2


def ease_in_circ(t: float) -> float:
    return 1 - math.sqrt(1 - t * t)


def ease_out_circ(t: float) -> float:
    return math.sqrt(1 - (t - 1) ** 2)


def ease_in_out_circ(t: float) -> float:
    if t < 0.5:
        return (1 - math.sqrt(1 - (2 * t) ** 2)) / 2
    return (math.sqrt(1 - (-2 * t + 2) ** 2) + 1) / 2


@dataclass
class BackParams:
    overshoot: float = 1.70158


def ease_in_back(t: float, params: BackParams = BackParams()) -> float:
    c1 = params.overshoot
    c3 = c1 + 1
    return c3 * t ** 3 - c1 * t ** 2


def ease_out_back(t: float, params: BackParams = BackParams()) -> float:
    c1 = params.overshoot
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_in_out_back(t: float, params: BackParams = BackParams()) -> float:
    c1 = params.overshoot
    c2 = c1 * 1.525
    if t < 0.5:
        return ((2 * t) ** 2 * ((c2 + 1) * 2 * t - c2)) / 2
    return ((2 * t - 2) ** 2 * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


@dataclass
class BounceParams:
    n1: float = 7.5625
    d1: float = 2.75


def ease_out_bounce(t: float, params: BounceParams = BounceParams()) -> float:
    n1 = params.n1
    d1 = params.d1
    if t < 1 / d1:
        return n1 * t * t
    if t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def ease_in_bounce(t: float, params: BounceParams = BounceParams()) -> float:
    return 1 - ease_out_bounce(1 - t, params)


def ease_in_out_bounce(t: float, params: BounceParams = BounceParams()) -> float:
    if t < 0.5:
        return (1 - ease_out_bounce(1 - 2 * t, params)) / 2
    return (1 + ease_out_bounce(2 * t - 1, params)) / 2

# ---------------------------------------------------------------------------
# Elastic easing
# ---------------------------------------------------------------------------

@dataclass
class ElasticParams:
    oscillations: int = 3
    decay: float = 3.0


def elastic(t: float, params: ElasticParams = ElasticParams()) -> float:
    """Elastic easing with configurable oscillations and decay.

    Parameters
    ----------
    t:
        Time in the range [0, 1].
    params:
        :class:`ElasticParams` instance describing the number of oscillations
        and the exponential decay factor.
    """
    if t == 0 or t == 1:
        return t
    # Exponential decay multiplied by an oscillating sine component
    sin_term = math.sin(params.oscillations * 2 * math.pi * t)
    decay_term = math.exp(-params.decay * t)
    return 1 - (sin_term * decay_term)


def cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float) -> Callable[[float], float]:
    """Return a cubic bezier easing function defined by control points."""

    def func(t: float) -> float:
        # Invert x(t) using Newton-Raphson iterations
        u = t
        for _ in range(5):
            x = (
                (1 - u) ** 3 * 0
                + 3 * (1 - u) ** 2 * u * p1x
                + 3 * (1 - u) * u ** 2 * p2x
                + u ** 3
            )
            dx = (
                3 * (1 - u) ** 2 * (p1x - 0)
                + 6 * (1 - u) * u * (p2x - p1x)
                + 3 * u ** 2 * (1 - p2x)
            )
            if dx == 0:
                break
            u -= (x - t) / dx
            u = max(0.0, min(1.0, u))
        y = (
            (1 - u) ** 3 * 0
            + 3 * (1 - u) ** 2 * u * p1y
            + 3 * (1 - u) * u ** 2 * p2y
            + u ** 3
        )
        return y

    return func

# Registry of easing functions for easy selection
EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "Linear": linear,
    "EaseInQuad": ease_in_quad,
    "EaseOutQuad": ease_out_quad,
    "EaseInOutQuad": ease_in_out_quad,
    "EaseInCubic": ease_in_cubic,
    "EaseOutCubic": ease_out_cubic,
    "EaseInOutCubic": ease_in_out_cubic,
    "EaseInQuart": ease_in_quart,
    "EaseOutQuart": ease_out_quart,
    "EaseInOutQuart": ease_in_out_quart,
    "EaseInQuint": ease_in_quint,
    "EaseOutQuint": ease_out_quint,
    "EaseInOutQuint": ease_in_out_quint,
    "EaseInSine": ease_in_sine,
    "EaseOutSine": ease_out_sine,
    "EaseInOutSine": ease_in_out_sine,
    "EaseInExpo": ease_in_expo,
    "EaseOutExpo": ease_out_expo,
    "EaseInOutExpo": ease_in_out_expo,
    "EaseInCirc": ease_in_circ,
    "EaseOutCirc": ease_out_circ,
    "EaseInOutCirc": ease_in_out_circ,
    "EaseInBack": ease_in_back,
    "EaseOutBack": ease_out_back,
    "EaseInOutBack": ease_in_out_back,
    "EaseInBounce": ease_in_bounce,
    "EaseOutBounce": ease_out_bounce,
    "EaseInOutBounce": ease_in_out_bounce,
    # Elastic is handled separately due to parameters
}

