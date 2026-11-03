"""Estado da corrida, chegadas, ranking e tempos."""

from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Any, Iterable

from .detection import Detection
from .geometry import crossing_between, side, side_sign

Point = tuple[float, float]


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat(timespec="milliseconds")


def _line_points(line: Any) -> tuple[Point, Point] | None:
    if not isinstance(line, dict):
        return None
    first = line.get("p1")
    second = line.get("p2")
    if not isinstance(first, (list, tuple)) or not isinstance(second, (list, tuple)):
        return None
    if len(first) < 2 or len(second) < 2:
        return None
    try:
        p1 = (float(first[0]), float(first[1]))
        p2 = (float(second[0]), float(second[1]))
    except (TypeError, ValueError):
        return None
    if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) < 1e-6:
        return None
    return p1, p2


@dataclass
class CarState:
    color: str
    label: str
    status: str = "waiting"
    position: int | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    crossed_at: datetime | None = None
    elapsed_ms: int | None = None
    delta_ms: int | None = None
    cx: float | None = None
    cy: float | None = None
    nx: float | None = None
    ny: float | None = None
    area: float | None = None
    start_distance: float | None = None
    progress: float = 0.0
    last_side: int | None = None
    last_point: Point | None = None
    pending_side: int | None = None
    pending_count: int = 0
    pending_crossing_at: float | None = None

    def reset_crossing(self) -> None:
        self.last_side = None
        self.last_point = None
        self.pending_side = None
        self.pending_count = 0
        self.pending_crossing_at = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "color": self.color,
            "label": self.label,
            "status": self.status,
            "position": self.position,
            "first_seen_at": _iso(self.first_seen_at),
            "last_seen_at": _iso(self.last_seen_at),
            "crossed_at": _iso(self.crossed_at),
            "elapsed_ms": self.elapsed_ms,
            "delta_ms": self.delta_ms,
            "cx": round(self.cx, 1) if self.cx is not None else None,
            "cy": round(self.cy, 1) if self.cy is not None else None,
            "nx": round(self.nx, 5) if self.nx is not None else None,
            "ny": round(self.ny, 5) if self.ny is not None else None,
            "area": round(self.area, 1) if self.area is not None else None,
            "progress": round(min(1.0, max(0.0, self.progress)), 3),
        }


class RaceManager:
    """Controla sorteio, largada, chegadas e ranking de uma bateria."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._lock = RLock()
        self._colors: dict[str, Any] = {}
        self._cars_per_race = 3
        self._confirm_frames = 2
        self._max_jump = 0.35
        self._status = "idle"
        self._lineup: list[str] = []
        self._cars: dict[str, CarState] = {}
        self._order: list[str] = []
        self._started_at: datetime | None = None
        self._started_mono: float | None = None
        self._finished_at: datetime | None = None
        self._finished_elapsed_ms = 0
        self.configure(config or {})

    def configure(self, config: dict[str, Any]) -> None:
        colors = config.get("colors")
        race = config.get("race")
        race = race if isinstance(race, dict) else {}
        with self._lock:
            self._colors = copy.deepcopy(colors) if isinstance(colors, dict) else {}
            try:
                self._cars_per_race = max(1, int(race.get("cars_per_race", 3)))
            except (TypeError, ValueError):
                self._cars_per_race = 3
            try:
                self._confirm_frames = max(1, int(race.get("confirm_frames", 2)))
            except (TypeError, ValueError):
                self._confirm_frames = 2
            for key, car in self._cars.items():
                entry = self._colors.get(key)
                if isinstance(entry, dict) and entry.get("label"):
                    car.label = str(entry["label"])

    def _label(self, key: str) -> str:
        entry = self._colors.get(key)
        if isinstance(entry, dict) and entry.get("label"):
            return str(entry["label"])
        return key.replace("_", " ").title()

    def arm(self, lineup: Iterable[str] | None = None) -> dict[str, Any]:
        with self._lock:
            if self._status == "running":
                raise ValueError("Finalize ou resete a corrida antes de sortear outra.")
            available = [
                key
                for key, value in self._colors.items()
                if isinstance(value, dict)
            ]
            if not available:
                raise ValueError("Nenhuma cor esta configurada.")

            if lineup is None:
                count = min(self._cars_per_race, len(available))
                selected = random.sample(available, count)
            else:
                selected = []
                for key in lineup:
                    if (
                        isinstance(key, str)
                        and key in available
                        and key not in selected
                    ):
                        selected.append(key)
                if not selected:
                    raise ValueError("A formacao informada nao tem cores validas.")
                selected = selected[: self._cars_per_race]

            self._lineup = selected
            self._cars = {
                key: CarState(color=key, label=self._label(key))
                for key in selected
            }
            self._order = []
            self._status = "armed"
            self._started_at = None
            self._started_mono = None
            self._finished_at = None
            self._finished_elapsed_ms = 0
            return self._snapshot_locked()

    def start(self, now_mono: float | None = None) -> dict[str, Any]:
        with self._lock:
            if self._status != "armed":
                raise ValueError("Sorteie os carros antes de iniciar a corrida.")
            if not self._lineup:
                raise ValueError("A formacao da corrida esta vazia.")
            self._started_at = datetime.now().astimezone()
            self._started_mono = (
                time.monotonic() if now_mono is None else float(now_mono)
            )
            self._finished_at = None
            self._finished_elapsed_ms = 0
            self._order = []
            self._status = "running"
            for car in self._cars.values():
                car.status = "running"
                car.position = None
                car.first_seen_at = None
                car.last_seen_at = None
                car.crossed_at = None
                car.elapsed_ms = None
                car.delta_ms = None
                car.nx = None
                car.ny = None
                car.start_distance = None
                car.progress = 0.0
                car.reset_crossing()
            return self._snapshot_locked()

    def reset(self) -> dict[str, Any]:
        with self._lock:
            self._status = "idle"
            self._lineup = []
            self._cars = {}
            self._order = []
            self._started_at = None
            self._started_mono = None
            self._finished_at = None
            self._finished_elapsed_ms = 0
            return self._snapshot_locked()

    def finish(self, now_mono: float | None = None) -> dict[str, Any]:
        with self._lock:
            if self._status != "running":
                raise ValueError("Nao existe uma corrida em andamento.")
            now = time.monotonic() if now_mono is None else float(now_mono)
            elapsed = self._elapsed_locked(now)
            self._status = "finished"
            self._finished_at = datetime.now().astimezone()
            self._finished_elapsed_ms = elapsed
            for car in self._cars.values():
                if car.status == "running":
                    car.status = "missed"
            return self._snapshot_locked()

    def _elapsed_locked(self, now_mono: float | None = None) -> int:
        if self._started_mono is None:
            return 0
        if self._status == "running":
            now = time.monotonic() if now_mono is None else float(now_mono)
            return max(0, int(round((now - self._started_mono) * 1000.0)))
        return max(0, int(self._finished_elapsed_ms))

    def observe(
        self,
        detections: Iterable[Detection],
        line: Any,
        now_mono: float | None = None,
        wall_time: datetime | None = None,
    ) -> None:
        with self._lock:
            if self._status != "running" or self._started_mono is None:
                return
            points = _line_points(line)
            if points is None:
                return
            line_p1, line_p2 = points
            line_length = math.hypot(
                line_p2[0] - line_p1[0],
                line_p2[1] - line_p1[1],
            )
            if line_length < 1e-6:
                return
            now = time.monotonic() if now_mono is None else float(now_mono)
            wall = wall_time or datetime.now().astimezone()
            by_color = {detection.color: detection for detection in detections}

            for key in self._lineup:
                car = self._cars.get(key)
                detection = by_color.get(key)
                if car is None or detection is None:
                    continue

                point = (detection.nx, detection.ny)
                value = side(line_p1, line_p2, point)
                distance = abs(value) / line_length
                current_side = side_sign(value)

                if car.first_seen_at is None:
                    car.first_seen_at = wall
                    car.start_distance = distance
                car.last_seen_at = wall
                car.cx = detection.cx
                car.cy = detection.cy
                car.nx = detection.nx
                car.ny = detection.ny
                car.area = detection.area

                if car.status == "finished":
                    car.progress = 1.0
                    continue

                if car.start_distance is None:
                    car.start_distance = distance
                denominator = max(0.02, float(car.start_distance))
                car.progress = min(1.0, max(0.0, 1.0 - distance / denominator))

                if current_side == 0:
                    continue

                if car.last_side is None or car.last_point is None:
                    car.last_side = current_side
                    car.last_point = point
                    continue

                if current_side == car.last_side:
                    car.last_point = point
                    car.pending_side = None
                    car.pending_count = 0
                    car.pending_crossing_at = None
                    continue

                if car.pending_side == current_side:
                    car.pending_count += 1
                else:
                    jump = math.hypot(
                        point[0] - car.last_point[0],
                        point[1] - car.last_point[1],
                    )
                    if jump > self._max_jump:
                        car.last_side = current_side
                        car.last_point = point
                        car.pending_side = None
                        car.pending_count = 0
                        car.pending_crossing_at = None
                        continue

                    crossing = crossing_between(
                        line_p1,
                        line_p2,
                        car.last_point,
                        point,
                    )
                    if crossing is None:
                        car.last_side = current_side
                        car.last_point = point
                        car.pending_side = None
                        car.pending_count = 0
                        car.pending_crossing_at = None
                        continue

                    car.pending_side = current_side
                    car.pending_count = 1
                    car.pending_crossing_at = now

                if (
                    car.pending_count < self._confirm_frames
                    or car.pending_crossing_at is None
                ):
                    continue

                elapsed = max(
                    0,
                    int(round((car.pending_crossing_at - self._started_mono) * 1000.0)),
                )
                car.status = "finished"
                car.position = len(self._order) + 1
                car.elapsed_ms = elapsed
                car.progress = 1.0
                if self._started_at is not None:
                    car.crossed_at = self._started_at + timedelta(
                        milliseconds=elapsed,
                    )
                else:
                    car.crossed_at = wall
                if self._order:
                    first = self._cars.get(self._order[0])
                    first_elapsed = first.elapsed_ms if first is not None else 0
                    car.delta_ms = max(0, elapsed - int(first_elapsed or 0))
                else:
                    car.delta_ms = 0
                self._order.append(key)
                car.last_side = current_side
                car.last_point = point
                car.pending_side = None
                car.pending_count = 0
                car.pending_crossing_at = None

                if len(self._order) >= len(self._lineup):
                    self._status = "finished"
                    self._finished_at = wall
                    self._finished_elapsed_ms = elapsed

    def _snapshot_locked(self) -> dict[str, Any]:
        now = time.monotonic() if self._status == "running" else None
        return {
            "status": self._status,
            "started_at": _iso(self._started_at),
            "finished_at": _iso(self._finished_at),
            "elapsed_ms": self._elapsed_locked(now),
            "lineup": list(self._lineup),
            "cars": [
                self._cars[key].to_dict()
                for key in self._lineup
                if key in self._cars
            ],
            "confirm_frames": self._confirm_frames,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_locked()
