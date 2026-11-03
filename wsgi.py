"""Ponto de entrada WSGI para hospedagem (gunicorn, Render, Railway etc.)."""

from __future__ import annotations

import os

from app import create_app

source = os.environ.get("CAMERA_SOURCE")
if not source:
    source = "demo" if os.environ.get("DEMO", "1") != "0" else "webcam"

app = create_app(source=source)
