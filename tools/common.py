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
    if env_path.exists():
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
    _wire_ca_bundle()


def _wire_ca_bundle() -> None:
    """Point requests/ssl at a corporate CA bundle when one is present.

    Behind a TLS-intercepting proxy, certifi's public store can't verify the
    proxy's substituted cert ('unable to get local issuer certificate'), so the
    Finnhub feeds (news/econ/earnings) fail. If a bundle is configured (via
    REQUESTS_CA_BUNDLE/SSL_CERT_FILE) or sitting at config/corp-ca-bundle.pem,
    export it through both standard env vars so `requests` (REQUESTS_CA_BUNDLE)
    and raw ssl/httpx (SSL_CERT_FILE) honor it. Always resolved to an absolute
    path so the working directory doesn't matter.
    """
    bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if bundle and not Path(bundle).is_absolute():
        bundle = str((ROOT / bundle).resolve())
    if not bundle:
        default = ROOT / "config" / "corp-ca-bundle.pem"
        bundle = str(default) if default.exists() else None
    if not bundle or not Path(bundle).exists():
        return
    os.environ["REQUESTS_CA_BUNDLE"] = bundle
    os.environ["SSL_CERT_FILE"] = bundle


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
