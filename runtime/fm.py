#!/usr/bin/env python3
"""free-match CLI — local board or remote --board URL. No rent. No content police."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from fmlib import (  # noqa: E402
    DEFAULT_BOARD,
    DEFAULT_IDS,
    BoardStore,
    build_have,
    build_want,
    create_identity,
    load_identity,
    load_json,
    public_identity,
    review_summary,
    sign_message,
    validate_envelope,
)

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


def emit(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


class RemoteBoard:
    def __init__(self, base: str, timeout: float = 30.0):
        self.base = base.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str, query: dict[str, str] | None = None) -> str:
        url = self.base + path
        if query:
            url += "?" + urllib.parse.urlencode({k: v for k, v in query.items() if v is not None and v != ""})
        return url

    def _req(self, method: str, path: str, body: dict | None = None, query: dict | None = None) -> Any:
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self._url(path, query),
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw)
            except Exception:
                detail = {"error": raw or str(e)}
            raise SystemExit(json.dumps({"http_error": e.code, "detail": detail}, ensure_ascii=False, indent=2))

    def put(self, msg: dict[str, Any], force: bool = False) -> dict[str, Any]:
        q = {"force": "1"} if force else None
        res = self._req("POST", "/api/v1/messages", msg, q)
        return res.get("message") or msg

    def query(self, types=None, q="", region="", limit=200, offset=0, summary=False,
              near_lat=None, near_lon=None, radius_m=None, require_geo=False, sort="time"):
        type_s = ",".join(sorted(types)) if types else ""
        query = {
            "type": type_s,
            "q": q,
            "region": region,
            "limit": str(limit),
            "offset": str(offset),
            "summary": "1" if summary else "0",
            "sort": sort,
        }
        if near_lat is not None:
            query["near_lat"] = str(near_lat)
        if near_lon is not None:
            query["near_lon"] = str(near_lon)
        if radius_m is not None:
            query["radius_m"] = str(radius_m)
        if require_geo:
            query["require_geo"] = "1"
        res = self._req("GET", "/api/v1/messages", query=query)
        return res.get("messages") or []

    def get(self, msg_id: str):
        return self._req("GET", f"/api/v1/messages/{urllib.parse.quote(msg_id)}")

    def thread(self, root_id: str):
        res = self._req("GET", f"/api/v1/thread/{urllib.parse.quote(root_id)}")
        return res.get("messages") or []

    def list_all(self):
        return self.query(limit=1000)

    def reviews(self, actor_id: str):
        return self._req("GET", f"/api/v1/reviews/{urllib.parse.quote(actor_id)}")


def get_board(args: argparse.Namespace):
    if getattr(args, "board", None):
        return RemoteBoard(args.board)
    return BoardStore(Path(getattr(args, "board_dir", None) or DEFAULT_BOARD))


def attach_match(body: dict[str, Any], vertical: str | None, mode: str | None, max_accepts: int | None) -> dict[str, Any]:
    if not vertical and not mode and max_accepts is None:
        return body
    match: dict[str, Any] = {}
    if mode:
        match["mode"] = mode
    if vertical:
        match["vertical"] = vertical
    if max_accepts is not None:
        match["max_accepts"] = max_accepts
        match["exclusive"] = max_accepts <= 1
    body = dict(body)
    body["match"] = match
    return body


def cmd_id_new(args: argparse.Namespace) -> int:
    doc = create_identity(args.name, Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    out = public_identity(doc)
    if args.show_secret:
        out["privkey"] = doc.get("privkey")
    emit(out)
    return 0


def cmd_id_show(args: argparse.Namespace) -> int:
    doc = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not doc:
        print("no identity; run: python runtime/fm.py id new --name <handle>", file=sys.stderr)
        return 1
    emit(public_identity(doc))
    return 0


def read_msg(args: argparse.Namespace) -> dict[str, Any]:
    if getattr(args, "file", None):
        return load_json(Path(args.file))
    if getattr(args, "stdin", False):
        return json.load(sys.stdin)
    raise SystemExit("need --file or --stdin")


def cmd_validate(args: argparse.Namespace) -> int:
    msg = read_msg(args)
    errs = validate_envelope(msg)
    if errs:
        print("INVALID")
        for e in errs:
            print(f"- {e}")
        return 1
    print("OK")
    return 0


def cmd_post(args: argparse.Namespace) -> int:
    board = get_board(args)
    msg = read_msg(args)
    if args.sign:
        ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
        if not ident:
            print("cannot sign: no identity", file=sys.stderr)
            return 1
        msg = sign_message(msg, ident)
    if isinstance(board, RemoteBoard):
        stored = board.put(msg, force=args.force)
        emit({"posted": "remote", "id": stored.get("id"), "type": stored.get("type"), "message": stored})
        return 0
    stored = board.put(msg, force=args.force)
    path = board.messages_dir / f"{stored['id']}.json"
    emit({"posted": str(path), "id": stored["id"], "type": stored["type"]})
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    board = get_board(args)
    types = {t.strip() for t in (args.type or "").split(",") if t.strip()} or None
    kwargs = dict(
        types=types,
        q=args.q or "",
        region=args.region or "",
        summary=True,
        near_lat=args.near_lat,
        near_lon=args.near_lon,
        radius_m=args.radius_m,
        require_geo=args.require_geo,
        sort=args.sort,
    )
    if isinstance(board, RemoteBoard):
        rows = board.query(**kwargs)
    else:
        rows = board.query(**kwargs)
    emit(rows)
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        emit(board.get(args.msg_id))
    else:
        msg = board.get(args.msg_id)
        if not msg:
            print("not found", file=sys.stderr)
            return 1
        emit(msg)
    return 0


def cmd_distance(args: argparse.Namespace) -> int:
    from fmlib import extract_geo, format_distance_m, haversine_m

    board = get_board(args)
    if args.from_id and args.to_id:
        if isinstance(board, RemoteBoard):
            url_path = f"/api/v1/distance?from_id={args.from_id}&to_id={args.to_id}"
            # reuse remote
            res = board._req("GET", f"/api/v1/distance", query={"from_id": args.from_id, "to_id": args.to_id})
            emit(res)
            return 0
        a, b = board.get(args.from_id), board.get(args.to_id)
        if not a or not b:
            print("not found", file=sys.stderr)
            return 1
        ga, gb = extract_geo(a), extract_geo(b)
        if not ga or not gb:
            print("missing geo on one or both messages", file=sys.stderr)
            return 1
        d = round(haversine_m(ga[0], ga[1], gb[0], gb[1]), 1)
        emit({"from_id": args.from_id, "to_id": args.to_id, "distance_m": d, "distance_text": format_distance_m(d),
              "from": {"lat": ga[0], "lon": ga[1]}, "to": {"lat": gb[0], "lon": gb[1]}})
        return 0
    if None in (args.from_lat, args.from_lon, args.to_lat, args.to_lon):
        print("need --from-id/--to-id or all of --from-lat --from-lon --to-lat --to-lon", file=sys.stderr)
        return 1
    d = round(haversine_m(args.from_lat, args.from_lon, args.to_lat, args.to_lon), 1)
    emit({"distance_m": d, "distance_text": format_distance_m(d),
          "from": {"lat": args.from_lat, "lon": args.from_lon},
          "to": {"lat": args.to_lat, "lon": args.to_lon}})
    return 0


def cmd_want(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run: python runtime/fm.py id new --name <handle>", file=sys.stderr)
        return 1
    msg = build_want(
        ident,
        title=args.title,
        budget=args.budget,
        currency=args.currency,
        region=args.region,
        desc=args.desc,
        condition=args.condition,
        qty=args.qty,
        notes=args.notes,
        need_courier=args.need_courier,
        ttl=args.ttl,
        lat=args.lat,
        lon=args.lon,
        radius_m=args.place_radius,
        label=args.label,
        privacy=args.privacy,
    )
    msg["body"] = attach_match(msg["body"], args.vertical, args.mode, args.max_accepts)
    if args.sign:
        msg = sign_message(msg, ident)
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        stored = board.put(msg, force=True)
        emit(stored)
        return 0
    board.put(msg, force=True)
    emit(msg)
    return 0


def cmd_have(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run: python runtime/fm.py id new --name <handle>", file=sys.stderr)
        return 1
    msg = build_have(
        ident,
        title=args.title,
        price=args.price,
        currency=args.currency,
        region=args.region,
        desc=args.desc,
        condition=args.condition,
        stock=args.stock,
        notes=args.notes,
        ttl=args.ttl,
        lat=args.lat,
        lon=args.lon,
        radius_m=args.place_radius,
        label=args.label,
        privacy=args.privacy,
    )
    msg["body"] = attach_match(msg["body"], args.vertical, args.mode, args.max_accepts)
    if args.sign:
        msg = sign_message(msg, ident)
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        stored = board.put(msg, force=True)
        emit(stored)
        return 0
    board.put(msg, force=True)
    emit(msg)
    return 0


def cmd_bid(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "bid",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller"]},
        "thread": args.target,
        "reply_to": args.target,
        "body": {
            "target_id": args.target,
            "price": {"amount": str(args.price), "currency": args.currency},
            "message": args.message,
            "delivery": {"mode": args.delivery} if args.delivery else None,
            "payment": {"methods": [args.pay], "timing": args.pay_timing} if args.pay else None,
        },
        "sig": None,
    }
    board = get_board(args)
    if args.sign:
        msg = sign_message(msg, ident)
    if isinstance(board, RemoteBoard):
        emit(board.put(msg, force=True))
    else:
        emit(board.put(msg, force=True))
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "accept",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller", "courier"]},
        "thread": args.thread or args.bid,
        "reply_to": args.bid,
        "body": {"bid_id": args.bid, "message": args.message},
        "sig": None,
    }
    board = get_board(args)
    if args.sign:
        msg = sign_message(msg, ident)
    emit(board.put(msg, force=True) if not isinstance(board, RemoteBoard) else board.put(msg, force=True))
    return 0


def add_board_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--board", default=None, help="Remote board base URL, e.g. http://127.0.0.1:8787")
    p.add_argument("--board-dir", default=str(DEFAULT_BOARD), help="Local messages dir when not using --board")
    p.add_argument("--ids-dir", default=str(DEFAULT_IDS))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fm", description="free-match CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    idp = sub.add_parser("id")
    idsub = idp.add_subparsers(dest="id_cmd", required=True)
    idn = idsub.add_parser("new")
    idn.add_argument("--name", required=True)
    idn.add_argument("--show-secret", action="store_true")
    idn.add_argument("--ids-dir", default=str(DEFAULT_IDS))
    idn.set_defaults(func=cmd_id_new)
    ids = idsub.add_parser("show")
    ids.add_argument("--ids-dir", default=str(DEFAULT_IDS))
    ids.set_defaults(func=cmd_id_show)

    for name, fn in (
        ("validate", cmd_validate),
    ):
        x = sub.add_parser(name)
        x.add_argument("--file")
        x.add_argument("--stdin", action="store_true")
        x.set_defaults(func=fn)

    post = sub.add_parser("post")
    add_board_args(post)
    post.add_argument("--file")
    post.add_argument("--stdin", action="store_true")
    post.add_argument("--sign", action="store_true")
    post.add_argument("--force", action="store_true")
    post.set_defaults(func=cmd_post)

    lst = sub.add_parser("list")
    add_board_args(lst)
    lst.add_argument("--type", default="want,have")
    lst.add_argument("--q", default="")
    lst.add_argument("--region", default="")
    lst.add_argument("--near-lat", type=float, default=None)
    lst.add_argument("--near-lon", type=float, default=None)
    lst.add_argument("--radius-m", type=float, default=None)
    lst.add_argument("--require-geo", action="store_true")
    lst.add_argument("--sort", default="time", choices=["time", "distance"])
    lst.set_defaults(func=cmd_list)

    getp = sub.add_parser("get")
    add_board_args(getp)
    getp.add_argument("msg_id")
    getp.set_defaults(func=cmd_get)

    dist = sub.add_parser("distance", help="distance between two geos or message ids")
    add_board_args(dist)
    dist.add_argument("--from-id", default=None)
    dist.add_argument("--to-id", default=None)
    dist.add_argument("--from-lat", type=float, default=None)
    dist.add_argument("--from-lon", type=float, default=None)
    dist.add_argument("--to-lat", type=float, default=None)
    dist.add_argument("--to-lon", type=float, default=None)
    dist.set_defaults(func=cmd_distance)

    th = sub.add_parser("thread")
    add_board_args(th)
    th.add_argument("root_id")
    th.set_defaults(func=cmd_thread)

    rs = sub.add_parser("review-summary")
    add_board_args(rs)
    rs.add_argument("actor_id")
    rs.set_defaults(func=cmd_review_summary)

    w = sub.add_parser("want")
    add_board_args(w)
    w.add_argument("--title", required=True)
    w.add_argument("--budget", default=None)
    w.add_argument("--currency", default="CNY")
    w.add_argument("--region", default=None)
    w.add_argument("--lat", type=float, default=None)
    w.add_argument("--lon", type=float, default=None)
    w.add_argument("--place-radius", type=float, default=None, help="service radius_m on the place")
    w.add_argument("--label", default=None)
    w.add_argument("--privacy", default="after_deal", choices=["public", "after_deal", "direct_only"])
    w.add_argument("--desc", default=None)
    w.add_argument("--condition", default=None)
    w.add_argument("--qty", type=float, default=1)
    w.add_argument("--notes", default=None)
    w.add_argument("--need-courier", action="store_true")
    w.add_argument("--ttl", type=int, default=172800)
    w.add_argument("--vertical", default=None, help="goods_unique|goods_stock|food_order|ride|errand|service|bulk_rfq")
    w.add_argument("--mode", default=None, help="one_to_one|one_to_many|many_to_one|many_to_many|broadcast_claim")
    w.add_argument("--max-accepts", type=int, default=None)
    w.add_argument("--sign", action="store_true")
    w.set_defaults(func=cmd_want)

    h = sub.add_parser("have")
    add_board_args(h)
    h.add_argument("--title", required=True)
    h.add_argument("--price", default=None)
    h.add_argument("--currency", default="CNY")
    h.add_argument("--region", default=None)
    h.add_argument("--lat", type=float, default=None)
    h.add_argument("--lon", type=float, default=None)
    h.add_argument("--place-radius", type=float, default=None)
    h.add_argument("--label", default=None)
    h.add_argument("--privacy", default="after_deal", choices=["public", "after_deal", "direct_only"])
    h.add_argument("--desc", default=None)
    h.add_argument("--condition", default=None)
    h.add_argument("--stock", type=float, default=1)
    h.add_argument("--notes", default=None)
    h.add_argument("--ttl", type=int, default=604800)
    h.add_argument("--vertical", default=None)
    h.add_argument("--mode", default=None)
    h.add_argument("--max-accepts", type=int, default=None)
    h.add_argument("--sign", action="store_true")
    h.set_defaults(func=cmd_have)

    b = sub.add_parser("bid")
    add_board_args(b)
    b.add_argument("--target", required=True)
    b.add_argument("--price", required=True)
    b.add_argument("--currency", default="CNY")
    b.add_argument("--message", default=None)
    b.add_argument("--delivery", default=None)
    b.add_argument("--pay", default=None)
    b.add_argument("--pay-timing", default="on_delivery")
    b.add_argument("--sign", action="store_true")
    b.set_defaults(func=cmd_bid)

    a = sub.add_parser("accept")
    add_board_args(a)
    a.add_argument("--bid", required=True)
    a.add_argument("--thread", default=None)
    a.add_argument("--message", default=None)
    a.add_argument("--sign", action="store_true")
    a.set_defaults(func=cmd_accept)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileExistsError as e:
        print(str(e), file=sys.stderr)
        return 1
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
