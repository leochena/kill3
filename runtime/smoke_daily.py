#!/usr/bin/env python3
"""Daily-use acceptance smoke for all verticals (goods, food, ride, errand, service, bulk_rfq)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from fmlib import create_identity, new_id, parse_buyer_nl, utc_now, validate_envelope  # noqa: E402


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 15.0):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post(base: str, msg: dict) -> dict:
    errs = validate_envelope(msg)
    if errs:
        raise AssertionError(errs)
    res = http_json("POST", base + "/api/v1/messages?force=1", msg)
    return res.get("message") or msg


def env(actor: dict, typ: str, body: dict, **extra) -> dict:
    m = {
        "v": 1,
        "id": new_id(),
        "type": typ,
        "ts": utc_now(),
        "from": {"id": actor["id"], "display": actor.get("display"), "roles": actor.get("roles") or []},
        "body": body,
        "sig": None,
    }
    m.update(extra)
    return m


def actor(name: str, roles: list[str], root: Path) -> dict:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    doc = create_identity(name, d)
    return {"id": doc["id"], "display": name, "roles": roles}


def wait_health(base: str, seconds: float = 15.0) -> None:
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        try:
            h = http_json("GET", base + "/health")
            if h.get("ok"):
                return
            last = h
        except Exception as e:
            last = str(e)
        time.sleep(0.15)
    raise RuntimeError(f"unhealthy: {last}")


def track(base: str, rid: str) -> dict:
    return http_json("GET", base + f"/api/v1/track/{rid}")["status"]


def run_goods(base: str, tmp: Path) -> dict:
    seller = actor("g_seller", ["seller"], tmp)
    buyer = actor("g_buyer", ["buyer"], tmp)
    have = env(
        seller,
        "have",
        {
            "item": {
                "title": "Used bike",
                "description": "City bike, good brakes",
                "condition": "used",
                "tags": ["bike", "used"],
                "attachments": [
                    {"uri": "https://picsum.photos/seed/bike/200/200.jpg", "mime": "image/jpeg"}
                ],
            },
            "price": {"amount": "120", "currency": "EUR"},
            "where": {"region": "Berlin", "geo": {"lat": 52.52, "lon": 13.405}, "privacy": "public"},
            "stock": 1,
            "match": {"mode": "one_to_many", "vertical": "goods_unique", "max_accepts": 1, "exclusive": True},
        },
    )
    post(base, have)
    bid = env(
        buyer,
        "bid",
        {"target_id": have["id"], "price": {"amount": "100", "currency": "EUR"}, "message": "100 cash"},
        thread=have["id"],
        reply_to=have["id"],
    )
    post(base, bid)
    acc = env(seller, "accept", {"bid_id": bid["id"]}, thread=have["id"], reply_to=bid["id"])
    post(base, acc)
    deal = env(
        seller,
        "deal",
        {
            "parties": {"buyer": buyer["id"], "seller": seller["id"], "courier": None},
            "item": {"title": "Used bike", "qty": 1},
            "price": {"amount": "100", "currency": "EUR"},
            "based_on": [have["id"], bid["id"], acc["id"]],
            "match": {"mode": "one_to_one", "vertical": "goods_unique"},
            "delivery": {"mode": "meetup"},
        },
        thread=have["id"],
    )
    post(base, deal)
    post(base, env(seller, "fulfill", {"deal_id": deal["id"], "event": "delivered", "note": "handed over"}))
    post(base, env(buyer, "confirm", {"deal_id": deal["id"], "status": "complete"}))
    post(
        base,
        env(buyer, "review", {"subject_id": seller["id"], "deal_id": deal["id"], "stars": 5, "text": "good"}),
    )
    st = track(base, deal["id"])
    assert st["status"] in ("complete", "completed") or st["label"] == "Completed", st
    # NL search finds listing text still on board
    rows = http_json(
        "GET",
        base
        + "/api/v1/messages?type=have&summary=1&q=bike&near_lat=52.52&near_lon=13.405&radius_m=5000&sort=distance",
    )
    assert any(m.get("image_count", 0) >= 1 for m in rows.get("messages") or []), rows
    return {"vertical": "goods_unique", "deal": deal["id"], "status": st["status"], "nl_filters": parse_buyer_nl("used bike under 150 EUR within 5 km")}


def run_food(base: str, tmp: Path) -> dict:
    kitchen = actor("kitchen", ["seller"], tmp)
    diner = actor("diner", ["buyer"], tmp)
    rider = actor("rider", ["courier"], tmp)
    have = env(
        kitchen,
        "have",
        {
            "item": {
                "title": "Vegan bowl",
                "description": "quinoa vegan",
                "tags": ["vegan", "food"],
                "attachments": [{"uri": "https://picsum.photos/seed/bowl/200/200.jpg", "mime": "image/jpeg"}],
            },
            "price": {"amount": "11", "currency": "EUR"},
            "where": {"region": "Lisbon", "geo": {"lat": 38.71, "lon": -9.14}, "privacy": "public"},
            "match": {"mode": "one_to_many", "vertical": "food_order", "max_accepts": 1},
        },
    )
    post(base, have)
    bid = env(
        diner,
        "bid",
        {
            "target_id": have["id"],
            "price": {"amount": "11", "currency": "EUR"},
            "delivery": {"mode": "courier"},
        },
        thread=have["id"],
    )
    post(base, bid)
    acc = env(kitchen, "accept", {"bid_id": bid["id"]}, thread=have["id"])
    post(base, acc)
    meal = env(
        kitchen,
        "deal",
        {
            "parties": {"buyer": diner["id"], "seller": kitchen["id"], "courier": None},
            "item": {"title": "Vegan bowl"},
            "price": {"amount": "11", "currency": "EUR"},
            "delivery": {"mode": "courier"},
            "based_on": [have["id"], bid["id"], acc["id"]],
            "match": {"mode": "one_to_one", "vertical": "food_order"},
        },
        thread=have["id"],
    )
    post(base, meal)
    assert track(base, meal["id"])["status"] == "awaiting_courier"
    offer = env(
        rider,
        "courier.offer",
        {
            "target_id": meal["id"],
            "fee": {"amount": "3", "currency": "EUR"},
            "eta": "20m",
            "match": {"mode": "one_to_many", "vertical": "food_order"},
        },
    )
    post(base, offer)
    post(base, env(diner, "courier.accept", {"offer_id": offer["id"]}, thread=have["id"]))
    post(base, env(rider, "fulfill", {"deal_id": meal["id"], "event": "picked_up"}))
    post(base, env(rider, "fulfill", {"deal_id": meal["id"], "event": "delivered"}))
    post(base, env(diner, "confirm", {"deal_id": meal["id"], "status": "complete"}))
    post(base, env(diner, "review", {"subject_id": kitchen["id"], "deal_id": meal["id"], "stars": 5}))
    post(base, env(diner, "review", {"subject_id": rider["id"], "deal_id": meal["id"], "stars": 5}))
    st = track(base, meal["id"])
    return {"vertical": "food_order", "deal": meal["id"], "status": st["status"], "courier_fee_separate": True}


def run_ride(base: str, tmp: Path) -> dict:
    pax = actor("pax", ["buyer"], tmp)
    drv = actor("drv", ["courier"], tmp)
    want = env(
        pax,
        "want",
        {
            "item": {"title": "Airport run A→B", "tags": ["ride"], "description": "2 bags"},
            "budget": {"amount": "40", "currency": "EUR"},
            "where": {"region": "City", "geo": {"lat": 52.5, "lon": 13.4}, "privacy": "public"},
            "need_courier": True,
            "match": {"mode": "one_to_many", "vertical": "ride", "max_accepts": 1, "exclusive": True},
        },
    )
    post(base, want)
    offer = env(
        drv,
        "courier.offer",
        {
            "target_id": want["id"],
            "fee": {"amount": "35", "currency": "EUR"},
            "eta": "5m",
            "vehicle": "sedan",
            "match": {"mode": "one_to_many", "vertical": "ride"},
        },
        thread=want["id"],
    )
    post(base, offer)
    post(base, env(pax, "courier.accept", {"offer_id": offer["id"]}, thread=want["id"]))
    deal = env(
        pax,
        "deal",
        {
            "parties": {"buyer": pax["id"], "seller": drv["id"], "courier": drv["id"]},
            "item": {"title": "Airport run A→B"},
            "price": {"amount": "35", "currency": "EUR"},
            "based_on": [want["id"], offer["id"]],
            "match": {"mode": "one_to_one", "vertical": "ride"},
            "delivery": {"mode": "courier"},
        },
        thread=want["id"],
    )
    post(base, deal)
    post(base, env(drv, "fulfill", {"deal_id": deal["id"], "event": "picked_up"}))
    post(base, env(drv, "fulfill", {"deal_id": deal["id"], "event": "delivered"}))
    post(base, env(pax, "confirm", {"deal_id": deal["id"], "status": "complete"}))
    post(base, env(pax, "review", {"subject_id": drv["id"], "deal_id": deal["id"], "stars": 5}))
    return {"vertical": "ride", "deal": deal["id"], "status": track(base, deal["id"])["status"]}


def run_errand(base: str, tmp: Path) -> dict:
    buyer = actor("err_b", ["buyer"], tmp)
    cour = actor("err_c", ["courier"], tmp)
    want = env(
        buyer,
        "want",
        {
            "item": {"title": "Pharmacy pickup", "description": "Collect package", "tags": ["errand"]},
            "budget": {"amount": "15", "currency": "EUR"},
            "where": {"region": "Center", "geo": {"lat": 48.85, "lon": 2.35}, "privacy": "public"},
            "need_courier": True,
            "match": {"mode": "one_to_many", "vertical": "errand", "max_accepts": 1},
        },
    )
    post(base, want)
    offer = env(
        cour,
        "courier.offer",
        {"target_id": want["id"], "fee": {"amount": "12", "currency": "EUR"}, "eta": "30m",
         "match": {"mode": "one_to_many", "vertical": "errand"}},
        thread=want["id"],
    )
    post(base, offer)
    post(base, env(buyer, "courier.accept", {"offer_id": offer["id"]}, thread=want["id"]))
    deal = env(
        buyer,
        "deal",
        {
            "parties": {"buyer": buyer["id"], "seller": cour["id"], "courier": cour["id"]},
            "item": {"title": "Pharmacy pickup"},
            "price": {"amount": "12", "currency": "EUR"},
            "based_on": [want["id"], offer["id"]],
            "match": {"mode": "one_to_one", "vertical": "errand"},
        },
        thread=want["id"],
    )
    post(base, deal)
    post(base, env(cour, "fulfill", {"deal_id": deal["id"], "event": "picked_up"}))
    post(base, env(cour, "fulfill", {"deal_id": deal["id"], "event": "delivered"}))
    post(base, env(buyer, "confirm", {"deal_id": deal["id"], "status": "complete"}))
    return {"vertical": "errand", "deal": deal["id"], "status": track(base, deal["id"])["status"]}


def run_service(base: str, tmp: Path) -> dict:
    seller = actor("svc_s", ["seller"], tmp)
    buyer = actor("svc_b", ["buyer"], tmp)
    have = env(
        seller,
        "have",
        {
            "item": {"title": "Laptop repair", "description": "screen replacement", "tags": ["service", "repair"]},
            "price": {"amount": "80", "currency": "EUR"},
            "where": {"region": "Town", "privacy": "public"},
            "match": {"mode": "one_to_many", "vertical": "service", "max_accepts": 1},
        },
    )
    post(base, have)
    bid = env(buyer, "bid", {"target_id": have["id"], "price": {"amount": "75", "currency": "EUR"}}, thread=have["id"])
    post(base, bid)
    post(base, env(seller, "accept", {"bid_id": bid["id"]}, thread=have["id"]))
    deal = env(
        seller,
        "deal",
        {
            "parties": {"buyer": buyer["id"], "seller": seller["id"]},
            "item": {"title": "Laptop repair"},
            "price": {"amount": "75", "currency": "EUR"},
            "based_on": [have["id"], bid["id"]],
            "match": {"mode": "one_to_one", "vertical": "service"},
        },
        thread=have["id"],
    )
    post(base, deal)
    post(base, env(seller, "fulfill", {"deal_id": deal["id"], "event": "service_done"}))
    post(base, env(buyer, "confirm", {"deal_id": deal["id"], "status": "complete"}))
    post(base, env(buyer, "review", {"subject_id": seller["id"], "deal_id": deal["id"], "stars": 5}))
    return {"vertical": "service", "deal": deal["id"], "status": track(base, deal["id"])["status"]}


def run_rfq(base: str, tmp: Path) -> dict:
    buyer = actor("rfq_b", ["buyer"], tmp)
    s1 = actor("rfq_s1", ["seller"], tmp)
    s2 = actor("rfq_s2", ["seller"], tmp)
    want = env(
        buyer,
        "want",
        {
            "item": {"title": "100 cotton tote bags", "tags": ["bulk"], "qty": 100},
            "budget": {"amount": "500", "currency": "USD"},
            "match": {"mode": "one_to_many", "vertical": "bulk_rfq", "max_accepts": 1},
            "notes": "quote with shipping",
        },
    )
    post(base, want)
    b1 = env(s1, "bid", {"target_id": want["id"], "price": {"amount": "480", "currency": "USD"}}, thread=want["id"])
    b2 = env(s2, "bid", {"target_id": want["id"], "price": {"amount": "450", "currency": "USD"}}, thread=want["id"])
    post(base, b1)
    post(base, b2)
    post(base, env(buyer, "accept", {"bid_id": b2["id"]}, thread=want["id"]))
    deal = env(
        buyer,
        "deal",
        {
            "parties": {"buyer": buyer["id"], "seller": s2["id"]},
            "item": {"title": "100 cotton tote bags", "qty": 100},
            "price": {"amount": "450", "currency": "USD"},
            "based_on": [want["id"], b2["id"]],
            "match": {"mode": "one_to_one", "vertical": "bulk_rfq"},
        },
        thread=want["id"],
    )
    post(base, deal)
    post(base, env(s2, "fulfill", {"deal_id": deal["id"], "event": "shipped"}))
    post(base, env(s2, "fulfill", {"deal_id": deal["id"], "event": "delivered"}))
    post(base, env(buyer, "confirm", {"deal_id": deal["id"], "status": "complete"}))
    return {"vertical": "bulk_rfq", "deal": deal["id"], "bids": 2, "status": track(base, deal["id"])["status"]}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    port = 19201
    board_dir = Path(tempfile.mkdtemp(prefix="fm_daily_"))
    media_dir = Path(tempfile.mkdtemp(prefix="fm_daily_media_"))
    tmp = Path(tempfile.mkdtemp(prefix="fm_daily_ids_"))
    proc = subprocess.Popen(
        [
            sys.executable,
            str(RUNTIME / "server.py"),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--board-dir",
            str(board_dir),
            "--media-dir",
            str(media_dir),
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        wait_health(base)
        # media upload
        import base64

        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16).decode()
        med = http_json(
            "POST",
            base + "/api/v1/media",
            {"filename": "x.png", "mime": "image/png", "content_base64": png},
        )
        assert med.get("uri", "").startswith("/media/")

        # fee blocked
        try:
            http_json(
                "POST",
                base + "/api/v1/messages",
                {
                    "v": 1,
                    "id": new_id(),
                    "type": "want",
                    "ts": utc_now(),
                    "from": {"id": "x"},
                    "body": {"item": {"title": "t"}, "boost": 1},
                },
            )
            fee_ok = False
        except urllib.error.HTTPError as e:
            fee_ok = e.code == 400

        results = {
            "goods_unique": run_goods(base, tmp),
            "food_order": run_food(base, tmp),
            "ride": run_ride(base, tmp),
            "errand": run_errand(base, tmp),
            "service": run_service(base, tmp),
            "bulk_rfq": run_rfq(base, tmp),
            "media_upload": med.get("uri"),
            "paid_boost_blocked": fee_ok,
            "config": http_json("GET", base + "/api/v1/config"),
            "health": http_json("GET", base + "/health"),
        }
        # all terminal statuses ok-ish
        for k, v in list(results.items()):
            if isinstance(v, dict) and "status" in v:
                assert v["status"] in ("complete", "completed", "delivered") or "Complete" in str(
                    v.get("label", "")
                ), (k, v)

        print(json.dumps({"ok": True, "daily_use": True, "results": results}, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2))
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(board_dir, ignore_errors=True)
        shutil.rmtree(media_dir, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
