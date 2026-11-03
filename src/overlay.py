"""Desenho de sobreposicoes da pista e de frames de espera."""

from __future__ import annotations

import math
import textwrap
import unicodedata
from typing import Any

import cv2
import numpy as np

ACCENT = (238, 211, 34)
WHITE = (245, 247, 250)
DARK = (10, 13, 18)
MUTED = (148, 163, 184)


def _ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii")


def draw_overlay(
    frame: np.ndarray,
    config: dict[str, Any],
    status: dict[str, Any],
    detections: list[dict[str, Any]] | None = None,
    race: dict[str, Any] | None = None,
) -> np.ndarray:
    height, width = frame.shape[:2]
    _draw_roi(frame, config.get("roi", {}), width, height)
    line = config.get("finish_line", {})
    _draw_finish_line(frame, line.get("p1"), line.get("p2"), width, height)
    if detections:
        _draw_detections(frame, config, detections, race, width, height)
    _draw_race_hud(frame, race, width, height)
    _draw_hud(frame, status)
    return frame


def _draw_roi(
    frame: np.ndarray,
    roi: dict[str, Any],
    width: int,
    height: int,
) -> None:
    try:
        x = int(float(roi.get("x", 0.0)) * width)
        y = int(float(roi.get("y", 0.0)) * height)
        w = int(float(roi.get("w", 1.0)) * width)
        h = int(float(roi.get("h", 1.0)) * height)
    except (TypeError, ValueError):
        return

    if x <= 0 and y <= 0 and w >= width and h >= height:
        return

    x2 = min(width - 1, x + w)
    y2 = min(height - 1, y + h)
    length = max(10, int(min(width, height) * 0.035))
    thickness = 2

    corners = (
        ((x, y), (x + length, y), (x, y + length)),
        ((x2, y), (x2 - length, y), (x2, y + length)),
        ((x, y2), (x + length, y2), (x, y2 - length)),
        ((x2, y2), (x2 - length, y2), (x2, y2 - length)),
    )
    for corner, horizontal_end, vertical_end in corners:
        cv2.line(frame, corner, horizontal_end, ACCENT, thickness, cv2.LINE_AA)
        cv2.line(frame, corner, vertical_end, ACCENT, thickness, cv2.LINE_AA)


def _draw_finish_line(
    frame: np.ndarray,
    p1: Any,
    p2: Any,
    width: int,
    height: int,
) -> None:
    if not isinstance(p1, (list, tuple)) or not isinstance(p2, (list, tuple)):
        return
    try:
        ax = float(p1[0]) * width
        ay = float(p1[1]) * height
        bx = float(p2[0]) * width
        by = float(p2[1]) * height
    except (TypeError, ValueError, IndexError):
        return

    dx = bx - ax
    dy = by - ay
    length = math.hypot(dx, dy)
    if length < 10:
        return

    ux = dx / length
    uy = dy / length
    nx = -uy
    ny = ux
    thickness = max(10, int(min(width, height) * 0.028))
    row_thickness = max(4, thickness // 2)
    gap = max(1, thickness // 8)

    cv2.line(
        frame,
        (int(ax), int(ay)),
        (int(bx), int(by)),
        (6, 8, 12),
        thickness + 6,
        cv2.LINE_AA,
    )

    cell = max(10, int(min(width, height) * 0.024))
    steps = max(1, int(length // cell))
    for row in (0, 1):
        offset = (row - 0.5) * (row_thickness + gap)
        for index in range(steps + 1):
            start = index * cell
            end = min(length, (index + 1) * cell)
            color = WHITE if (index + row) % 2 == 0 else (30, 34, 40)
            cv2.line(
                frame,
                (
                    int(ax + ux * start + nx * offset),
                    int(ay + uy * start + ny * offset),
                ),
                (
                    int(ax + ux * end + nx * offset),
                    int(ay + uy * end + ny * offset),
                ),
                color,
                row_thickness,
                cv2.LINE_8,
            )

    cap_radius = max(3, row_thickness // 2)
    cv2.circle(frame, (int(ax), int(ay)), cap_radius, WHITE, -1, cv2.LINE_AA)
    cv2.circle(frame, (int(bx), int(by)), cap_radius, WHITE, -1, cv2.LINE_AA)

    label = "CHEGADA"
    text_scale = max(0.42, min(width, height) * 0.0009)
    text_thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        text_scale,
        text_thickness,
    )
    middle_x = (ax + bx) / 2
    middle_y = (ay + by) / 2
    offset = thickness / 2 + text_h + 14
    label_x = int(middle_x - nx * offset) - text_w // 2
    label_y = int(middle_y - ny * offset)
    padding = 6
    cv2.rectangle(
        frame,
        (label_x - padding, label_y - text_h - padding),
        (label_x + text_w + padding, label_y + baseline + padding),
        DARK,
        -1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        label,
        (label_x, label_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        text_scale,
        ACCENT,
        text_thickness,
        cv2.LINE_AA,
    )


def _detection_color(
    config: dict[str, Any],
    color_key: str,
) -> tuple[int, int, int]:
    colors = config.get("colors")
    if not isinstance(colors, dict):
        return MUTED
    entry = colors.get(color_key)
    if not isinstance(entry, dict):
        return MUTED
    try:
        blue, green, red = (
            int(max(0, min(255, int(channel))))
            for channel in entry.get("bgr", MUTED)
        )
    except (TypeError, ValueError):
        return MUTED
    return blue, green, red


def _draw_detections(
    frame: np.ndarray,
    config: dict[str, Any],
    detections: list[dict[str, Any]],
    race: dict[str, Any] | None,
    width: int,
    height: int,
) -> None:
    cars: dict[str, dict[str, Any]] = {}
    if isinstance(race, dict):
        for car in race.get("cars", []):
            if isinstance(car, dict) and car.get("color"):
                cars[str(car["color"])] = car

    scale = max(0.38, min(width, height) * 0.00085)
    thickness = 1
    for detection in detections:
        if not isinstance(detection, dict):
            continue
        bbox = detection.get("bbox")
        if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
            continue
        try:
            x, y, w, h = (int(value) for value in bbox)
        except (TypeError, ValueError):
            continue
        if w <= 0 or h <= 0:
            continue

        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        w = max(1, min(width - x, w))
        h = max(1, min(height - y, h))
        color_key = str(detection.get("color", ""))
        color = _detection_color(config, color_key)
        car = cars.get(color_key)
        label = _ascii(detection.get("label") or color_key)
        if car and car.get("status") == "finished":
            position = car.get("position")
            if position:
                label = f"{label} {position}o"

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            color,
            2,
            cv2.LINE_AA,
        )
        center = (
            x + w // 2,
            y + h // 2,
        )
        cv2.circle(frame, center, 3, color, -1, cv2.LINE_AA)

        (text_w, text_h), baseline = cv2.getTextSize(
            label,
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            thickness,
        )
        padding = 5
        label_x = x
        label_y = y - text_h - baseline - padding
        if label_y < 4:
            label_y = min(height - baseline - padding, y + h + 4)
        label_x = max(4, min(width - text_w - padding - 4, label_x))
        cv2.rectangle(
            frame,
            (label_x - padding, label_y - text_h - 2),
            (label_x + text_w + padding, label_y + baseline + 2),
            DARK,
            -1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            label,
            (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )


def _draw_race_hud(
    frame: np.ndarray,
    race: dict[str, Any] | None,
    width: int,
    height: int,
) -> None:
    if not isinstance(race, dict):
        return
    status = race.get("status")
    if status not in {"armed", "running", "finished"}:
        return

    elapsed = int(race.get("elapsed_ms") or 0)
    if status == "armed":
        label = "LARGADA"
        color = ACCENT
    elif status == "running":
        label = f"CORRIDA {elapsed / 1000.0:.2f}s"
        color = ACCENT
    else:
        label = f"FINALIZADA {elapsed / 1000.0:.2f}s"
        color = (153, 211, 52)

    scale = max(0.42, min(width, height) * 0.00085)
    thickness = 1
    (text_w, text_h), baseline = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness,
    )
    padding = 8
    left = (width - text_w) // 2 - padding
    top = 14
    cv2.rectangle(
        frame,
        (left, top),
        (left + text_w + padding * 2, top + text_h + baseline + padding),
        DARK,
        -1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        label,
        (left + padding, top + text_h + 3),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def _draw_hud(frame: np.ndarray, status: dict[str, Any]) -> None:
    height, width = frame.shape[:2]
    fps = float(status.get("fps", 0.0))
    source = "DEMO" if status.get("source") == "demo" else "WEBCAM"
    label = f"{fps:4.1f} FPS"
    scale = max(0.38, min(width, height) * 0.0008)
    thickness = 1

    (text_w, text_h), baseline = cv2.getTextSize(
        label,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness,
    )
    left, top = 14, 14
    cv2.rectangle(
        frame,
        (left, top),
        (left + text_w + 26, top + text_h + baseline + 12),
        DARK,
        -1,
        cv2.LINE_AA,
    )
    cv2.circle(
        frame,
        (left + 11, top + text_h // 2 + 6),
        3,
        (52, 211, 153),
        -1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        label,
        (left + 20, top + text_h + 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        WHITE,
        thickness,
        cv2.LINE_AA,
    )

    (source_w, source_h), source_baseline = cv2.getTextSize(
        source,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness,
    )
    source_x = width - source_w - 26
    cv2.rectangle(
        frame,
        (source_x - 8, top),
        (width - 12, top + source_h + source_baseline + 12),
        DARK,
        -1,
        cv2.LINE_AA,
    )
    source_color = ACCENT if source == "DEMO" else MUTED
    cv2.putText(
        frame,
        source,
        (source_x, top + source_h + 4),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        source_color,
        thickness,
        cv2.LINE_AA,
    )


def make_offline_frame(
    status: dict[str, Any],
    size: tuple[int, int],
) -> np.ndarray:
    width, height = size
    frame = np.empty((height, width, 3), dtype=np.uint8)
    frame[:] = (9, 12, 17)

    for x in range(0, width, 48):
        cv2.line(frame, (x, 0), (x, height), (22, 27, 34), 1)
    for y in range(0, height, 48):
        cv2.line(frame, (0, y), (width, y), (22, 27, 34), 1)

    waiting = status.get("status") == "starting"
    title = "Iniciando a camera" if waiting else "Webcam indisponivel"
    detail = status.get("error")
    if not detail:
        detail = (
            "Aguardando o primeiro frame..."
            if waiting
            else "Verifique a conexao e o indice da camera em config.local.json."
        )
    hint = "Dica: rode com --demo para visualizar a interface sem webcam."

    title_scale = max(0.6, min(width, height) * 0.0014)
    body_scale = max(0.42, min(width, height) * 0.0009)
    title_y = height // 2 - 28

    accent_half = max(28, int(width * 0.035))
    cv2.line(
        frame,
        (width // 2 - accent_half, title_y - int(34 * title_scale)),
        (width // 2 + accent_half, title_y - int(34 * title_scale)),
        ACCENT,
        3,
        cv2.LINE_AA,
    )

    title_y = _center_text(
        frame,
        _ascii(title),
        title_y,
        title_scale,
        WHITE,
        2,
    )

    for line in textwrap.wrap(_ascii(detail), width=56) or [""]:
        title_y = _center_text(
            frame,
            line,
            title_y + int(10 * body_scale + 6),
            body_scale,
            MUTED,
        )

    _center_text(
        frame,
        _ascii(hint),
        title_y + int(18 * body_scale + 12),
        max(0.36, body_scale * 0.86),
        (90, 104, 120),
    )
    return frame


def _center_text(
    frame: np.ndarray,
    text: str,
    baseline_y: int,
    scale: float,
    color: tuple[int, int, int],
    thickness: int = 1,
) -> int:
    width = frame.shape[1]
    (text_w, text_h), baseline = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness,
    )
    x = max(12, (width - text_w) // 2)
    cv2.putText(
        frame,
        text,
        (x, baseline_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )
    return baseline_y + text_h + baseline
