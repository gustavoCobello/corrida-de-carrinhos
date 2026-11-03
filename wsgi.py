"""Ponto de entrada WSGI para hospedagem (gunicorn, Render, Railway etc.)."""

from __future__ import annotations

import os

from app import create_app

app = create_app(demo=os.environ.get("DEMO", "1") != "0")
