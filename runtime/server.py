#!/usr/bin/env python3
"""free-match dumb HTTP board — store & list envelopes only. No fees. No content police."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from fmlib import (  # noqa: E402
    BoardStore,
    derive_status,
    review_summary,
    utc_now,
    validate_envelope,
)

STATIC_DIR = RUNTIME / "static"
DEFAULT_HOST = os.environ.get("FM_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("FM_PORT", "8787"))
DEFAULT_BOARD = Path(os.environ.get("FM_BOARD_DIR", str(RUNTIME / "board" / "messages")))
DEFAULT_MEDIA = Path(os.environ.get("FM_MEDIA_DIR", str(RUNTIME / "board" / "media")))
TILE_URL = os.environ.get(
    "FM_TILE_URL",
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
)
TILE_ATTR = os.environ.get("FM_TILE_ATTR", "&copy; OpenStreetMap contributors")
NOMINATIM_URL = os.environ.get("FM_NOMINATIM_URL", "")

STORE: BoardStore | None = None
MEDIA_DIR: Path = DEFAULT_MEDIA
STARTED_AT = utc_now()


def json_bytes(data: Any, code: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return code, body, "application/json; charset=utf-8"


class Handler(BaseHTTPRequestHandler):
    server_version = "free-match-board/0.2"

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
        if length > 12_000_000:
            raise ValueError("payload too large")
        raw = self.rfile.read(length)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("JSON body must be object")
        return data

    def _read_raw(self, max_len: int = 12_000_000) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return b""
        if length > max_len:
            raise ValueError("payload too large")
        return self.rfile.read(length)

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
            if path.startswith("/media/"):
                return self._media(path[len("/media/") :], head_only=head_only)

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
                            "paid_boost": False,
                            "sponsored_ranking": False,
                            "project": "public-interest",
                            "affiliation": "none-with-commercial-marketplaces",
                            "note": "dumb pipe; public-interest; no rent; no paid pin; media via /media; law is government's job; quality is peer reviews",
                        },
                        "maps": {
                            "tile_url": TILE_URL,
                            "tile_attribution": TILE_ATTR,
                            "nominatim_url": NOMINATIM_URL or None,
                            "distance": "haversine",
                        },
                        "stats": STORE.stats(),
                    }
                )
                return self._send(code, body, ct)

            if path == "/api/v1/config":
                code, body, ct = json_bytes(
                    {
                        "tile_url": TILE_URL,
                        "tile_attribution": TILE_ATTR,
                        "nominatim_url": NOMINATIM_URL or None,
                        "media_upload": True,
                        "max_media_bytes": 10_000_000,
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
                require_geo = (qs.get("require_geo") or ["0"])[0] in ("1", "true", "yes")
                sort = (qs.get("sort") or ["time"])[0]
                near_lat = qs.get("near_lat") or qs.get("lat")
                near_lon = qs.get("near_lon") or qs.get("lon")
                radius = qs.get("radius_m") or qs.get("radius")
                try:
                    nlat = float(near_lat[0]) if near_lat and near_lat[0] != "" else None
                    nlon = float(near_lon[0]) if near_lon and near_lon[0] != "" else None
                    rad = float(radius[0]) if radius and radius[0] != "" else None
                except ValueError:
                    code, body, ct = json_bytes({"error": "invalid near_lat/near_lon/radius_m"}, 400)
                    return self._send(code, body, ct)
                try:
                    rows = STORE.query(
                        types=types,
                        q=q,
                        region=region,
                        limit=limit,
                        offset=offset,
                        summary=summary,
                        near_lat=nlat,
                        near_lon=nlon,
                        radius_m=rad,
                        require_geo=require_geo,
                        sort=sort,
                    )
                except ValueError as e:
                    code, body, ct = json_bytes({"error": str(e)}, 400)
                    return self._send(code, body, ct)
                code, body, ct = json_bytes(
                    {
                        "messages": rows,
                        "count": len(rows),
                        "origin": {"lat": nlat, "lon": nlon}
                        if nlat is not None and nlon is not None
                        else None,
                        "radius_m": rad,
                        "sort": sort,
                    }
                )
                return self._send(code, body, ct)

            if path.startswith("/api/v1/track/"):
                root = path[len("/api/v1/track/") :]
                msgs = STORE.thread(root)
                st = derive_status(msgs)
                code, body, ct = json_bytes({"root": root, "status": st, "messages": msgs})
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
                near_lat = qs.get("near_lat") or qs.get("lat")
                near_lon = qs.get("near_lon") or qs.get("lon")
                if near_lat and near_lon and near_lat[0] != "" and near_lon[0] != "":
                    from fmlib import extract_geo, format_distance_m, haversine_m

                    try:
                        o = (float(near_lat[0]), float(near_lon[0]))
                        g = extract_geo(msg)
                        if g:
                            d = round(haversine_m(o[0], o[1], g[0], g[1]), 1)
                            msg = dict(msg)
                            msg["_distance_m"] = d
                            msg["_distance_text"] = format_distance_m(d)
                    except ValueError:
                        pass
                code, body, ct = json_bytes(msg)
                return self._send(code, body, ct)

            if path.startswith("/api/v1/thread/"):
                root = path[len("/api/v1/thread/") :]
                msgs = STORE.thread(root)
                code, body, ct = json_bytes(
                    {"root": root, "messages": msgs, "status": derive_status(msgs)}
                )
                return self._send(code, body, ct)

            if path.startswith("/api/v1/reviews/"):
                actor = path[len("/api/v1/reviews/") :]
                code, body, ct = json_bytes(review_summary(STORE.list_all(), actor))
                return self._send(code, body, ct)

            if path == "/api/v1/distance":
                from fmlib import extract_geo, format_distance_m, haversine_m

                fl, fo = qs.get("from_lat"), qs.get("from_lon")
                tl, to = qs.get("to_lat"), qs.get("to_lon")
                fid = (qs.get("from_id") or [None])[0]
                tid = (qs.get("to_id") or [None])[0]
                try:
                    if fid and tid:
                        a, b = STORE.get(fid), STORE.get(tid)
                        if not a or not b:
                            code, body, ct = json_bytes({"error": "message not found"}, 404)
                            return self._send(code, body, ct)
                        ga, gb = extract_geo(a), extract_geo(b)
                        if not ga or not gb:
                            code, body, ct = json_bytes(
                                {"error": "one or both messages lack geo"}, 400
                            )
                            return self._send(code, body, ct)
                        d = round(haversine_m(ga[0], ga[1], gb[0], gb[1]), 1)
                        code, body, ct = json_bytes(
                            {
                                "from_id": fid,
                                "to_id": tid,
                                "from": {"lat": ga[0], "lon": ga[1]},
                                "to": {"lat": gb[0], "lon": gb[1]},
                                "distance_m": d,
                                "distance_text": format_distance_m(d),
                            }
                        )
                        return self._send(code, body, ct)
                    if fl and fo and tl and to:
                        d = round(
                            haversine_m(float(fl[0]), float(fo[0]), float(tl[0]), float(to[0])),
                            1,
                        )
                        code, body, ct = json_bytes(
                            {
                                "from": {"lat": float(fl[0]), "lon": float(fo[0])},
                                "to": {"lat": float(tl[0]), "lon": float(to[0])},
                                "distance_m": d,
                                "distance_text": format_distance_m(d),
                            }
                        )
                        return self._send(code, body, ct)
                    code, body, ct = json_bytes(
                        {"error": "need from_lat/from_lon/to_lat/to_lon or from_id/to_id"},
                        400,
                    )
                    return self._send(code, body, ct)
                except ValueError:
                    code, body, ct = json_bytes({"error": "invalid coordinates"}, 400)
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
                            "GET /api/v1/config",
                            "GET /api/v1/messages",
                            "POST /api/v1/messages",
                            "POST /api/v1/media",
                            "GET /media/{file}",
                            "GET /api/v1/thread/{id}",
                            "GET /api/v1/track/{id}",
                            "GET /api/v1/reviews/{actor_id}",
                            "GET /api/v1/distance",
                        ],
                        "media": {
                            "upload": "POST /api/v1/media",
                            "item_field": "item.attachments[]",
                        },
                        "maps": {"tile_url_env": "FM_TILE_URL", "distance": "haversine"},
                        "forbidden_server_behaviors": [
                            "charging fees",
                            "content moderation as protocol",
                            "mandatory KYC",
                            "paid boost",
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

            if path == "/api/v1/media":
                ctype = self.headers.get("Content-Type") or ""
                raw = self._read_raw()
                if not raw:
                    code, body, ct = json_bytes({"error": "empty body"}, 400)
                    return self._send(code, body, ct)
                filename = None
                mime = None
                data = raw
                if "application/json" in ctype:
                    obj = json.loads(raw.decode("utf-8"))
                    data = base64.b64decode(obj.get("content_base64") or "")
                    filename = obj.get("filename")
                    mime = obj.get("mime")
                else:
                    mime = ctype.split(";")[0].strip() or None
                    filename = (qs.get("filename") or [None])[0]
                if not data:
                    code, body, ct = json_bytes({"error": "no media data"}, 400)
                    return self._send(code, body, ct)
                if len(data) > 10_000_000:
                    code, body, ct = json_bytes({"error": "media too large (10MB max)"}, 400)
                    return self._send(code, body, ct)
                ext = ""
                if filename and "." in filename:
                    ext = "." + filename.rsplit(".", 1)[-1].lower()
                    ext = re.sub(r"[^a-z0-9.]", "", ext)[:8]
                if not ext and mime:
                    ext = mimetypes.guess_extension(mime.split(";")[0].strip()) or ""
                if not ext:
                    ext = ".bin"
                name = f"{uuid.uuid4().hex}{ext}"
                MEDIA_DIR.mkdir(parents=True, exist_ok=True)
                (MEDIA_DIR / name).write_bytes(data)
                uri = f"/media/{name}"
                guessed = mime or mimetypes.guess_type(name)[0]
                code, body, ct = json_bytes(
                    {
                        "ok": True,
                        "uri": uri,
                        "mime": guessed,
                        "bytes": len(data),
                        "attachment": {"uri": uri, "mime": guessed, "sha256": None},
                    },
                    201,
                )
                return self._send(code, body, ct)

            if path == "/api/v1/messages":
                msg = self._read_json()
                force = (qs.get("force") or ["0"])[0] in ("1", "true", "yes")
                if (qs.get("validate_only") or ["0"])[0] in ("1", "true", "yes"):
                    errs = validate_envelope(msg)
                    code, body, ct = json_bytes(
                        {"ok": not errs, "errors": errs}, 200 if not errs else 400
                    )
                    return self._send(code, body, ct)
                try:
                    stored = STORE.put(msg, force=force)
                except ValueError as e:
                    code, body, ct = json_bytes(
                        {"error": "invalid", "details": str(e).split("; ")}, 400
                    )
                    return self._send(code, body, ct)
                except FileExistsError as e:
                    code, body, ct = json_bytes({"error": str(e)}, 409)
                    return self._send(code, body, ct)
                code, body, ct = json_bytes(
                    {"ok": True, "id": stored["id"], "message": stored}, 201
                )
                return self._send(code, body, ct)

            if path == "/api/v1/validate":
                msg = self._read_json()
                errs = validate_envelope(msg)
                code, body, ct = json_bytes(
                    {"ok": not errs, "errors": errs}, 200 if not errs else 400
                )
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

    def _media(self, rel: str, head_only: bool = False) -> None:
        rel = rel.replace("\\", "/").lstrip("/")
        if ".." in rel.split("/") or not rel:
            code, body, ct = json_bytes({"error": "bad path"}, 400)
            return self._send(code, body, ct)
        path = (MEDIA_DIR / rel).resolve()
        if not str(path).startswith(str(MEDIA_DIR.resolve())):
            code, body, ct = json_bytes({"error": "bad path"}, 400)
            return self._send(code, body, ct)
        if not path.is_file():
            code, body, ct = json_bytes({"error": "not found"}, 404)
            return self._send(code, body, ct)
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if head_only:
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return
        self._send(200, data, ctype)

    def _static(self, rel: str, head_only: bool = False) -> None:
        rel = rel.replace("\\", "/").lstrip("/")
        if ".." in rel.split("/"):
            code, body, ct = json_bytes({"error": "bad path"}, 400)
            return self._send(code, body, ct)
        path = (STATIC_DIR / rel).resolve()
        if not str(path).startswith(str(STATIC_DIR.resolve())):
            code, body, ct = json_bytes({"error": "bad path"}, 400)
            return self._send(code, body, ct)
        if not path.is_file():
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
    global STORE, STARTED_AT, MEDIA_DIR
    p = argparse.ArgumentParser(description="free-match HTTP board (dumb pipe)")
    p.add_argument("--host", default=DEFAULT_HOST)
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--board-dir", default=str(DEFAULT_BOARD))
    p.add_argument("--media-dir", default=str(DEFAULT_MEDIA))
    args = p.parse_args(argv)

    STORE = BoardStore(Path(args.board_dir))
    MEDIA_DIR = Path(args.media_dir)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    STARTED_AT = utc_now()
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        json.dumps(
            {
                "listening": f"http://{args.host}:{args.port}",
                "board": str(Path(args.board_dir).resolve()),
                "media": str(MEDIA_DIR.resolve()),
                "ui": f"http://127.0.0.1:{args.port}/",
                "tiles": TILE_URL,
                "policy": "no platform fee, no content moderation, no KYC, no paid boost",
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
