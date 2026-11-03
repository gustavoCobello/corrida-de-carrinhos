"""Pipeline compartilhado entre captura, deteccao, corrida e API."""

from __future__ import annotations

import time
from threading import RLock
from typing import Any, Iterable

import numpy as np

from .config import ConfigStore
from .detection import ColorDetector, Detection
from .race import RaceManager


class VisionPipeline:
    """Processa cada frame e mantem o estado visivel para Flask e overlay."""

    def __init__(self, config_store: ConfigStore) -> None:
        self._store = config_store
        self._lock = RLock()
        self._version = -1
        self._config: dict[str, Any] = {}
        self._detector = ColorDetector({})
        self._race = RaceManager()
        self._detections: list[Detection] = []
        self._detected_at: float | None = None
        self._refresh()

    def _refresh(self) -> None:
        version = self._store.version
        if version == self._version:
            return
        config = self._store.snapshot()
        self._config = config
        self._detector = ColorDetector(config)
        self._race.configure(config)
        self._version = version

    def process(self, frame: np.ndarray, now_mono: float | None = None) -> None:
        with self._lock:
            self._refresh()
            detector = self._detector
            line = self._config.get("finish_line")

        detections = detector.detect(frame)

        now = time.monotonic() if now_mono is None else float(now_mono)
        with self._lock:
            self._detections = detections
            self._detected_at = now
            self._race.observe(detections, line, now_mono=now)

    def arm(self, lineup: Iterable[str] | None = None) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return self._race.arm(lineup)

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return self._race.start()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return self._race.reset()

    def finish(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            return self._race.finish()

    def race_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._race.snapshot()

    def detections_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [detection.to_dict() for detection in self._detections]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "race": self._race.snapshot(),
                "detections": [
                    detection.to_dict() for detection in self._detections
                ],
                "detected_at": self._detected_at,
            }
