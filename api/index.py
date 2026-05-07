"""
Vercel serverless entry point for the FastAPI backend.

Vercel routes /_/backend/* here via rewrite. This wrapper strips
the /_/backend prefix so FastAPI sees /health, /finish-catalogue, etc.
"""
import sys
import os

# Make `app.*` imports resolve from the backend directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.main import app as _backend_app  # noqa: E402

_PREFIX = "/_/backend"


class _StripPrefixMiddleware:
    """ASGI middleware that strips /_/backend from incoming paths."""

    def __init__(self, app, prefix: str):
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path: str = scope.get("path", "")
            if path.startswith(self.prefix):
                scope = dict(scope)
                scope["path"] = path[len(self.prefix):] or "/"
                scope["raw_path"] = scope["path"].encode()
        await self.app(scope, receive, send)


app = _StripPrefixMiddleware(_backend_app, _PREFIX)
