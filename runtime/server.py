#!/usr/bin/env python3
"""free-match dumb HTTP board — store & list envelopes only. No fees. No content police."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

# ensure runtime on path
RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from fmlib import (  # noqa: E402
    BoardStore,
    review_summary,
    validate_envelope,
    utc_now,
)

STATIC_DIR = RUNTIME / "static"
DEFAULT_HOST = os.environ.get("FM_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("FM_PORT", "8787"))
DEFAULT_BOARD = Path(os.environ.get("FM_BOARD_DIR", str(RUNTIME / "board" / "messages")))

STORE: BoardStore | None = None
STARTED_AT = utc_now()


def json_bytes(data: Any, code: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return code, body, "application/json; charset=utf-8"


class Handler(BaseHTTPRequestHandler):
    server_version = "free-match-board/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > 2_000_000:
            raise ValueError("payload too large")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be object")
        return data

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET(head_only=True)

    def do_GET(self, head_only: bool = False) -> None:  # noqa: N802
        try:
            assert STORE is not None
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)

            if path in ("/", "/index.html"):
                return self._static("index.html", head_only=head_only)
            if path.startswith("/static/"):
                return self._static(path[len("/static/") :], head_only=head_only)
            if path in ("/app.js", "/app.css"):
                return self._static(path.lstrip("/"), head_only=head_only)

            if path == "/health":
                code, body, ct = json_bytes(
                    {
                        "ok": True,
                        "service": "free-match-board",
                        "v": 1,
                        "started_at": STARTED_AT,
                        "policy": {
                            "platform_fee": False,
                            "content_moderation": False,
                            "kyc_required": False,
                            "note": "dumb pipe; law is government's job; quality is peer reviews",
                        },
                        "stats": STORE.stats(),
                    }
                )
                return self._send(code, body, ct)

            if path == "/api/v1/messages":
                types_raw = (qs.get("type") or qs.get("types") or [""])[0]
                types = {t.strip() for t in types_raw.split(",") if t.strip()} or None
                q = (qs.get("q") or [""])[0]
                region = (qs.get("region") or [""])[0]
                limit = int((qs.get("limit") or ["200"])[0])
                offset = int((qs.get("offset") or ["0"])[0])
                summary = (qs.get("summary") or ["0"])[0] in ("1", "true", "yes")
                rows = STORE.query(types=types, q=q, region=region, limit=limit, offset=offset, summary=summary)
                code, body, ct = json_bytes({"messages": rows, "count": len(rows)})
                return self._send(code, body, ct)

            if path.startswith("/api/v1/messages/"):
                msg_id = path[len("/api/v1/messages/") :]
                if not msg_id:
                    code, body, ct = json_bytes({"error": "missing id"}, 400)
                    return self._send(code, body, ct)
                msg = STORE.get(msg_id)
                if not msg:
                    code, body, ct = json_bytes({"error": "not found"}, 404)
                    return self._send(code, body, ct)
                code, body, ct = json_bytes(msg)
                return self._send(code, body, ct)

            if path.startswith("/api/v1/thread/"):
                root = path[len("/api/v1/thread/") :]
                code, body, ct = json_bytes({"root": root, "messages": STORE.thread(root)})
                return self._send(code, body, ct)

            if path.startswith("/api/v1/reviews/"):
                actor = path[len("/api/v1/reviews/") :]
                code, body, ct = json_bytes(review_summary(STORE.list_all(), actor))
                return self._send(code, body, ct)

            if path == "/api/v1/stats":
                code, body, ct = json_bytes(STORE.stats())
                return self._send(code, body, ct)

            if path == "/api/v1/meta":
                code, body, ct = json_bytes(
                    {
                        "name": "free-match",
                        "protocol": 1,
                        "endpoints": [
                            "GET /health",
                            "GET /api/v1/messages",
                            "GET /api/v1/messages/{id}",
                            "POST /api/v1/messages",
                            "GET /api/v1/thread/{id}",
                            "GET /api/v1/reviews/{actor_id}",
                            "GET /api/v1/stats",
                        ],
                        "forbidden_server_behaviors": [
                            "charging fees",
                            "content moderation as protocol",
                            "mandatory KYC",
                        ],
                    }
                )
                return self._send(code, body, ct)

            code, body, ct = json_bytes({"error": "not found", "path": path}, 404)
            self._send(code, body, ct)
        except Exception as e:
            traceback.print_exc()
            code, body, ct = json_bytes({"error": str(e)}, 500)
            self._send(code, body, ct)

    def do_POST(self) -> None:  # noqa: N802
        try:
            assert STORE is not None
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            qs = parse_qs(parsed.query)

            if path == "/api/v1/messages":
                msg = self._read_json()
                force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
                # optional validate-only
                if (qs.get("validate_only") or ["0"])[0] in ("1", "true", "yes"):
                    errs = validate_envelope(msg)
                    if errs:
                        code, body, ct = json_bytes({"ok": False, "errors": errs}, 400)
                    else:
                        code, body, ct = json_bytes({"ok": True})
                    return self._send(code, body, ct)
                try:
                    stored = STORE.put(msg, force=force)
                except ValueError as e:
                    code, body, ct = json_bytes({"error": "invalid", "details": str(e).split("; ")}, 400)
                    return self._send(code, body, ct)
                except FileExistsError as e:
                    code, body, ct = json_bytes({"error": str(e)}, 409)
                    return self._send(code, body, ct)
                code, body, ct = json_bytes({"ok": True, "id": stored["id"], "message": stored}, 201)
                return self._send(code, body, ct)

            if path == "/api/v1/validate":
                msg = self._read_json()
                errs = validate_envelope(msg)
                code, body, ct = json_bytes({"ok": not errs, "errors": errs}, 200 if not errs else 400)
                return self._send(code, body, ct)

            code, body, ct = json_bytes({"error": "not found"}, 404)
            self._send(code, body, ct)
        except json.JSONDecodeError:
            code, body, ct = json_bytes({"error": "invalid json"}, 400)
            self._send(code, body, ct)
        except ValueError as e:
            code, body, ct = json_bytes({"error": str(e)}, 400)
            self._send(code, body, ct)
        except Exception as e:
            traceback.print_exc()
            code, body, ct = json_bytes({"error": str(e)}, 500)
            self._send(code, body, ct)

    def _static(self, rel: str, head_only: bool = False) -> None:
        # path safety
        rel = rel.replace("\\", "/").lstrip("/")
        if ".." in rel.split("/"):
            code, body, ct = json_bytes({"error": "bad path"}, 400)
            return self._send(code, body, ct)
        path = (STATIC_DIR / rel).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())):
            code, body, ct = json_bytes({"error": "bad path"}, 400)
            return self._send(code, body, ct)
        if not path.is_file():
            # fallback index
            if rel in ("", "index.html"):
                code, body, ct = json_bytes({"error": "UI missing; API still works at /api/v1/meta"}, 404)
                return self._send(code, body, ct)
            code, body, ct = json_bytes({"error": "not found"}, 404)
            return self._send(code, body, ct)
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix == ".js":
            ctype = "application/javascript; charset=utf-8"
        elif path.suffix == ".css":
            ctype = "text/css; charset=utf-8"
        elif path.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        if head_only:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return
        self._send(200, data, ctype)


def main(argv: list[str] | None = None) -> int:
    global STORE, STARTED_AT
    p = argparse.ArgumentParser(description="free-match HTTP board (dumb pipe)")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--board-dir", default=str(DEFAULT_BOARD))
    args = p.parse_args(argv)

    STORE = BoardStore(Path(args.board_dir))
    STARTED_AT = utc_now()
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        json.dumps(
            {
                "listening": f"http://{args.host}:{args.port}",
                "board": str(Path(args.board_dir).resolve()),
                "ui": f"http://127.0.0.1:{args.port}/",
                "health": f"http://127.0.0.1:{args.port}/health",
                "policy": "no platform fee, no content moderation, no KYC",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
