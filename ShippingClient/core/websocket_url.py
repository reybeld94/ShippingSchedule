"""Utilities for normalizing Shipping Schedule WebSocket URLs."""
from urllib.parse import urlsplit, urlunsplit

DEFAULT_WEBSOCKET_PATH = "/ws"
DEFAULT_WEBSOCKET_URL = "ws://localhost:8000/ws"


def normalize_websocket_url(url: str | None, default: str = DEFAULT_WEBSOCKET_URL) -> str:
    """Return a usable WebSocket URL, defaulting root paths to ``/ws``.

    Users sometimes enter the server root (for example ``ws://host:8000`` or
    ``http://host:8000``) in the WebSocket setting. FastAPI only serves the
    realtime endpoint at ``/ws``, so root WebSocket attempts are rejected with
    repeated 403 log entries. This helper keeps custom non-root paths intact
    while converting an empty/root path to the app's default WebSocket path.
    """
    raw_url = str(url or "").strip() or default

    if raw_url.startswith("//"):
        raw_url = f"ws:{raw_url}"
    elif "://" not in raw_url:
        raw_url = f"ws://{raw_url}"

    parsed = urlsplit(raw_url)
    scheme = parsed.scheme.lower()
    if scheme == "http":
        scheme = "ws"
    elif scheme == "https":
        scheme = "wss"
    elif scheme not in {"ws", "wss"}:
        scheme = "ws"

    path = parsed.path.rstrip("/")
    if not path:
        path = DEFAULT_WEBSOCKET_PATH

    return urlunsplit((scheme, parsed.netloc, path, parsed.query, parsed.fragment))
