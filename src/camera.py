"""Captura de video em thread separada, com modo de demonstracao."""

from __future__ import annotations

import logging
import math
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable

import cv2
import numpy as np

LOGGER = logging.getLogger(__name__)

OFFLINE_MESSAGE = (
    "Nao foi possivel abrir a webcam. Verifique a conexao e o indice configurado."
)


class DemoSource:
    """Gera uma pista sintetica para validar a interface sem webcam."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._started = time.monotonic()
        self._cars = [
            {"x": 0.22, "speed": 0.145, "offset": 0.04, "color": (53, 57, 229)},
            {"x": 0.41, "speed": 0.178, "offset": 0.30, "color": (71, 160, 67)},
            {"x": 0.60, "speed": 0.160, "offset": 0.61, "color": (229, 136, 30)},
            {"x": 0.79, "speed": 0.198, "offset": 0.87, "color": (122, 64, 236)},
        ]

    def read(self) -> np.ndarray:
        elapsed = time.monotonic() - self._started
        frame = np.empty((self.height, self.width, 3), dtype=np.uint8)
        frame[:] = (36, 40, 46)

        for fraction in (0.265, 0.5, 0.735):
            x = int(fraction * self.width)
            for y in range(-40, self.height + 40, 56):
                cv2.line(frame, (x, y), (x, y + 28), (58, 64, 72), 2, cv2.LINE_AA)

        cv2.line(frame, (8, 0), (8, self.height), (52, 58, 66), 3)
        cv2.line(
            frame,
            (self.width - 8, 0),
            (self.width - 8, self.height),
            (52, 58, 66),
            3,
        )

        for car in self._cars:
            progress = (car["offset"] + elapsed * car["speed"]) % 1.28 - 0.14
            center_y = int(progress * self.height)
            wobble = math.sin(elapsed * 1.6 + car["x"] * 9.0) * 0.008
            center_x = int((car["x"] + wobble) * self.width)
            _draw_demo_car(frame, center_x, center_y, car["color"])

        return frame


def _draw_demo_car(
    frame: np.ndarray,
    center_x: int,
    center_y: int,
    color: tuple[int, int, int],
) -> None:
    height, width = frame.shape[:2]
    car_w = max(34, int(width * 0.052))
    car_l = max(58, int(height * 0.155))

    left = center_x - car_w // 2
    right = center_x + car_w // 2
    top = center_y - car_l // 2
    bottom = center_y + car_l // 2

    cv2.ellipse(
        frame,
        (center_x + 5, center_y + 7),
        (car_w // 2 + 2, car_l // 2 + 2),
        0,
        0,
        360,
        (18, 20, 24),
        -1,
        cv2.LINE_AA,
    )

    wheel_w = max(4, int(car_w * 0.14))
    wheel_h = max(8, int(car_l * 0.16))
    for wheel_y in (top + int(car_l * 0.18), bottom - int(car_l * 0.34)):
        cv2.rectangle(
            frame,
            (left - wheel_w // 2, wheel_y),
            (left + wheel_w // 2, wheel_y + wheel_h),
            (12, 14, 17),
            -1,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            frame,
            (right - wheel_w // 2, wheel_y),
            (right + wheel_w // 2, wheel_y + wheel_h),
            (12, 14, 17),
            -1,
            cv2.LINE_AA,
        )

    cv2.rectangle(
        frame,
        (left, top),
        (right, bottom),
        (20, 22, 26),
        -1,
        cv2.LINE_AA,
    )
    cv2.rectangle(
        frame,
        (left + 2, top + 2),
        (right - 2, bottom - 2),
        color,
        -1,
        cv2.LINE_AA,
    )

    light = tuple(min(255, int(channel * 1.25 + 18)) for channel in color)
    cabin_left = left + int(car_w * 0.16)
    cabin_right = right - int(car_w * 0.16)
    cabin_top = top + int(car_l * 0.22)
    cabin_bottom = top + int(car_l * 0.62)
    cv2.rectangle(
        frame,
        (cabin_left, cabin_top),
        (cabin_right, cabin_bottom),
        light,
        -1,
        cv2.LINE_AA,
    )

    windshield_top = top + int(car_l * 0.62)
    windshield_bottom = top + int(car_l * 0.78)
    cv2.rectangle(
        frame,
        (cabin_left, windshield_top),
        (cabin_right, windshield_bottom),
        (18, 24, 30),
        -1,
        cv2.LINE_AA,
    )

    rear_top = top + int(car_l * 0.12)
    rear_bottom = top + int(car_l * 0.20)
    cv2.rectangle(
        frame,
        (cabin_left, rear_top),
        (cabin_right, rear_bottom),
        (18, 24, 30),
        -1,
        cv2.LINE_AA,
    )

    light_w = max(4, int(car_w * 0.18))
    light_h = max(2, int(car_l * 0.02))
    cv2.rectangle(
        frame,
        (left + int(car_w * 0.12), bottom - 6),
        (left + int(car_w * 0.12) + light_w, bottom - 6 + light_h),
        (240, 240, 220),
        -1,
        cv2.LINE_AA,
    )
    cv2.rectangle(
        frame,
        (right - int(car_w * 0.12) - light_w, bottom - 6),
        (right - int(car_w * 0.12), bottom - 6 + light_h),
        (240, 240, 220),
        -1,
        cv2.LINE_AA,
    )


class CameraStream:
    """Uma unica thread mantem o ultimo frame e publica para os clientes."""

    def __init__(self, config: dict[str, Any], demo: bool = False) -> None:
        camera = config.get("camera", {})
        self.index = int(camera.get("index", 0))
        self.backend = str(camera.get("backend", "dshow")).lower()
        self.capture_width = int(camera.get("width", 1280))
        self.capture_height = int(camera.get("height", 720))
        self.process_width = int(camera.get("process_width", 960))
        self.process_height = int(camera.get("process_height", 540))
        self.demo = bool(demo or camera.get("demo", False))

        self._condition = threading.Condition()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._running = False
        self._frame: np.ndarray | None = None
        self._frame_id = 0
        self._frames = 0
        self._fps = 0.0
        self._last_frame_ts: float | None = None
        self._last_frame_at: float | None = None
        self._status = "starting"
        self._error: str | None = None
        self._capture_size = (self.capture_width, self.capture_height)
        self._frame_callback: Callable[[np.ndarray, float], None] | None = None
        self._callback_error_logged = False

    def set_frame_callback(
        self,
        callback: Callable[[np.ndarray, float], None] | None,
    ) -> None:
        self._frame_callback = callback

    def start(self) -> None:
        with self._condition:
            if self._running:
                return
            self._running = True
            self._status = "starting"
            self._error = None
            self._stop_event.clear()
            target = self._run_demo if self.demo else self._run_camera
            self._thread = threading.Thread(
                target=target,
                name="camera-stream",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        with self._condition:
            self._running = False
            self._condition.notify_all()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

    def is_running(self) -> bool:
        with self._condition:
            return self._running

    def status(self) -> dict[str, Any]:
        with self._condition:
            frame = self._frame
            width = int(frame.shape[1]) if frame is not None else self.process_width
            height = int(frame.shape[0]) if frame is not None else self.process_height
            last_frame_at = None
            if self._last_frame_at is not None:
                last_frame_at = (
                    datetime.fromtimestamp(self._last_frame_at)
                    .astimezone()
                    .isoformat(timespec="seconds")
                )
            return {
                "status": self._status,
                "source": "demo" if self.demo else "webcam",
                "index": self.index,
                "running": self._running,
                "fps": round(float(self._fps), 1),
                "frames": self._frames,
                "width": width,
                "height": height,
                "capture_width": int(self._capture_size[0]),
                "capture_height": int(self._capture_size[1]),
                "process_width": self.process_width,
                "process_height": self.process_height,
                "error": self._error,
                "last_frame_at": last_frame_at,
            }

    def get_frame(self) -> np.ndarray | None:
        with self._condition:
            if self._frame is None:
                return None
            return self._frame.copy()

    def wait_for_frame(
        self,
        after_id: int,
        timeout: float = 1.0,
    ) -> tuple[int | None, np.ndarray | None]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._frame_id > after_id or not self._running,
                timeout=timeout,
            )
            if (
                not self._running
                or self._frame_id <= after_id
                or self._frame is None
            ):
                return None, None
            return self._frame_id, self._frame.copy()

    def _publish(self, frame: np.ndarray) -> None:
        if (
            frame.shape[1] != self.process_width
            or frame.shape[0] != self.process_height
        ):
            frame = cv2.resize(
                frame,
                (self.process_width, self.process_height),
                interpolation=cv2.INTER_AREA,
            )

        callback = self._frame_callback
        if callback is not None:
            try:
                callback(frame, time.monotonic())
            except Exception:
                if not self._callback_error_logged:
                    LOGGER.exception("Falha no processamento do frame")
                    self._callback_error_logged = True

        now = time.monotonic()
        with self._condition:
            if not self._running:
                return
            if self._last_frame_ts is not None:
                delta = now - self._last_frame_ts
                if delta > 0:
                    instant = 1.0 / delta
                    self._fps = (
                        instant
                        if self._fps <= 0
                        else (0.85 * self._fps + 0.15 * instant)
                    )
            self._last_frame_ts = now
            self._last_frame_at = time.time()
            self._frame = frame
            self._frame_id += 1
            self._frames += 1
            self._status = "streaming"
            self._error = None
            self._condition.notify_all()

    def _set_offline(self, message: str) -> None:
        with self._condition:
            self._status = "offline"
            self._error = message
            self._condition.notify_all()

    def _open_capture(self) -> cv2.VideoCapture | None:
        capture: cv2.VideoCapture | None = None
        if (
            self.backend == "dshow"
            and sys.platform.startswith("win")
            and hasattr(cv2, "CAP_DSHOW")
        ):
            capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)

        if capture is None or not capture.isOpened():
            if capture is not None:
                capture.release()
            capture = cv2.VideoCapture(self.index)

        if capture is None or not capture.isOpened():
            if capture is not None:
                capture.release()
            return None

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.capture_width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.capture_height)
        capture.set(cv2.CAP_PROP_FPS, 30)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        for _ in range(5):
            capture.read()

        actual_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or self.capture_width)
        actual_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or self.capture_height)
        with self._condition:
            self._capture_size = (actual_width, actual_height)
        LOGGER.info(
            "Webcam aberta: indice %s, %sx%s",
            self.index,
            actual_width,
            actual_height,
        )
        return capture

    def _run_camera(self) -> None:
        while self._running and not self._stop_event.is_set():
            capture = self._open_capture()
            if capture is None:
                LOGGER.warning("Webcam indisponivel (indice %s).", self.index)
                self._set_offline(OFFLINE_MESSAGE)
                if self._stop_event.wait(2.0):
                    break
                continue

            with self._condition:
                self._status = "streaming"
                self._error = None
                self._condition.notify_all()

            failures = 0
            while self._running and not self._stop_event.is_set():
                ok, frame = capture.read()
                if not ok or frame is None:
                    failures += 1
                    if failures >= 15:
                        self._set_offline(
                            "Sinal da webcam perdido. Tentando reconectar..."
                        )
                        break
                    if self._stop_event.wait(0.05):
                        break
                    continue
                failures = 0
                self._publish(frame)

            capture.release()
            if self._stop_event.wait(0.5):
                break

        with self._condition:
            self._status = "offline"
            self._running = False
            self._condition.notify_all()

    def _run_demo(self) -> None:
        source = DemoSource(self.process_width, self.process_height)
        interval = 1.0 / 30.0

        with self._condition:
            self._status = "streaming"
            self._error = None
            self._condition.notify_all()

        while self._running and not self._stop_event.is_set():
            started = time.monotonic()
            self._publish(source.read())
            remaining = interval - (time.monotonic() - started)
            if remaining > 0:
                self._stop_event.wait(remaining)

        with self._condition:
            self._status = "offline"
            self._running = False
            self._condition.notify_all()
