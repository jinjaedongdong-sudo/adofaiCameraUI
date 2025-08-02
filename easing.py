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

# Registry of easing functions for easy selection
EASING_FUNCTIONS: dict[str, Callable[[float], float]] = {
    "Linear": linear,
    "EaseInQuad": ease_in_quad,
    "EaseOutQuad": ease_out_quad,
    "EaseInOutQuad": ease_in_out_quad,
    # Elastic is handled separately due to parameters
}

