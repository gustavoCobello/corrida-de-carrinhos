"""Servidor local do toy-car-race-vision."""

from __future__ import annotations

import argparse
import atexit
import logging
import time
from datetime import datetime
from typing import Any, Iterator

import cv2
from flask import Flask, Response, jsonify, render_template, request

from src.camera import CameraStream
from src.config import ConfigStore, bgr_to_hex
from src.overlay import draw_overlay, make_offline_frame
from src.pipeline import VisionPipeline

LOGGER = logging.getLogger(__name__)


def _color_options(config: dict[str, Any]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    for key, value in config.get("colors", {}).items():
        if not isinstance(value, dict):
            continue
        label = value.get("label") or key.replace("_", " ").title()
        options.append(
            {
                "key": key,
                "label": str(label),
                "hex": bgr_to_hex(value.get("bgr", [148, 163, 184])),
            }
        )
    return options


def _mjpeg_frames(
    camera: CameraStream,
    config_store: ConfigStore,
    pipeline: VisionPipeline,
    overlay: bool = True,
) -> Iterator[bytes]:
    last_id = -1
    placeholder_size = (camera.process_width, camera.process_height)

    while True:
        frame_id, frame = camera.wait_for_frame(last_id, timeout=1.0)
        status = camera.status()

        if frame is None:
            if not camera.is_running():
                break
            if status["status"] == "offline":
                frame = make_offline_frame(status, placeholder_size)
            else:
                time.sleep(0.05)
                continue
        else:
            last_id = frame_id
            if overlay:
                state = pipeline.snapshot()
                draw_overlay(
                    frame,
                    config_store.snapshot(),
                    status,
                    detections=state["detections"],
                    race=state["race"],
                )

        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 82],
        )
        if not ok:
            continue

        payload = encoded.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n"
            + payload
            + b"\r\n"
        )


def create_app(
    demo: bool = False,
    camera_index: int | None = None,
    config_store: ConfigStore | None = None,
) -> Flask:
    config_store = config_store or ConfigStore()
    config = config_store.snapshot()

    camera_config = config
    if camera_index is not None:
        camera_config = {
            **config,
            "camera": {**config["camera"], "index": int(camera_index)},
        }

    pipeline = VisionPipeline(config_store)
    camera = CameraStream(camera_config, demo=demo)
    camera.set_frame_callback(pipeline.process)
    camera.start()
    atexit.register(camera.stop)

    app = Flask(__name__)
    app.json.sort_keys = False
    app.extensions["camera"] = camera
    app.extensions["config_store"] = config_store
    app.extensions["pipeline"] = pipeline

    @app.get("/")
    def index() -> str:
        snapshot = config_store.snapshot()
        return render_template(
            "index.html",
            colors=_color_options(snapshot),
            poll_ms=snapshot["server"]["poll_ms"],
        )

    @app.get("/setup")
    def setup() -> str:
        snapshot = config_store.snapshot()
        return render_template(
            "setup.html",
            poll_ms=snapshot["server"]["poll_ms"],
            process_width=snapshot["camera"]["process_width"],
            process_height=snapshot["camera"]["process_height"],
            line=snapshot["finish_line"],
            roi=snapshot["roi"],
        )

    @app.get("/video_feed")
    def video_feed() -> Response:
        show_overlay = request.args.get("overlay", "1") != "0"
        response = Response(
            _mjpeg_frames(
                camera,
                config_store,
                pipeline,
                overlay=show_overlay,
            ),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        return response

    @app.get("/api/state")
    def api_state() -> Response:
        snapshot = config_store.snapshot()
        status = camera.status()
        vision = pipeline.snapshot()
        return jsonify(
            {
                "phase": 4,
                "server_time": datetime.now()
                .astimezone()
                .isoformat(timespec="milliseconds"),
                "camera": status,
                "config": {
                    "camera_index": status["index"],
                    "line": snapshot["finish_line"],
                    "roi": snapshot["roi"],
                    "colors": _color_options(snapshot),
                    "poll_ms": snapshot["server"]["poll_ms"],
                },
                "race": vision["race"],
                "detections": vision["detections"],
            }
        )

    @app.get("/api/config")
    def api_config() -> Response:
        return jsonify(config_store.snapshot())

    @app.post("/api/config/line")
    def api_config_line() -> Response:
        payload = request.get_json(silent=True) or {}
        try:
            line = config_store.save_line(payload.get("p1"), payload.get("p2"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except OSError:
            LOGGER.exception("Falha ao salvar a linha")
            return jsonify(
                {"error": "Não foi possível gravar config.local.json."}
            ), 500
        return jsonify({"ok": True, "line": line})

    @app.post("/api/config/roi")
    def api_config_roi() -> Response:
        payload = request.get_json(silent=True) or {}
        values = payload.get("roi", payload)
        if not isinstance(values, dict):
            return jsonify({"error": "Formato de ROI inválido."}), 400
        try:
            roi_values = {
                key: float(values.get(key)) for key in ("x", "y", "w", "h")
            }
        except (TypeError, ValueError):
            return jsonify({"error": "Informe x, y, w e h numéricos."}), 400
        if roi_values["w"] <= 0 or roi_values["h"] <= 0:
            return jsonify(
                {"error": "A largura e a altura da ROI devem ser positivas."}
            ), 400
        try:
            config = config_store.save_section("roi", roi_values)
        except OSError:
            LOGGER.exception("Falha ao salvar a ROI")
            return jsonify(
                {"error": "Não foi possível gravar config.local.json."}
            ), 500
        return jsonify({"ok": True, "roi": config["roi"]})

    @app.post("/api/config/colors")
    def api_config_colors() -> Response:
        payload = request.get_json(silent=True) or {}
        colors = payload.get("colors", payload)
        if not isinstance(colors, dict) or not colors:
            return jsonify({"error": "Formato de cores inválido."}), 400
        try:
            config = config_store.save_section("colors", colors)
        except OSError:
            LOGGER.exception("Falha ao salvar as cores")
            return jsonify(
                {"error": "Não foi possível gravar config.local.json."}
            ), 500
        return jsonify({"ok": True, "colors": config["colors"]})

    @app.post("/api/race/arm")
    def api_race_arm() -> Response:
        payload = request.get_json(silent=True) or {}
        lineup = payload.get("lineup") if isinstance(payload, dict) else None
        if lineup is not None and (
            not isinstance(lineup, list)
            or not all(isinstance(item, str) for item in lineup)
        ):
            return jsonify({"error": "lineup deve ser uma lista de cores."}), 400
        try:
            race = pipeline.arm(lineup)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True, "race": race})

    @app.post("/api/race/start")
    def api_race_start() -> Response:
        try:
            race = pipeline.start()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True, "race": race})

    @app.post("/api/race/reset")
    def api_race_reset() -> Response:
        return jsonify({"ok": True, "race": pipeline.reset()})

    @app.post("/api/race/finish")
    def api_race_finish() -> Response:
        try:
            race = pipeline.finish()
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 409
        return jsonify({"ok": True, "race": race})

    @app.get("/api/setup/frame")
    def api_setup_frame() -> Response:
        status = camera.status()
        frame = camera.get_frame()
        if frame is None:
            frame = make_offline_frame(
                status,
                (camera.process_width, camera.process_height),
            )
        else:
            vision = pipeline.snapshot()
            draw_overlay(
                frame,
                config_store.snapshot(),
                status,
                detections=vision["detections"],
                race=vision["race"],
            )
        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), 88],
        )
        if not ok:
            return jsonify({"error": "Falha ao codificar o frame."}), 503
        response = Response(encoded.tobytes(), mimetype="image/jpeg")
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def api_health() -> Response:
        return jsonify(
            {
                "ok": True,
                "camera": camera.status()["status"],
                "race": pipeline.race_snapshot()["status"],
            }
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Servidor local do toy-car-race-vision",
    )
    parser.add_argument("--host", help="Endereco do servidor (padrao: config)")
    parser.add_argument("--port", type=int, help="Porta do servidor (padrao: config)")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Usa uma pista sintetica, sem webcam",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        help="Sobrescreve o indice da webcam",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ativa o modo de depuracao do Flask",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config_store = ConfigStore()
    snapshot = config_store.snapshot()
    host = args.host or snapshot["server"]["host"]
    port = args.port or snapshot["server"]["port"]

    app = create_app(
        demo=args.demo,
        camera_index=args.camera_index,
        config_store=config_store,
    )
    camera = app.extensions["camera"]
    LOGGER.info(
        "Servidor em http://%s:%s (fonte: %s)",
        host,
        port,
        "demo" if camera.demo else f"webcam {camera.index}",
    )
    try:
        app.run(
            host=host,
            port=port,
            debug=args.debug,
            threaded=True,
            use_reloader=False,
        )
    finally:
        camera.stop()


if __name__ == "__main__":
    main()
