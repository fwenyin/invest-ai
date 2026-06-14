"""Shared helpers for the data layer: env loading, JSON caching, CLI output.

Every tool module imports from here so behaviour (cache TTL, error shape,
key loading) is consistent and the FastMCP server can reuse the same functions.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_ENV_LOADED = False


def load_env() -> None:
    """Load .env from repo root once. Falls back silently if file/lib absent."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_path)
    except Exception:
        # Minimal parser if python-dotenv isn't installed yet.
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def env(key: str, default: str | None = None) -> str | None:
    load_env()
    val = os.environ.get(key, default)
    return val if val not in ("", None) else default


def cache_get(name: str, ttl_seconds: int) -> Any | None:
    """Return cached JSON for `name` if newer than ttl, else None."""
    path = CACHE_DIR / f"{name}.json"
    if not path.exists():
        return None
    if time.time() - path.stat().st_mtime > ttl_seconds:
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def cache_set(name: str, data: Any) -> None:
    path = CACHE_DIR / f"{name}.json"
    try:
        path.write_text(json.dumps(data, default=str))
    except Exception:
        pass


def ok(data: Any) -> dict:
    return {"ok": True, "data": data}


def err(message: str, **extra) -> dict:
    out = {"ok": False, "error": message}
    out.update(extra)
    return out


def emit(result: Any) -> None:
    """Pretty-print a JSON result for CLI use and exit non-zero on error."""
    print(json.dumps(result, indent=2, default=str))
    if isinstance(result, dict) and result.get("ok") is False:
        sys.exit(1)
