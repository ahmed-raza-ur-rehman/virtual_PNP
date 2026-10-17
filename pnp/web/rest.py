"""REST API framework (stdlib-based)."""
from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class Route:
    method: str
    pattern: str
    handler: Callable
    regex: re.Pattern = field(init=False)

    def __post_init__(self):
        # convert {param} to regex group
        p = self.pattern
        p = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", p)
        self.regex = re.compile(f"^{p}$")


class RESTRouter:
    def __init__(self):
        self.routes: list[Route] = []
        self.middleware: list[Callable] = []
        self.error_handlers: dict[int, Callable] = {}

    def get(self, pattern: str):
        def decorator(handler):
            self.routes.append(Route("GET", pattern, handler))
            return handler
        return decorator

    def post(self, pattern: str):
        def decorator(handler):
            self.routes.append(Route("POST", pattern, handler))
            return handler
        return decorator

    def put(self, pattern: str):
        def decorator(handler):
            self.routes.append(Route("PUT", pattern, handler))
            return handler
        return decorator

    def delete(self, pattern: str):
        def decorator(handler):
            self.routes.append(Route("DELETE", pattern, handler))
            return handler
        return decorator

    def patch(self, pattern: str):
        def decorator(handler):
            self.routes.append(Route("PATCH", pattern, handler))
            return handler
        return decorator

    def add_middleware(self, mw: Callable):
        self.middleware.append(mw)

    def add_error_handler(self, status: int, handler: Callable):
        self.error_handlers[status] = handler

    def resolve(self, method: str, path: str) -> tuple[Callable | None, dict[str, str]]:
        for route in self.routes:
            if route.method != method:
                continue
            m = route.regex.match(path)
            if m:
                return route.handler, m.groupdict()
        return None, {}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method", "GET")
        path = request.get("path", "/")
        # strip query
        parsed = urlparse(path)
        path = parsed.path
        query = parse_qs(parsed.query)
        handler, params = self.resolve(method, path)
        if handler is None:
            return {"status": 404, "body": {"error": "Not found"}}
        # middleware
        for mw in self.middleware:
            result = mw(request)
            if result is not None:
                return result
        try:
            body = handler(request, params, query)
            if isinstance(body, tuple):
                status, data = body
                return {"status": status, "body": data}
            return {"status": 200, "body": body}
        except (ValueError, RuntimeError) as e:
            handler_eh = self.error_handlers.get(500)
            if handler_eh:
                return handler_eh(e)
            return {"status": 500, "body": {"error": str(e)}}


class RESTHandler(BaseHTTPRequestHandler):
    router: RESTRouter = None

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_PATCH(self):
        self._handle("PATCH")

    def _handle(self, method):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else ""
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        req = {"method": method, "path": self.path, "headers": dict(self.headers), "body": data, "query": {}}
        result = self.router.handle(req)
        status = result.get("status", 200)
        body_bytes = json.dumps(result.get("body", {})).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def log_message(self, *args):
        pass


class Pagination:
    @staticmethod
    def paginate(items: list, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        total = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "items": items[start:end],
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }


class RateLimiter:
    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self.requests: dict[str, list[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        self.requests[client_id] = [t for t in self.requests[client_id] if now - t < self.window]
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        self.requests[client_id].append(now)
        return True

    def remaining(self, client_id: str) -> int:
        now = time.time()
        if client_id not in self.requests:
            return self.max_requests
        recent = [t for t in self.requests[client_id] if now - t < self.window]
        return max(0, self.max_requests - len(recent))


class CORSHandler:
    def __init__(self, allowed_origins: list[str] | None = None, allowed_methods: list[str] | None = None):
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

    def handle_preflight(self, origin: str) -> dict[str, str]:
        headers = {}
        if origin in self.allowed_origins or "*" in self.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin if origin in self.allowed_origins else "*"
            headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            headers["Access-Control-Max-Age"] = "86400"
        return headers


class APIVersioning:
    def __init__(self):
        self.versions: dict[str, RESTRouter] = {}

    def register(self, version: str, router: RESTRouter):
        self.versions[version] = router

    def get_router(self, version: str) -> RESTRouter | None:
        return self.versions.get(version)

    def latest(self) -> str:
        return max(self.versions.keys()) if self.versions else ""
