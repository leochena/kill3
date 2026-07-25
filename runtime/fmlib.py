#!/usr/bin/env python3
"""Shared free-match library: validation, board store, identity. No platform rent/police."""

from __future__ import annotations

import base64
import hashlib
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parent
DEFAULT_BOARD = RUNTIME / "board" / "messages"
DEFAULT_IDS = RUNTIME / "board" / "identities"

REQUIRED_ENVELOPE = ("v", "id", "type", "ts", "from", "body")
KNOWN_TYPES = {
    "identity.announce",
    "want",
    "have",
    "bid",
    "accept",
    "reject",
    "deal",
    "fulfill",
    "confirm",
    "review",
    "courier.offer",
    "courier.accept",
    "ping",
    "board.list",
}
FORBIDDEN_FIELDS = (
    "platform_fee",
    "commission",
    "service_charge",
    "take_rate",
    "kyc_level",
    "compliance_status",
    "risk_score",
    "ban_reason",
    "content_policy",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id() -> str:
    return f"fm{int(time.time() * 1000):x}{uuid.uuid4().hex[:10]}"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    tmp.replace(path)


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def try_import_nacl():
    try:
        from nacl.signing import SigningKey, VerifyKey  # type: ignore

        return SigningKey, VerifyKey
    except Exception:
        return None, None


def validate_envelope(msg: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(msg, dict):
        return ["message must be object"]
    for k in REQUIRED_ENVELOPE:
        if k not in msg:
            errors.append(f"missing field: {k}")
    if msg.get("v") != 1:
        errors.append("v must be 1")
    t = msg.get("type")
    if t not in KNOWN_TYPES:
        errors.append(f"unknown type: {t}")
    fr = msg.get("from")
    if not isinstance(fr, dict) or not fr.get("id"):
        errors.append("from.id required")
    body = msg.get("body")
    if not isinstance(body, dict):
        errors.append("body must be object")
    else:
        if t == "want" and "item" not in body:
            errors.append("want.body.item required")
        if t == "have" and "item" not in body:
            errors.append("have.body.item required")
        if t == "bid" and ("target_id" not in body or "price" not in body):
            errors.append("bid.body needs target_id and price")
        if t == "accept" and "bid_id" not in body:
            errors.append("accept.body.bid_id required")
        if t == "reject" and "bid_id" not in body:
            errors.append("reject.body.bid_id required")
        if t == "deal" and not all(k in body for k in ("parties", "item", "price")):
            errors.append("deal.body needs parties, item, price")
        if t == "fulfill" and not all(k in body for k in ("deal_id", "event")):
            errors.append("fulfill.body needs deal_id, event")
        if t == "confirm" and not all(k in body for k in ("deal_id", "status")):
            errors.append("confirm.body needs deal_id, status")
        if t == "review":
            if not all(k in body for k in ("subject_id", "deal_id", "stars")):
                errors.append("review.body needs subject_id, deal_id, stars")
            else:
                try:
                    stars = int(body["stars"])
                    if stars < 1 or stars > 5:
                        errors.append("review.stars must be 1..5")
                except Exception:
                    errors.append("review.stars must be int 1..5")
        if t == "courier.offer" and not all(k in body for k in ("target_id", "fee")):
            errors.append("courier.offer needs target_id, fee")
        if t == "courier.accept" and "offer_id" not in body:
            errors.append("courier.accept needs offer_id")
        if t in ("want", "have"):
            item = body.get("item")
            if isinstance(item, dict) and not item.get("title"):
                errors.append(f"{t}.body.item.title required")
    blob = json.dumps(msg, ensure_ascii=False)
    for f in FORBIDDEN_FIELDS:
        if f'"{f}"' in blob:
            errors.append(f"forbidden field present: {f} (no platform rent/police fields)")
    return errors


def normalize_message(msg: dict[str, Any], default_from: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(msg)
    if not out.get("id"):
        out["id"] = new_id()
    if not out.get("ts"):
        out["ts"] = utc_now()
    if not out.get("v"):
        out["v"] = 1
    if not out.get("from") and default_from:
        out["from"] = default_from
    if "sig" not in out:
        out["sig"] = None
    return out


def sign_message(msg: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    SigningKey, _ = try_import_nacl()
    if not identity.get("privkey") or SigningKey is None:
        return msg
    sk = SigningKey(base64.b64decode(identity["privkey"]))
    unsigned = {k: v for k, v in msg.items() if k != "sig"}
    sig = sk.sign(canonical_bytes(unsigned)).signature
    out = dict(msg)
    out["sig"] = base64.b64encode(sig).decode("ascii")
    return out


def create_identity(name: str, ids_dir: Path | None = None) -> dict[str, Any]:
    ids_dir = ids_dir or DEFAULT_IDS
    ids_dir.mkdir(parents=True, exist_ok=True)
    SigningKey, _ = try_import_nacl()
    if SigningKey is None:
        seed = uuid.uuid4().hex
        actor_id = "local_" + hashlib.sha256(seed.encode()).hexdigest()[:16]
        doc = {
            "id": actor_id,
            "display": name,
            "algo": None,
            "pubkey": None,
            "privkey": None,
            "note": "PyNaCl not installed; unsigned local identity. pip install pynacl for ed25519.",
            "created": utc_now(),
        }
    else:
        sk = SigningKey.generate()
        vk = sk.verify_key
        pub = base64.b64encode(bytes(vk)).decode("ascii")
        priv = base64.b64encode(bytes(sk)).decode("ascii")
        actor_id = "ed25519:" + hashlib.sha256(bytes(vk)).hexdigest()[:16]
        doc = {
            "id": actor_id,
            "display": name,
            "algo": "ed25519",
            "pubkey": pub,
            "privkey": priv,
            "created": utc_now(),
        }
    write_json(ids_dir / "default.json", doc)
    return doc


def load_identity(ids_dir: Path | None = None, name: str = "default") -> dict[str, Any] | None:
    ids_dir = ids_dir or DEFAULT_IDS
    path = ids_dir / f"{name}.json"
    if not path.exists():
        return None
    return load_json(path)


def public_identity(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k != "privkey"}


def summarize_row(m: dict[str, Any]) -> dict[str, Any]:
    body = m.get("body") or {}
    item = body.get("item") or {}
    where = body.get("where") or {}
    reg = (where.get("region") or "") if isinstance(where, dict) else ""
    match = body.get("match") if isinstance(body.get("match"), dict) else {}
    return {
        "id": m.get("id"),
        "type": m.get("type"),
        "from": (m.get("from") or {}).get("id"),
        "display": (m.get("from") or {}).get("display"),
        "title": item.get("title") or "",
        "price": body.get("price") or body.get("budget") or body.get("fee"),
        "region": reg,
        "ts": m.get("ts"),
        "thread": m.get("thread"),
        "ttl_sec": m.get("ttl_sec"),
        "match_mode": match.get("mode"),
        "vertical": match.get("vertical"),
        "body": {"match": match} if match else {},
    }


def match_filters(
    m: dict[str, Any],
    types: set[str] | None = None,
    q: str = "",
    region: str = "",
) -> bool:
    if types and m.get("type") not in types:
        return False
    body = m.get("body") or {}
    where = body.get("where") or {}
    reg = (where.get("region") or "") if isinstance(where, dict) else ""
    if region and region.lower() not in reg.lower():
        return False
    if q and q.lower() not in json.dumps(m, ensure_ascii=False).lower():
        return False
    return True


def thread_related(m: dict[str, Any], root: str) -> bool:
    if m.get("id") == root or m.get("thread") == root or m.get("reply_to") == root:
        return True
    body = m.get("body") or {}
    for key in ("target_id", "deal_id", "bid_id", "offer_id"):
        if body.get(key) == root:
            return True
    based = body.get("based_on") or []
    if isinstance(based, list) and root in based:
        return True
    return False


def review_summary(messages: list[dict[str, Any]], actor_id: str) -> dict[str, Any]:
    reviews = [
        m
        for m in messages
        if m.get("type") == "review" and (m.get("body") or {}).get("subject_id") == actor_id
    ]
    if not reviews:
        return {"actor_id": actor_id, "count": 0, "avg": None, "reviews": []}
    stars = [int((m.get("body") or {}).get("stars") or 0) for m in reviews]
    avg = sum(stars) / len(stars) if stars else None
    return {
        "actor_id": actor_id,
        "count": len(reviews),
        "avg": round(avg, 3) if avg is not None else None,
        "reviews": [
            {
                "id": m.get("id"),
                "from": (m.get("from") or {}).get("id"),
                "stars": (m.get("body") or {}).get("stars"),
                "text": (m.get("body") or {}).get("text"),
                "deal_id": (m.get("body") or {}).get("deal_id"),
                "ts": m.get("ts"),
            }
            for m in reviews
        ],
    }


class BoardStore:
    """Thread-safe file-backed message board. Dumb pipe — no ranking ads, no fees."""

    def __init__(self, messages_dir: Path | None = None):
        self.messages_dir = Path(messages_dir or DEFAULT_BOARD)
        self.messages_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def path_for(self, msg_id: str) -> Path:
        # prevent path traversal
        safe = "".join(c for c in msg_id if c.isalnum() or c in ("-", "_", ".", ":"))
        if not safe or safe != msg_id:
            # still allow common id chars; if stripped differs, reject later
            safe = hashlib.sha256(msg_id.encode()).hexdigest()
        return self.messages_dir / f"{safe}.json"

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            out: list[dict[str, Any]] = []
            for p in sorted(self.messages_dir.glob("*.json")):
                try:
                    out.append(load_json(p))
                except Exception:
                    continue
            return out

    def get(self, msg_id: str) -> dict[str, Any] | None:
        with self._lock:
            p = self.messages_dir / f"{msg_id}.json"
            if not p.exists():
                # try hashed name
                p2 = self.path_for(msg_id)
                if p2.exists() and p2 != p:
                    return load_json(p2)
                return None
            return load_json(p)

    def put(self, msg: dict[str, Any], force: bool = False) -> dict[str, Any]:
        msg = normalize_message(msg)
        errs = validate_envelope(msg)
        if errs:
            raise ValueError("; ".join(errs))
        with self._lock:
            path = self.messages_dir / f"{msg['id']}.json"
            if path.exists() and not force:
                existing = load_json(path)
                if existing == msg:
                    return msg
                raise FileExistsError(f"message id already exists: {msg['id']}")
            write_json(path, msg)
            return msg

    def query(
        self,
        types: set[str] | None = None,
        q: str = "",
        region: str = "",
        limit: int = 200,
        offset: int = 0,
        summary: bool = False,
    ) -> list[dict[str, Any]]:
        rows = [m for m in self.list_all() if match_filters(m, types, q, region)]
        rows.sort(key=lambda m: m.get("ts") or "", reverse=True)
        sliced = rows[offset : offset + max(1, min(limit, 1000))]
        if summary:
            return [summarize_row(m) for m in sliced]
        return sliced

    def thread(self, root_id: str) -> list[dict[str, Any]]:
        msgs = [m for m in self.list_all() if thread_related(m, root_id)]
        msgs.sort(key=lambda x: x.get("ts") or "")
        return msgs

    def stats(self) -> dict[str, Any]:
        all_m = self.list_all()
        by_type: dict[str, int] = {}
        for m in all_m:
            t = str(m.get("type") or "?")
            by_type[t] = by_type.get(t, 0) + 1
        return {"count": len(all_m), "by_type": by_type, "board": str(self.messages_dir)}


def build_want(
    identity: dict[str, Any],
    title: str,
    budget: str | None = None,
    currency: str = "CNY",
    region: str | None = None,
    desc: str | None = None,
    condition: str | None = None,
    qty: float = 1,
    notes: str | None = None,
    need_courier: bool = False,
    ttl: int = 172800,
) -> dict[str, Any]:
    return {
        "v": 1,
        "id": new_id(),
        "type": "want",
        "ts": utc_now(),
        "from": {"id": identity["id"], "display": identity.get("display"), "roles": ["buyer"]},
        "ttl_sec": ttl,
        "body": {
            "item": {"title": title, "description": desc, "condition": condition, "qty": qty},
            "budget": {"amount": str(budget), "currency": currency} if budget is not None else None,
            "where": {"region": region} if region else None,
            "need_courier": need_courier,
            "notes": notes,
        },
        "sig": None,
    }


def build_have(
    identity: dict[str, Any],
    title: str,
    price: str | None = None,
    currency: str = "CNY",
    region: str | None = None,
    desc: str | None = None,
    condition: str | None = None,
    stock: float = 1,
    notes: str | None = None,
    ttl: int = 604800,
) -> dict[str, Any]:
    return {
        "v": 1,
        "id": new_id(),
        "type": "have",
        "ts": utc_now(),
        "from": {"id": identity["id"], "display": identity.get("display"), "roles": ["seller"]},
        "ttl_sec": ttl,
        "body": {
            "item": {"title": title, "description": desc, "condition": condition},
            "price": {"amount": str(price), "currency": currency} if price is not None else None,
            "where": {"region": region} if region else None,
            "stock": stock,
            "notes": notes,
        },
        "sig": None,
    }
