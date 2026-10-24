"""Vercel serverless entrypoint for the CreatorScope FastAPI backend.

Vercel's filesystem is read-only except /tmp, so SQLite must live in /tmp
(otherwise db.init_db() fails on startup). This is set BEFORE importing
app.main, because config reads DATABASE_PATH at import time.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_PATH", "/tmp/creatorscope.db")

# Ensure the repo root (parent of api/) is importable, wherever Vercel runs this from.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402  (Vercel serves this ASGI app)
