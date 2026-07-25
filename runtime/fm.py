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
    derive_status,
    load_identity,
    load_json,
    parse_buyer_nl,
    public_identity,
    rank_listings,
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


def cmd_thread(args: argparse.Namespace) -> int:
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        msgs = board.thread(args.root_id)
    else:
        msgs = board.thread(args.root_id)
    emit(msgs)
    return 0


def cmd_review_summary(args: argparse.Namespace) -> int:
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        emit(board.reviews(args.actor_id))
        return 0
    emit(review_summary(board.list_all(), args.actor_id))
    return 0


def cmd_track(args: argparse.Namespace) -> int:
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        res = board._req("GET", f"/api/v1/track/{args.root_id}")
        emit(res.get("status") if args.status_only else res)
        return 0
    msgs = board.thread(args.root_id)
    st = derive_status(msgs)
    if args.status_only:
        emit(st)
    else:
        emit({"root": args.root_id, "status": st, "messages": msgs})
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    filters = parse_buyer_nl(args.nl)
    board = get_board(args)
    types = {t.strip() for t in str(filters.get("type") or "have").split(",") if t.strip()}
    radius = args.radius_m if args.radius_m is not None else filters.get("radius_m")
    kwargs = dict(
        types=types,
        q=filters.get("q") or "",
        region=args.region or "",
        summary=True,
        near_lat=args.near_lat,
        near_lon=args.near_lon,
        radius_m=radius,
        require_geo=False,
        sort="distance" if args.near_lat is not None else "time",
    )
    if isinstance(board, RemoteBoard):
        rows = board.query(**kwargs)
    else:
        rows = board.query(**kwargs)
    ranked = rank_listings(rows, filters)
    emit({"filters": filters, "count": len(ranked), "results": ranked[: args.limit]})
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
    images = []
    if args.image:
        images.extend(args.image)
    if args.image_uri:
        images.extend(args.image_uri)
    # upload local files to remote board media if --board set
    resolved = []
    board = get_board(args)
    for img in images:
        p = Path(img)
        if p.is_file() and isinstance(board, RemoteBoard):
            import base64
            import mimetypes

            raw = p.read_bytes()
            mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            res = board._req(
                "POST",
                "/api/v1/media",
                {
                    "filename": p.name,
                    "mime": mime,
                    "content_base64": base64.b64encode(raw).decode("ascii"),
                },
            )
            resolved.append(res.get("uri") or img)
        else:
            resolved.append(img)
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
        tags=[t.strip() for t in (args.tags or "").split(",") if t.strip()] or None,
        image_uris=resolved or None,
    )
    msg["body"] = attach_match(msg["body"], args.vertical, args.mode, args.max_accepts)
    if args.sign:
        msg = sign_message(msg, ident)
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


def _post_built(args: argparse.Namespace, msg: dict[str, Any]) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    board = get_board(args)
    if getattr(args, "sign", False):
        if not ident:
            print("cannot sign: no identity", file=sys.stderr)
            return 1
        msg = sign_message(msg, ident)
    stored = board.put(msg, force=True)
    emit(stored)
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "reject",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller"]},
        "thread": args.thread or args.bid,
        "reply_to": args.bid,
        "body": {"bid_id": args.bid, "reason": args.reason},
        "sig": None,
    }
    return _post_built(args, msg)


def cmd_deal(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "deal",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller"]},
        "thread": args.thread,
        "body": {
            "parties": {
                "buyer": args.buyer,
                "seller": args.seller,
                "courier": args.courier,
            },
            "item": {"title": args.title, "qty": args.qty, "description": args.desc},
            "price": {"amount": str(args.price), "currency": args.currency},
            "payment": {"methods": [args.pay], "timing": args.pay_timing} if args.pay else None,
            "delivery": {"mode": args.delivery} if args.delivery else None,
            "based_on": [x for x in (args.based_on or "").split(",") if x.strip()],
            "terms": args.terms,
            "match": {
                "mode": args.mode or "one_to_one",
                "vertical": args.vertical,
                "max_accepts": 1,
                "exclusive": True,
            }
            if args.vertical or args.mode
            else None,
        },
        "sig": None,
    }
    # drop null match
    if msg["body"].get("match") and not msg["body"]["match"].get("vertical") and not args.mode:
        msg["body"]["match"] = None
    return _post_built(args, msg)


def cmd_fulfill(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "fulfill",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["seller", "courier"]},
        "thread": args.thread or args.deal,
        "body": {
            "deal_id": args.deal,
            "event": args.event,
            "note": args.note,
            "proof": [{"uri": u} for u in (args.proof or [])] or None,
        },
        "sig": None,
    }
    return _post_built(args, msg)


def cmd_confirm(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "confirm",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller"]},
        "thread": args.thread or args.deal,
        "body": {"deal_id": args.deal, "status": args.status, "note": args.note},
        "sig": None,
    }
    return _post_built(args, msg)


def cmd_review(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "review",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller", "courier"]},
        "body": {
            "subject_id": args.subject,
            "deal_id": args.deal,
            "stars": args.stars,
            "text": args.text,
            "tags": [t.strip() for t in (args.tags or "").split(",") if t.strip()] or None,
        },
        "sig": None,
    }
    return _post_built(args, msg)


def cmd_courier_offer(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "courier.offer",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["courier"]},
        "thread": args.thread or args.target,
        "body": {
            "target_id": args.target,
            "fee": {"amount": str(args.fee), "currency": args.currency},
            "eta": args.eta,
            "vehicle": args.vehicle,
            "message": args.message,
            "match": {
                "mode": args.mode or "one_to_many",
                "vertical": args.vertical or "errand",
                "max_accepts": 1,
            },
            "where": {"geo": {"lat": args.lat, "lon": args.lon}, "region": args.region, "privacy": "public"}
            if args.lat is not None and args.lon is not None
            else ({"region": args.region, "privacy": "public"} if args.region else None),
        },
        "sig": None,
    }
    return _post_built(args, msg)


def cmd_courier_accept(args: argparse.Namespace) -> int:
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    if not ident:
        print("run id new first", file=sys.stderr)
        return 1
    msg = {
        "v": 1,
        "type": "courier.accept",
        "from": {"id": ident["id"], "display": ident.get("display"), "roles": ["buyer", "seller"]},
        "thread": args.thread,
        "reply_to": args.offer,
        "body": {"offer_id": args.offer, "message": args.message},
        "sig": None,
    }
    return _post_built(args, msg)


def cmd_inbox(args: argparse.Namespace) -> int:
    """List open items relevant to me (daily operator view)."""
    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    actor = args.actor or (ident or {}).get("id")
    if not actor:
        print("need identity or --actor", file=sys.stderr)
        return 1
    board = get_board(args)
    if isinstance(board, RemoteBoard):
        rows = board.query(types=None, q="", region="", summary=False, limit=500)
        # remote summary=false still returns messages list via query - need full
        # RemoteBoard.query with summary False still hits API summary flag - fix by list all types
        all_types = "want,have,bid,accept,deal,fulfill,confirm,courier.offer,courier.accept,review"
        rows = board.query(types=set(all_types.split(",")), summary=True, limit=500)
        # for status we need threads - fetch deals/wants/haves and track
        roots = [r for r in rows if r.get("type") in ("want", "have", "deal")]
    else:
        all_m = board.list_all()
        roots = [m for m in all_m if m.get("type") in ("want", "have", "deal")]
        rows = all_m

    out = []
    for r in roots:
        rid = r.get("id")
        # involve me?
        fr = r.get("from") if isinstance(r.get("from"), dict) else {}
        body = r.get("body") or {}
        parties = body.get("parties") or {}
        involved = (
            fr.get("id") == actor
            or parties.get("buyer") == actor
            or parties.get("seller") == actor
            or parties.get("courier") == actor
            or r.get("from") == actor
        )
        if not involved and not args.all:
            # also bids targeting my listings: skip heavy; include if --all
            continue
        if isinstance(board, RemoteBoard):
            st = board._req("GET", f"/api/v1/track/{rid}").get("status") or {}
        else:
            st = derive_status(board.thread(rid))
        status = st.get("status") or "unknown"
        if not args.include_closed and status in ("completed", "cancelled", "complete"):
            continue
        out.append(
            {
                "id": rid,
                "type": r.get("type"),
                "title": (body.get("item") or {}).get("title") or r.get("title"),
                "status": status,
                "label": st.get("label"),
                "from": fr.get("id") or r.get("from"),
                "ts": r.get("ts") or st.get("last_ts"),
            }
        )
    out.sort(key=lambda x: x.get("ts") or "", reverse=True)
    emit({"actor": actor, "count": len(out), "items": out[: args.limit]})
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    import time as _time

    ident = load_identity(Path(args.ids_dir) if args.ids_dir else DEFAULT_IDS)
    actor = args.actor or (ident or {}).get("id")
    if not actor:
        print("need identity or --actor", file=sys.stderr)
        return 1
    board = get_board(args)
    last: dict[str, str] = {}
    print(f"# watching actor={actor} interval={args.interval}s board={getattr(args,'board',None) or 'local'}", file=sys.stderr)
    rounds = 0
    while True:
        # reuse inbox logic lightly
        class NS:
            pass

        ns = argparse.Namespace(
            board=getattr(args, "board", None),
            board_dir=getattr(args, "board_dir", str(DEFAULT_BOARD)),
            ids_dir=getattr(args, "ids_dir", str(DEFAULT_IDS)),
            actor=actor,
            all=False,
            open_only=True,
            limit=50,
        )
        # call internals
        if isinstance(board, RemoteBoard):
            all_types = "want,have,deal"
            roots = board.query(types=set(all_types.split(",")), summary=True, limit=200)
        else:
            roots = [m for m in board.list_all() if m.get("type") in ("want", "have", "deal")]
        changes = []
        for r in roots:
            rid = r.get("id")
            fr = r.get("from") if isinstance(r.get("from"), dict) else {}
            body = r.get("body") or {}
            parties = body.get("parties") or {}
            involved = fr.get("id") == actor or actor in (
                parties.get("buyer"),
                parties.get("seller"),
                parties.get("courier"),
            )
            if not involved:
                continue
            if isinstance(board, RemoteBoard):
                st = (board._req("GET", f"/api/v1/track/{rid}") or {}).get("status") or {}
            else:
                st = derive_status(board.thread(rid))
            key = st.get("status") or "?"
            if last.get(rid) != key:
                if rid in last or args.include_initial:
                    changes.append(
                        {
                            "id": rid,
                            "from_status": last.get(rid),
                            "to_status": key,
                            "label": st.get("label"),
                            "title": (body.get("item") or {}).get("title") or r.get("title"),
                        }
                    )
                last[rid] = key
        if changes:
            emit({"ts": __import__("datetime").datetime.utcnow().isoformat() + "Z", "changes": changes})
        rounds += 1
        if args.once or (args.max_rounds and rounds >= args.max_rounds):
            break
        _time.sleep(max(2, args.interval))
    return 0


def cmd_geocode(args: argparse.Namespace) -> int:
    import json as _json
    import os
    import urllib.parse
    import urllib.request

    base = args.nominatim or os.environ.get("FM_NOMINATIM_URL") or "https://nominatim.openstreetmap.org/search"
    q = urllib.parse.urlencode({"q": args.query, "format": "json", "limit": str(args.limit)})
    url = base.rstrip("/") + ("&" if "?" in base else "?") + q
    # if base already is full search endpoint without query
    if "nominatim" in base and "search" not in base:
        url = base.rstrip("/") + "/search?" + urllib.parse.urlencode(
            {"q": args.query, "format": "json", "limit": str(args.limit)}
        )
    req = urllib.request.Request(url, headers={"User-Agent": "free-match/0.2 (public-interest; local tool)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(json.dumps({"error": str(e), "hint": "set FM_NOMINATIM_URL to self-hosted Nominatim"}, ensure_ascii=False, indent=2))
        return 1
    out = [
        {
            "display": r.get("display_name"),
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "type": r.get("type"),
        }
        for r in (data or [])
        if r.get("lat") and r.get("lon")
    ]
    emit({"query": args.query, "results": out})
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

    tr = sub.add_parser("track", help="order/thread status timeline")
    add_board_args(tr)
    tr.add_argument("root_id")
    tr.add_argument("--status-only", action="store_true")
    tr.set_defaults(func=cmd_track)

    se = sub.add_parser("search", help="buyer NL → filters + ranked listings")
    add_board_args(se)
    se.add_argument("--nl", required=True, help='e.g. "vegan lunch under 12 EUR within 2 km"')
    se.add_argument("--near-lat", type=float, default=None)
    se.add_argument("--near-lon", type=float, default=None)
    se.add_argument("--radius-m", type=float, default=None)
    se.add_argument("--region", default="")
    se.add_argument("--limit", type=int, default=20)
    se.set_defaults(func=cmd_search)

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
    h.add_argument("--tags", default=None, help="comma tags e.g. vegan,lunch")
    h.add_argument("--image", action="append", default=[], help="local image path (upload if --board)")
    h.add_argument("--image-uri", action="append", default=[], help="existing image URL")
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

    rj = sub.add_parser("reject")
    add_board_args(rj)
    rj.add_argument("--bid", required=True)
    rj.add_argument("--thread", default=None)
    rj.add_argument("--reason", default=None)
    rj.add_argument("--sign", action="store_true")
    rj.set_defaults(func=cmd_reject)

    dl = sub.add_parser("deal", help="lock a deal snapshot")
    add_board_args(dl)
    dl.add_argument("--buyer", required=True)
    dl.add_argument("--seller", required=True)
    dl.add_argument("--courier", default=None)
    dl.add_argument("--title", required=True)
    dl.add_argument("--price", required=True)
    dl.add_argument("--currency", default="EUR")
    dl.add_argument("--qty", type=float, default=1)
    dl.add_argument("--desc", default=None)
    dl.add_argument("--thread", default=None)
    dl.add_argument("--based-on", default="")
    dl.add_argument("--delivery", default=None)
    dl.add_argument("--pay", default=None)
    dl.add_argument("--pay-timing", default="on_delivery")
    dl.add_argument("--terms", default=None)
    dl.add_argument("--vertical", default=None)
    dl.add_argument("--mode", default="one_to_one")
    dl.add_argument("--sign", action="store_true")
    dl.set_defaults(func=cmd_deal)

    fu = sub.add_parser("fulfill")
    add_board_args(fu)
    fu.add_argument("--deal", required=True)
    fu.add_argument("--event", required=True, help="shipped|picked_up|in_transit|delivered|service_done|...")
    fu.add_argument("--note", default=None)
    fu.add_argument("--thread", default=None)
    fu.add_argument("--proof", action="append", default=[])
    fu.add_argument("--sign", action="store_true")
    fu.set_defaults(func=cmd_fulfill)

    cf = sub.add_parser("confirm")
    add_board_args(cf)
    cf.add_argument("--deal", required=True)
    cf.add_argument("--status", required=True, choices=["received", "paid", "complete", "disputed", "cancelled"])
    cf.add_argument("--note", default=None)
    cf.add_argument("--thread", default=None)
    cf.add_argument("--sign", action="store_true")
    cf.set_defaults(func=cmd_confirm)

    rv = sub.add_parser("review")
    add_board_args(rv)
    rv.add_argument("--subject", required=True)
    rv.add_argument("--deal", required=True)
    rv.add_argument("--stars", type=int, required=True)
    rv.add_argument("--text", default=None)
    rv.add_argument("--tags", default=None)
    rv.add_argument("--sign", action="store_true")
    rv.set_defaults(func=cmd_review)

    co = sub.add_parser("courier-offer")
    add_board_args(co)
    co.add_argument("--target", required=True)
    co.add_argument("--fee", required=True)
    co.add_argument("--currency", default="EUR")
    co.add_argument("--eta", default=None)
    co.add_argument("--vehicle", default=None)
    co.add_argument("--message", default=None)
    co.add_argument("--thread", default=None)
    co.add_argument("--vertical", default=None)
    co.add_argument("--mode", default=None)
    co.add_argument("--lat", type=float, default=None)
    co.add_argument("--lon", type=float, default=None)
    co.add_argument("--region", default=None)
    co.add_argument("--sign", action="store_true")
    co.set_defaults(func=cmd_courier_offer)

    ca = sub.add_parser("courier-accept")
    add_board_args(ca)
    ca.add_argument("--offer", required=True)
    ca.add_argument("--thread", default=None)
    ca.add_argument("--message", default=None)
    ca.add_argument("--sign", action="store_true")
    ca.set_defaults(func=cmd_courier_accept)

    ib = sub.add_parser("inbox", help="my open listings/deals with status")
    add_board_args(ib)
    ib.add_argument("--actor", default=None)
    ib.add_argument("--all", action="store_true", help="all roots, not only mine")
    ib.add_argument("--include-closed", action="store_true")
    ib.add_argument("--limit", type=int, default=50)
    ib.set_defaults(func=cmd_inbox)

    wa = sub.add_parser("watch", help="poll status changes for my threads")
    add_board_args(wa)
    wa.add_argument("--actor", default=None)
    wa.add_argument("--interval", type=int, default=15)
    wa.add_argument("--once", action="store_true")
    wa.add_argument("--max-rounds", type=int, default=0)
    wa.add_argument("--include-initial", action="store_true")
    wa.set_defaults(func=cmd_watch)

    geo = sub.add_parser("geocode", help="free Nominatim geocode (respect usage policy / self-host)")
    geo.add_argument("query")
    geo.add_argument("--nominatim", default=None, help="override FM_NOMINATIM_URL")
    geo.add_argument("--limit", type=int, default=5)
    geo.set_defaults(func=cmd_geocode)

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
