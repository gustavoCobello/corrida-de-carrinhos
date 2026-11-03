"""Carregamento, validacao e persistencia da configuracao."""

from __future__ import annotations

import copy
import json
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any

LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULTS_PATH = BASE_DIR / "config.example.json"
LOCAL_PATH = BASE_DIR / "config.local.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: esperado um objeto JSON")
    return data


def merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Mescla recursivamente, dando prioridade aos valores de override."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def clamp_point(point: Any) -> list[float] | None:
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        return None
    try:
        x = float(point[0])
        y = float(point[1])
    except (TypeError, ValueError):
        return None
    return [round(min(1.0, max(0.0, x)), 5), round(min(1.0, max(0.0, y)), 5)]


def bgr_to_hex(bgr: Any) -> str:
    try:
        blue, green, red = (int(max(0, min(255, int(channel)))) for channel in bgr)
    except (TypeError, ValueError):
        return "#94A3B8"
    return f"#{red:02X}{green:02X}{blue:02X}"


def _normalize(config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    camera = config.setdefault("camera", {})
    default_camera = defaults.get("camera", {})

    try:
        camera["index"] = int(camera.get("index", 0))
    except (TypeError, ValueError):
        camera["index"] = 0

    for key, fallback in (
        ("width", 1280),
        ("height", 720),
        ("process_width", 960),
        ("process_height", 540),
    ):
        default_value = int(default_camera.get(key, fallback))
        try:
            camera[key] = max(64, int(camera.get(key, default_value)))
        except (TypeError, ValueError):
            camera[key] = default_value

    camera["backend"] = str(camera.get("backend", "dshow")).lower()

    line = config.get("finish_line") or {}
    p1 = clamp_point(line.get("p1"))
    p2 = clamp_point(line.get("p2"))
    if p1 is None or p2 is None or p1 == p2:
        LOGGER.warning("Linha de chegada invalida; usando o padrao.")
        default_line = defaults.get("finish_line", {})
        p1 = clamp_point(default_line.get("p1")) or [0.15, 0.75]
        p2 = clamp_point(default_line.get("p2")) or [0.85, 0.75]
    config["finish_line"] = {"p1": p1, "p2": p2}

    roi = config.get("roi") or {}
    try:
        roi_x = min(1.0, max(0.0, float(roi.get("x", 0.0))))
        roi_y = min(1.0, max(0.0, float(roi.get("y", 0.0))))
        roi_w = min(1.0 - roi_x, max(0.01, float(roi.get("w", 1.0))))
        roi_h = min(1.0 - roi_y, max(0.01, float(roi.get("h", 1.0))))
    except (TypeError, ValueError):
        roi_x, roi_y, roi_w, roi_h = 0.0, 0.0, 1.0, 1.0
    config["roi"] = {"x": roi_x, "y": roi_y, "w": roi_w, "h": roi_h}

    server = config.setdefault("server", {})
    server["host"] = str(server.get("host", "127.0.0.1"))
    try:
        server["port"] = int(server.get("port", 5000))
    except (TypeError, ValueError):
        server["port"] = 5000
    try:
        server["poll_ms"] = max(100, int(server.get("poll_ms", 200)))
    except (TypeError, ValueError):
        server["poll_ms"] = 200

    colors = config.get("colors")
    if not isinstance(colors, dict) or not colors:
        LOGGER.warning("Cores ausentes; usando o padrao.")
        config["colors"] = copy.deepcopy(defaults.get("colors", {}))

    race = config.setdefault("race", {})
    try:
        race["cars_per_race"] = min(4, max(1, int(race.get("cars_per_race", 3))))
    except (TypeError, ValueError):
        race["cars_per_race"] = 3
    try:
        race["confirm_frames"] = max(1, int(race.get("confirm_frames", 2)))
    except (TypeError, ValueError):
        race["confirm_frames"] = 2
    try:
        race["min_area_px"] = max(1, int(race.get("min_area_px", 400)))
    except (TypeError, ValueError):
        race["min_area_px"] = 400

    config["debug"] = bool(config.get("debug", False))
    return config


class ConfigStore:
    """Mantem a configuracao efetiva e grava apenas as sobrescritas locais."""

    def __init__(
        self,
        defaults_path: Path | str = DEFAULTS_PATH,
        local_path: Path | str = LOCAL_PATH,
    ) -> None:
        self.defaults_path = Path(defaults_path)
        self.local_path = Path(local_path)
        self._lock = RLock()
        self._defaults = read_json(self.defaults_path)
        self._overrides = self._read_local()
        self._config = _normalize(
            merge(self._defaults, self._overrides),
            self._defaults,
        )
        self._version = 0
        self._local_mtime = self._mtime()

    def _read_local(self) -> dict[str, Any]:
        if not self.local_path.exists():
            return {}
        try:
            return read_json(self.local_path)
        except (OSError, ValueError) as exc:
            LOGGER.warning("Nao foi possivel ler %s: %s", self.local_path.name, exc)
            return {}

    def _mtime(self) -> int | None:
        try:
            return self.local_path.stat().st_mtime_ns
        except OSError:
            return None

    def _rebuild(self) -> None:
        self._config = _normalize(
            merge(self._defaults, self._overrides),
            self._defaults,
        )
        self._version += 1

    def _reload_if_changed_locked(self) -> None:
        mtime = self._mtime()
        if mtime == self._local_mtime:
            return
        self._overrides = self._read_local()
        self._local_mtime = mtime
        self._rebuild()
        LOGGER.info("Configuracao local recarregada.")

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._reload_if_changed_locked()
            return copy.deepcopy(self._config)

    @property
    def version(self) -> int:
        with self._lock:
            self._reload_if_changed_locked()
            return self._version

    def save_line(self, p1: Any, p2: Any) -> dict[str, Any]:
        first = clamp_point(p1)
        second = clamp_point(p2)
        if first is None or second is None:
            raise ValueError("Informe dois pontos com coordenadas numericas.")
        if first == second:
            raise ValueError("Os dois pontos da linha devem ser diferentes.")

        with self._lock:
            previous = copy.deepcopy(self._overrides)
            self._overrides["finish_line"] = {"p1": first, "p2": second}
            try:
                self._write_local()
            except OSError:
                self._overrides = previous
                raise
            self._rebuild()
            return copy.deepcopy(self._config["finish_line"])

    def save_section(self, section: str, values: Any) -> dict[str, Any]:
        if not isinstance(section, str) or not section:
            raise ValueError("Secao invalida.")
        if not isinstance(values, dict):
            raise ValueError("Os valores da secao devem ser um objeto JSON.")

        with self._lock:
            previous = copy.deepcopy(self._overrides)
            current = self._overrides.get(section, {})
            if not isinstance(current, dict):
                current = {}
            self._overrides[section] = merge(current, values)
            try:
                self._write_local()
            except OSError:
                self._overrides = previous
                raise
            self._rebuild()
            return copy.deepcopy(self._config)

    def _write_local(self) -> None:
        temporary = self.local_path.with_name(self.local_path.name + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(self._overrides, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, self.local_path)
        self._local_mtime = self._mtime()
