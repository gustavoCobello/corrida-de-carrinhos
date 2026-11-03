"""Deteccao dos carrinhos por faixas de cor em HSV."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


@dataclass(frozen=True)
class Detection:
    color: str
    label: str
    bbox: tuple[int, int, int, int]
    cx: float
    cy: float
    nx: float
    ny: float
    area: float
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "color": self.color,
            "label": self.label,
            "bbox": list(self.bbox),
            "cx": round(self.cx, 1),
            "cy": round(self.cy, 1),
            "nx": round(self.nx, 5),
            "ny": round(self.ny, 5),
            "area": round(self.area, 1),
            "confidence": round(self.confidence, 3),
        }


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _parse_ranges(value: Any) -> list[tuple[np.ndarray, np.ndarray]]:
    ranges: list[tuple[np.ndarray, np.ndarray]] = []
    if not isinstance(value, dict):
        return ranges
    raw_ranges = value.get("hsv_ranges")
    if not isinstance(raw_ranges, (list, tuple)):
        return ranges

    for item in raw_ranges:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        low, high = item
        if (
            not isinstance(low, (list, tuple))
            or not isinstance(high, (list, tuple))
            or len(low) < 3
            or len(high) < 3
        ):
            continue
        try:
            lower = [int(_clamp(float(channel), 0, 255)) for channel in low[:3]]
            upper = [int(_clamp(float(channel), 0, 255)) for channel in high[:3]]
        except (TypeError, ValueError):
            continue
        if lower[0] > upper[0]:
            continue
        ranges.append(
            (
                np.array(lower, dtype=np.uint8),
                np.array(upper, dtype=np.uint8),
            )
        )
    return ranges


def _roi_pixels(
    roi: dict[str, Any],
    width: int,
    height: int,
) -> tuple[int, int, int, int]:
    def number(key: str, fallback: float) -> float:
        try:
            return float(roi.get(key, fallback))
        except (TypeError, ValueError):
            return fallback

    x = _clamp(number("x", 0.0), 0.0, 1.0)
    y = _clamp(number("y", 0.0), 0.0, 1.0)
    w = _clamp(number("w", 1.0), 0.001, 1.0 - x)
    h = _clamp(number("h", 1.0), 0.001, 1.0 - y)

    x1 = int(round(x * width))
    y1 = int(round(y * height))
    x2 = int(round((x + w) * width))
    y2 = int(round((y + h) * height))
    x1 = max(0, min(width - 1, x1))
    y1 = max(0, min(height - 1, y1))
    x2 = max(x1 + 1, min(width, x2))
    y2 = max(y1 + 1, min(height, y2))
    return x1, y1, x2 - x1, y2 - y1


class ColorDetector:
    """Encontra o maior blob de cada cor configurada dentro da ROI."""

    def __init__(self, config: dict[str, Any]) -> None:
        colors = config.get("colors")
        self._colors: dict[str, Any] = colors if isinstance(colors, dict) else {}
        self._roi = config.get("roi") if isinstance(config.get("roi"), dict) else {}
        race = config.get("race")
        race = race if isinstance(race, dict) else {}
        try:
            self._min_area = max(1, int(race.get("min_area_px", 400)))
        except (TypeError, ValueError):
            self._min_area = 400
        self._ranges = {
            key: _parse_ranges(value)
            for key, value in self._colors.items()
            if isinstance(value, dict)
        }
        self._kernel = np.ones((5, 5), dtype=np.uint8)

    def detect(self, frame: np.ndarray) -> list[Detection]:
        if frame is None or frame.size == 0:
            return []

        height, width = frame.shape[:2]
        x_offset, y_offset, roi_width, roi_height = _roi_pixels(
            self._roi,
            width,
            height,
        )
        crop = frame[
            y_offset : y_offset + roi_height,
            x_offset : x_offset + roi_width,
        ]
        if crop.size == 0:
            return []

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        detections: list[Detection] = []

        for key, color in self._colors.items():
            ranges = self._ranges.get(key, [])
            if not ranges:
                continue

            mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
            for lower, upper in ranges:
                mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel)

            contours, _ = cv2.findContours(
                mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE,
            )
            if not contours:
                continue

            largest = max(contours, key=cv2.contourArea)
            area = float(cv2.contourArea(largest))
            if area < self._min_area:
                continue

            bx, by, bw, bh = cv2.boundingRect(largest)
            if bw <= 0 or bh <= 0:
                continue

            absolute_x = x_offset + bx
            absolute_y = y_offset + by
            center_x = absolute_x + bw / 2.0
            center_y = absolute_y + bh / 2.0
            label = color.get("label") or key.replace("_", " ").title()
            detections.append(
                Detection(
                    color=key,
                    label=str(label),
                    bbox=(absolute_x, absolute_y, bw, bh),
                    cx=center_x,
                    cy=center_y,
                    nx=center_x / width,
                    ny=center_y / height,
                    area=area,
                    confidence=min(1.0, area / max(1.0, float(bw * bh))),
                )
            )

        return detections
