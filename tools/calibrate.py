"""Ajuste fino das faixas HSV das cores dos carrinhos.

Uso:
    python tools/calibrate.py
    python tools/calibrate.py --demo

Teclas:
    1-4   troca a cor em edicao
    s     salva a cor atual em config.local.json
    r     restaura os valores salvos da cor atual
    q     sai (Esc tambem fecha)
"""

from __future__ import annotations

import argparse
import math
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.camera import DemoSource  # noqa: E402
from src.config import ConfigStore  # noqa: E402

WINDOW = "Calibracao HSV"
INFO_HEIGHT = 104
MAX_DISPLAY_WIDTH = 880
MORPH_KERNEL = np.ones((5, 5), np.uint8)
COLOR_FALLBACK = (148, 163, 184)
ACCENT = (238, 211, 34)
WHITE = (245, 247, 250)
MUTED = (148, 163, 184)
DARK = (14, 18, 24)


def _ascii(text: Any) -> str:
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii")


def _bgr(value: Any) -> tuple[int, int, int]:
    try:
        blue, green, red = (int(max(0, min(255, int(channel)))) for channel in value)
        return blue, green, red
    except (TypeError, ValueError):
        return COLOR_FALLBACK


def _ranges_from_sliders(
    center: int,
    tolerance: int,
    s_min: int,
    v_min: int,
) -> list[list[list[int]]]:
    center = int(max(0, min(179, center)))
    tolerance = int(max(0, min(89, tolerance)))
    s_min = int(max(0, min(255, s_min)))
    v_min = int(max(0, min(255, v_min)))

    low = center - tolerance
    high = center + tolerance
    if low < 0:
        spans = [(0, min(179, high)), (180 + low, 179)]
    elif high > 179:
        spans = [(low, 179), (0, high - 180)]
    else:
        spans = [(low, high)]

    return [
        [[int(start), s_min, v_min], [int(end), 255, 255]]
        for start, end in spans
        if start <= end
    ]


def _sliders_from_ranges(
    ranges: Any,
) -> tuple[int, int, int, int]:
    parsed: list[tuple[list[int], list[int]]] = []
    if isinstance(ranges, (list, tuple)):
        for item in ranges:
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
                parsed.append(
                    (
                        [int(value) for value in low],
                        [int(value) for value in high],
                    )
                )
            except (TypeError, ValueError):
                continue

    if not parsed:
        return 0, 12, 80, 50

    low_s = max(0, min(255, parsed[0][0][1]))
    low_v = max(0, min(255, parsed[0][0][2]))

    wrapped: tuple[int, int] | None = None
    if len(parsed) >= 2:
        first, second = parsed[0], parsed[1]
        if first[0][0] <= 0 and second[1][0] >= 179:
            wrapped = (second[0][0], first[1][0] + 180)
        elif second[0][0] <= 0 and first[1][0] >= 179:
            wrapped = (first[0][0], second[1][0] + 180)

    if wrapped is not None:
        inner_low, inner_high = wrapped
        center = int(round(((inner_low + inner_high) / 2.0) % 180.0))
        tolerance = int(round((inner_high - inner_low) / 2.0))
    else:
        first = parsed[0]
        center = int(round((first[0][0] + first[1][0]) / 2.0))
        tolerance = int(round((first[1][0] - first[0][0]) / 2.0))

    return (
        max(0, min(179, center)),
        max(0, min(89, tolerance)),
        low_s,
        low_v,
    )


def _build_mask(
    hsv: np.ndarray,
    ranges: list[list[list[int]]],
) -> np.ndarray:
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
    for low, high in ranges:
        mask = cv2.bitwise_or(
            mask,
            cv2.inRange(
                hsv,
                np.array(low, dtype=np.uint8),
                np.array(high, dtype=np.uint8),
            ),
        )
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, MORPH_KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, MORPH_KERNEL)
    return mask


def _ranges_text(ranges: list[list[list[int]]]) -> str:
    parts = [f"H{low[0]}-{high[0]}" for low, high in ranges]
    return " ".join(parts) if parts else "(vazio)"


def _open_capture(index: int, backend: str, width: int, height: int):
    capture = None
    if (
        backend == "dshow"
        and sys.platform.startswith("win")
        and hasattr(cv2, "CAP_DSHOW")
    ):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)

    if capture is None or not capture.isOpened():
        if capture is not None:
            capture.release()
        capture = cv2.VideoCapture(index)

    if capture is None or not capture.isOpened():
        if capture is not None:
            capture.release()
        return None

    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, 30)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    for _ in range(5):
        capture.read()
    return capture


def _sample_hsv(frame: np.ndarray, x: int, y: int) -> tuple[int, int, int] | None:
    height, width = frame.shape[:2]
    if not (0 <= x < width and 0 <= y < height):
        return None
    radius = 4
    patch = frame[
        max(0, y - radius) : min(height, y + radius + 1),
        max(0, x - radius) : min(width, x + radius + 1),
    ]
    if patch.size == 0:
        return None
    hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
    hues = hsv[..., 0].astype(np.float64)
    angles = hues * (2.0 * math.pi / 180.0)
    mean_sin = float(np.mean(np.sin(angles)))
    mean_cos = float(np.mean(np.cos(angles)))
    if abs(mean_sin) < 1e-9 and abs(mean_cos) < 1e-9:
        center = int(np.median(hues))
    else:
        degrees = math.degrees(math.atan2(mean_sin, mean_cos)) % 360.0
        center = int(round(degrees / 2.0)) % 180
    saturation = int(np.median(hsv[..., 1]))
    value = int(np.median(hsv[..., 2]))
    return center, saturation, value


def _draw_panel(
    frame: np.ndarray,
    mask: np.ndarray,
    color: tuple[int, int, int],
    key: str,
    label: str,
    index: int,
    total: int,
    center: int,
    tolerance: int,
    s_min: int,
    v_min: int,
    ranges: list[list[list[int]]],
    fps: float,
    message: str,
) -> np.ndarray:
    height, width = frame.shape[:2]
    display_width = min(MAX_DISPLAY_WIDTH, width)
    display_height = max(1, int(round(display_width * height / width)))
    display = cv2.resize(
        frame,
        (display_width, display_height),
        interpolation=cv2.INTER_AREA,
    )
    small_mask = cv2.resize(
        mask,
        (display_width, display_height),
        interpolation=cv2.INTER_NEAREST,
    )

    overlay = display.copy()
    overlay[small_mask > 0] = color
    display = cv2.addWeighted(display, 0.55, overlay, 0.45, 0)

    contours, _ = cv2.findContours(
        small_mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 30:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(display, (x, y), (x + w, y + h), WHITE, 1, cv2.LINE_AA)
        cv2.putText(
            display,
            f"{int(area)} px",
            (x, max(12, y - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            WHITE,
            1,
            cv2.LINE_AA,
        )

    inset_width = max(40, int(display_width * 0.23))
    inset_width = min(inset_width, max(40, display_width - 24))
    inset_height = max(1, int(round(inset_width * height / width)))
    inset_height = min(inset_height, max(1, display_height - 24))
    inset = cv2.cvtColor(
        cv2.resize(mask, (inset_width, inset_height), interpolation=cv2.INTER_NEAREST),
        cv2.COLOR_GRAY2BGR,
    )
    inset_x = display_width - inset_width - 12
    inset_y = 12
    display[
        inset_y : inset_y + inset_height,
        inset_x : inset_x + inset_width,
    ] = inset
    cv2.rectangle(
        display,
        (inset_x - 1, inset_y - 1),
        (inset_x + inset_width, inset_y + inset_height),
        MUTED,
        1,
    )
    cv2.putText(
        display,
        "MASCARA",
        (inset_x + 6, inset_y + 16),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        ACCENT,
        1,
        cv2.LINE_AA,
    )

    info = np.empty((INFO_HEIGHT, display_width, 3), dtype=np.uint8)
    info[:] = DARK
    cv2.line(info, (0, 0), (display_width, 0), (48, 56, 68), 1, cv2.LINE_AA)

    title = f"Cor {index + 1}/{total}: {_ascii(label)}  ({_ascii(key)})"
    cv2.putText(
        info,
        title,
        (16, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.56,
        ACCENT,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        info,
        f"{fps:4.1f} FPS",
        (display_width - 92, 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        MUTED,
        1,
        cv2.LINE_AA,
    )

    values = (
        f"H centro {center:3d}  +/- {tolerance:2d}   "
        f"S min {s_min:3d}   V min {v_min:3d}"
    )
    cv2.putText(
        info,
        values,
        (16, 50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        WHITE,
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        info,
        f"Faixas: {_ranges_text(ranges)}",
        (16, 74),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        MUTED,
        1,
        cv2.LINE_AA,
    )
    hint = "1-4 cor | clique amostra | s salvar | r resetar | q sair"
    cv2.putText(
        info,
        hint,
        (16, 96),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (96, 112, 132),
        1,
        cv2.LINE_AA,
    )

    panel = np.vstack([display, info])

    if message:
        (text_width, text_height), baseline = cv2.getTextSize(
            message,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            1,
        )
        box_top = display_height - 40
        cv2.rectangle(
            panel,
            (12, box_top),
            (min(display_width - 12, 12 + text_width + 20), box_top + text_height + baseline + 14),
            DARK,
            -1,
            cv2.LINE_AA,
        )
        cv2.putText(
            panel,
            message,
            (22, box_top + text_height + 7),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            WHITE,
            1,
            cv2.LINE_AA,
        )

    return panel


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calibra as faixas HSV das cores dos carrinhos.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Usa a pista sintetica em vez da webcam.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        help="Sobrescreve o indice da webcam.",
    )
    args = parser.parse_args()

    store = ConfigStore()
    config = store.snapshot()
    camera = config.get("camera", {})
    process_width = int(camera.get("process_width", 960))
    process_height = int(camera.get("process_height", 540))
    capture_width = int(camera.get("width", 1280))
    capture_height = int(camera.get("height", 720))
    camera_index = (
        args.camera_index
        if args.camera_index is not None
        else int(camera.get("index", 0))
    )

    colors: dict[str, Any] = config.get("colors", {})
    keys = list(colors)
    if not keys:
        print("Nenhuma cor configurada em config.example.json.")
        return 1
    if len(keys) > 9:
        keys = keys[:9]

    source = None
    capture = None
    if args.demo:
        source = DemoSource(process_width, process_height)
    else:
        capture = _open_capture(
            camera_index,
            str(camera.get("backend", "dshow")).lower(),
            capture_width,
            capture_height,
        )
        if capture is None:
            print(
                f"Nao foi possivel abrir a webcam {camera_index}. "
                "Verifique a conexao ou use --demo."
            )
            return 1

    selected = 0
    base_color = colors[keys[selected]]
    label = base_color.get("label") or keys[selected].replace("_", " ").title()
    center, tolerance, s_min, v_min = _sliders_from_ranges(
        base_color.get("hsv_ranges"),
    )

    state: dict[str, Any] = {
        "frame": None,
        "message": "",
        "message_until": 0.0,
        "display_width": MAX_DISPLAY_WIDTH,
        "display_height": 495,
    }

    def show_message(text: str) -> None:
        state["message"] = _ascii(text)
        state["message_until"] = time.monotonic() + 3.0

    def apply_color(index: int) -> None:
        nonlocal selected, base_color, label, center, tolerance, s_min, v_min
        selected = index
        base_color = colors[keys[selected]]
        label = base_color.get("label") or keys[selected].replace("_", " ").title()
        center, tolerance, s_min, v_min = _sliders_from_ranges(
            base_color.get("hsv_ranges"),
        )
        cv2.setTrackbarPos("H centro", WINDOW, center)
        cv2.setTrackbarPos("H tolerancia", WINDOW, tolerance)
        cv2.setTrackbarPos("S minimo", WINDOW, s_min)
        cv2.setTrackbarPos("V minimo", WINDOW, v_min)

    def on_mouse(event: int, x: int, y: int, _flags: int, _param: Any) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        frame = state["frame"]
        if frame is None:
            return
        display_width = int(state["display_width"])
        display_height = int(state["display_height"])
        if not (0 <= x < display_width and 0 <= y < display_height):
            return
        frame_height, frame_width = frame.shape[:2]
        frame_x = int(x * frame_width / display_width)
        frame_y = int(y * frame_height / display_height)
        sample = _sample_hsv(frame, frame_x, frame_y)
        if sample is None:
            return
        hue, saturation, value = sample
        cv2.setTrackbarPos("H centro", WINDOW, hue)
        cv2.setTrackbarPos("H tolerancia", WINDOW, 12)
        cv2.setTrackbarPos("S minimo", WINDOW, max(20, int(saturation * 0.55)))
        cv2.setTrackbarPos("V minimo", WINDOW, max(20, int(value * 0.45)))
        show_message(
            f"Amostra H={hue} S={saturation} V={value} em ({frame_x}, {frame_y})"
        )

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    cv2.createTrackbar("H centro", WINDOW, center, 179, lambda _value: None)
    cv2.createTrackbar("H tolerancia", WINDOW, tolerance, 89, lambda _value: None)
    cv2.createTrackbar("S minimo", WINDOW, s_min, 255, lambda _value: None)
    cv2.createTrackbar("V minimo", WINDOW, v_min, 255, lambda _value: None)
    cv2.setMouseCallback(WINDOW, on_mouse)

    print("Calibracao aberta. Teclas: 1-4 cor, s salvar, r resetar, q sair.")

    fps = 0.0
    last_time = time.monotonic()
    failures = 0
    result = 0

    while True:
        started = time.monotonic()

        if args.demo:
            frame = source.read()
        else:
            ok, frame = capture.read()
            if not ok or frame is None:
                failures += 1
                if failures > 30:
                    print("Sinal da webcam perdido.")
                    result = 1
                    break
                cv2.waitKey(30)
                continue
            failures = 0
            frame = cv2.resize(
                frame,
                (process_width, process_height),
                interpolation=cv2.INTER_AREA,
            )

        if frame is None:
            continue

        state["frame"] = frame
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        center = cv2.getTrackbarPos("H centro", WINDOW)
        tolerance = cv2.getTrackbarPos("H tolerancia", WINDOW)
        s_min = cv2.getTrackbarPos("S minimo", WINDOW)
        v_min = cv2.getTrackbarPos("V minimo", WINDOW)
        ranges = _ranges_from_sliders(center, tolerance, s_min, v_min)
        mask = _build_mask(hsv, ranges)

        frame_height, frame_width = frame.shape[:2]
        display_width = min(MAX_DISPLAY_WIDTH, frame_width)
        display_height = max(1, int(round(display_width * frame_height / frame_width)))
        state["display_width"] = display_width
        state["display_height"] = display_height

        now = time.monotonic()
        delta = now - last_time
        last_time = now
        if delta > 0:
            instant = 1.0 / delta
            fps = instant if fps <= 0 else (0.85 * fps + 0.15 * instant)

        if state["message"] and now > state["message_until"]:
            state["message"] = ""

        panel = _draw_panel(
            frame,
            mask,
            _bgr(base_color.get("bgr")),
            keys[selected],
            label,
            selected,
            len(keys),
            center,
            tolerance,
            s_min,
            v_min,
            ranges,
            fps,
            state["message"],
        )
        cv2.imshow(WINDOW, panel)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        if ord("1") <= key <= ord("9"):
            index = key - ord("1")
            if index < len(keys):
                apply_color(index)
                show_message(f"Editando {label}")
        elif key == ord("s"):
            updated = dict(base_color)
            updated["hsv_ranges"] = ranges
            try:
                store.save_section("colors", {keys[selected]: updated})
            except OSError as exc:
                print(f"Falha ao salvar: {exc}")
                show_message("Erro ao salvar config.local.json")
            else:
                colors[keys[selected]] = updated
                base_color = updated
                show_message("Salvo em config.local.json")
                print(
                    f"{label}: salvo H {center} +/- {tolerance}, "
                    f"S>={s_min}, V>={v_min}."
                )
        elif key == ord("r"):
            fresh = store.snapshot().get("colors", {}).get(keys[selected])
            if isinstance(fresh, dict):
                colors[keys[selected]] = fresh
                base_color = fresh
                apply_color(selected)
                show_message("Valores salvos restaurados")

        elapsed = time.monotonic() - started
        remaining = (1.0 / 30.0) - elapsed
        if remaining > 0 and args.demo:
            time.sleep(remaining)

    if capture is not None:
        capture.release()
    cv2.destroyAllWindows()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
