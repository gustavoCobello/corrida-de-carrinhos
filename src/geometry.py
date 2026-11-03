"""Geometria da linha de chegada e deteccao de cruzamento."""

from __future__ import annotations

import math
from typing import Sequence

Point = tuple[float, float]

EPSILON = 1e-9


def _point(value: Sequence[float] | None) -> Point | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        return float(value[0]), float(value[1])
    except (TypeError, ValueError):
        return None


def line_length(p1: Sequence[float], p2: Sequence[float]) -> float:
    first = _point(p1)
    second = _point(p2)
    if first is None or second is None:
        return 0.0
    return math.hypot(second[0] - first[0], second[1] - first[1])


def side(p1: Sequence[float], p2: Sequence[float], point: Sequence[float]) -> float:
    """Produto vetorial que indica de que lado da reta o ponto esta."""
    first = _point(p1)
    second = _point(p2)
    target = _point(point)
    if first is None or second is None or target is None:
        return 0.0
    return (second[0] - first[0]) * (target[1] - first[1]) - (
        second[1] - first[1]
    ) * (target[0] - first[0])


def side_sign(value: float) -> int:
    if value > EPSILON:
        return 1
    if value < -EPSILON:
        return -1
    return 0


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def crossing_between(
    line_p1: Sequence[float],
    line_p2: Sequence[float],
    previous: Sequence[float],
    current: Sequence[float],
    margin: float = 0.01,
) -> tuple[float, float] | None:
    """Retorna (t, u) se o movimento cruzou o segmento da linha.

    t e a posicao no segmento da linha (0 a 1) e u a posicao no movimento
    (0 a 1). O cruzamento so vale se estiver dentro do segmento, com uma
    margem de tolerancia nas pontas.
    """
    first = _point(line_p1)
    second = _point(line_p2)
    start = _point(previous)
    end = _point(current)
    if first is None or second is None or start is None or end is None:
        return None

    line = (second[0] - first[0], second[1] - first[1])
    if math.hypot(line[0], line[1]) < EPSILON:
        return None

    start_side = side(first, second, start)
    end_side = side(first, second, end)
    if start_side * end_side >= 0:
        return None

    movement = (end[0] - start[0], end[1] - start[1])
    denominator = _cross(line, movement)
    if abs(denominator) < EPSILON:
        return None

    offset = (start[0] - first[0], start[1] - first[1])
    t = _cross(offset, movement) / denominator
    u = _cross(offset, line) / denominator
    if not (margin <= t <= 1.0 - margin):
        return None
    if not (-EPSILON <= u <= 1.0 + EPSILON):
        return None
    return t, u


def point_within_segment(
    p1: Sequence[float],
    p2: Sequence[float],
    point: Sequence[float],
    margin: float = 0.0,
) -> bool:
    """Verifica se a projecao do ponto cai dentro do segmento."""
    first = _point(p1)
    second = _point(p2)
    target = _point(point)
    if first is None or second is None or target is None:
        return False
    dx = second[0] - first[0]
    dy = second[1] - first[1]
    length_squared = dx * dx + dy * dy
    if length_squared < EPSILON:
        return False
    t = ((target[0] - first[0]) * dx + (target[1] - first[1]) * dy) / length_squared
    return margin <= t <= 1.0 - margin
