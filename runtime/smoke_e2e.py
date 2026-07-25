#!/usr/bin/env python3
"""End-to-end multi-peer smoke: 闲置 1:N, 外卖+快递, 打车抢单. Against local or --board URL."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parent
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

from fmlib import BoardStore, create_identity, new_id, utc_now, validate_envelope  # noqa: E402


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 10.0):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def post(board_url: str | None, store: BoardStore | None, msg: dict) -> dict:
    errs = validate_envelope(msg)
    if errs:
        raise AssertionError(f"invalid msg {msg.get('type')}: {errs}")
    if board_url:
        res = http_json("POST", board_url.rstrip("/") + "/api/v1/messages?force=1", msg)
        return res.get("message") or msg
    assert store is not None
    return store.put(msg, force=True)


def actor(name: str, ids_root: Path, roles: list[str]) -> dict:
    d = ids_root / name
    d.mkdir(parents=True, exist_ok=True)
    doc = create_identity(name, d)
    return {
        "id": doc["id"],
        "display": name,
        "roles": roles,
        "_doc": doc,
        "_ids": d,
    }


def env(from_actor: dict, typ: str, body: dict, **extra) -> dict:
    msg = {
        "v": 1,
        "id": new_id(),
        "type": typ,
        "ts": utc_now(),
        "from": {"id": from_actor["id"], "display": from_actor["display"], "roles": from_actor["roles"]},
        "body": body,
        "sig": None,
    }
    msg.update(extra)
    return msg


def scenario_goods(board_url, store) -> dict:
    """闲置：1 have → N bid → 1 accept → deal → review (one_to_many)."""
    tmp = Path(tempfile.mkdtemp(prefix="fm_goods_"))
    try:
        seller = actor("seller", tmp, ["seller"])
        buyer1 = actor("buyer1", tmp, ["buyer"])
        buyer2 = actor("buyer2", tmp, ["buyer"])
        have = env(
            seller,
            "have",
            {
                "item": {"title": "闲置机械键盘", "condition": "used", "qty": 1},
                "price": {"amount": "350", "currency": "CNY"},
                "where": {"region": "上海-徐汇"},
                "stock": 1,
                "match": {
                    "mode": "one_to_many",
                    "vertical": "goods_unique",
                    "max_accepts": 1,
                    "exclusive": True,
                },
            },
        )
        post(board_url, store, have)
        bid1 = env(
            buyer1,
            "bid",
            {"target_id": have["id"], "price": {"amount": "320", "currency": "CNY"}, "message": "320 面交"},
            thread=have["id"],
            reply_to=have["id"],
        )
        bid2 = env(
            buyer2,
            "bid",
            {"target_id": have["id"], "price": {"amount": "340", "currency": "CNY"}, "message": "340"},
            thread=have["id"],
            reply_to=have["id"],
        )
        post(board_url, store, bid1)
        post(board_url, store, bid2)
        acc = env(
            seller,
            "accept",
            {"bid_id": bid2["id"], "message": "卖给 buyer2"},
            thread=have["id"],
            reply_to=bid2["id"],
        )
        post(board_url, store, acc)
        deal = env(
            seller,
            "deal",
            {
                "parties": {"buyer": buyer2["id"], "seller": seller["id"], "courier": None},
                "item": {"title": "闲置机械键盘", "qty": 1},
                "price": {"amount": "340", "currency": "CNY"},
                "based_on": [have["id"], bid2["id"], acc["id"]],
                "match": {"mode": "one_to_one", "vertical": "goods_unique", "max_accepts": 1},
                "terms": "一对多竞价后锁定一单",
            },
            thread=have["id"],
        )
        post(board_url, store, deal)
        rev = env(
            buyer2,
            "review",
            {"subject_id": seller["id"], "deal_id": deal["id"], "stars": 5, "text": "键盘不错"},
        )
        post(board_url, store, rev)
        return {"vertical": "goods_unique", "mode": "one_to_many→1", "have": have["id"], "deal": deal["id"], "bids": 2}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_food(board_url, store) -> dict:
    """外卖：餐品 deal + 快递 broadcast_claim。"""
    tmp = Path(tempfile.mkdtemp(prefix="fm_food_"))
    try:
        shop = actor("shop", tmp, ["seller"])
        eater = actor("eater", tmp, ["buyer"])
        rider_a = actor("rider_a", tmp, ["courier"])
        rider_b = actor("rider_b", tmp, ["courier"])
        want = env(
            eater,
            "want",
            {
                "item": {"title": "黄焖鸡米饭 一份", "tags": ["food"]},
                "budget": {"amount": "28", "currency": "CNY"},
                "where": {"region": "上海-浦东"},
                "need_courier": True,
                "match": {
                    "mode": "one_to_many",
                    "vertical": "food_order",
                    "max_accepts": 1,
                    "exclusive": True,
                },
                "notes": "少辣",
            },
        )
        post(board_url, store, want)
        bid = env(
            shop,
            "bid",
            {
                "target_id": want["id"],
                "price": {"amount": "26", "currency": "CNY"},
                "delivery": {"mode": "courier"},
                "message": "25分钟出餐",
            },
            thread=want["id"],
            reply_to=want["id"],
        )
        post(board_url, store, bid)
        acc = env(eater, "accept", {"bid_id": bid["id"]}, thread=want["id"], reply_to=bid["id"])
        post(board_url, store, acc)
        meal = env(
            shop,
            "deal",
            {
                "parties": {"buyer": eater["id"], "seller": shop["id"], "courier": None},
                "item": {"title": "黄焖鸡米饭 一份"},
                "price": {"amount": "26", "currency": "CNY"},
                "delivery": {"mode": "courier", "courier_fee": None},
                "based_on": [want["id"], bid["id"], acc["id"]],
                "match": {"mode": "one_to_one", "vertical": "food_order"},
            },
            thread=want["id"],
        )
        post(board_url, store, meal)
        offer_a = env(
            rider_a,
            "courier.offer",
            {
                "target_id": meal["id"],
                "fee": {"amount": "8", "currency": "CNY"},
                "eta": "20m",
                "match": {"mode": "broadcast_claim", "vertical": "food_order", "max_accepts": 1},
            },
        )
        offer_b = env(
            rider_b,
            "courier.offer",
            {
                "target_id": meal["id"],
                "fee": {"amount": "6", "currency": "CNY"},
                "eta": "25m",
                "match": {"mode": "broadcast_claim", "vertical": "food_order", "max_accepts": 1},
            },
        )
        post(board_url, store, offer_a)
        post(board_url, store, offer_b)
        cacc = env(eater, "courier.accept", {"offer_id": offer_b["id"]}, reply_to=offer_b["id"])
        post(board_url, store, cacc)
        ful = env(rider_b, "fulfill", {"deal_id": meal["id"], "event": "delivered", "note": "已送达"})
        post(board_url, store, ful)
        conf = env(eater, "confirm", {"deal_id": meal["id"], "status": "complete"})
        post(board_url, store, conf)
        return {
            "vertical": "food_order",
            "mode": "meal deal + courier offers → pick 1",
            "want": want["id"],
            "meal_deal": meal["id"],
            "courier_offers": 2,
            "chosen_fee": "6",
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_geo(board_url, store) -> dict:
    """Two shops with geo — list by distance from customer."""
    tmp = Path(tempfile.mkdtemp(prefix="fm_geo_"))
    try:
        shop_near = actor("shop_near", tmp, ["seller"])
        shop_far = actor("shop_far", tmp, ["seller"])
        # Customer origin: Lujiazui-ish
        origin = (31.2397, 121.4998)
        near = env(
            shop_near,
            "have",
            {
                "item": {"title": "黄焖鸡-近", "tags": ["food"]},
                "price": {"amount": "26", "currency": "CNY"},
                "where": {
                    "region": "上海-浦东",
                    "geo": {"lat": 31.235, "lon": 121.505, "radius_m": 3000},
                    "privacy": "public",
                },
                "match": {"mode": "one_to_many", "vertical": "food_order", "max_accepts": 1},
            },
        )
        far = env(
            shop_far,
            "have",
            {
                "item": {"title": "黄焖鸡-远", "tags": ["food"]},
                "price": {"amount": "22", "currency": "CNY"},
                "where": {
                    "region": "上海-松江",
                    "geo": {"lat": 31.032, "lon": 121.227, "radius_m": 5000},
                    "privacy": "public",
                },
                "match": {"mode": "one_to_many", "vertical": "food_order", "max_accepts": 1},
            },
        )
        post(board_url, store, near)
        post(board_url, store, far)
        # distance API
        dist = http_json(
            "GET",
            board_url.rstrip("/")
            + f"/api/v1/distance?from_id={near['id']}&to_id={far['id']}",
        )
        assert dist.get("distance_m", 0) > 1000, dist
        # nearby list sorted by distance
        rows = http_json(
            "GET",
            board_url.rstrip("/")
            + "/api/v1/messages?"
            + urllib.parse.urlencode(
                {
                    "type": "have",
                    "summary": "1",
                    "near_lat": origin[0],
                    "near_lon": origin[1],
                    "radius_m": 50000,
                    "sort": "distance",
                    "q": "黄焖鸡",
                }
            ),
        )
        msgs = rows.get("messages") or []
        geo_msgs = [m for m in msgs if m.get("title") in ("黄焖鸡-近", "黄焖鸡-远")]
        assert len(geo_msgs) >= 2, rows
        assert geo_msgs[0]["title"] == "黄焖鸡-近", geo_msgs
        assert geo_msgs[0]["distance_m"] < geo_msgs[1]["distance_m"], geo_msgs
        # radius filter excludes far if tight
        tight = http_json(
            "GET",
            board_url.rstrip("/")
            + "/api/v1/messages?"
            + urllib.parse.urlencode(
                {
                    "type": "have",
                    "summary": "1",
                    "near_lat": origin[0],
                    "near_lon": origin[1],
                    "radius_m": 3000,
                    "sort": "distance",
                    "q": "黄焖鸡",
                }
            ),
        )
        titles = {m.get("title") for m in (tight.get("messages") or [])}
        assert "黄焖鸡-近" in titles
        assert "黄焖鸡-远" not in titles
        return {
            "vertical": "geo",
            "shop_distance_m": dist["distance_m"],
            "near_first": geo_msgs[0]["distance_text"],
            "radius_filter_ok": True,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scenario_ride(board_url, store) -> dict:
    """打车：1 want → N driver offers → passenger accept one (many_to_one / broadcast_claim)."""
    tmp = Path(tempfile.mkdtemp(prefix="fm_ride_"))
    try:
        pax = actor("pax", tmp, ["buyer"])
        drv1 = actor("drv1", tmp, ["courier"])
        drv2 = actor("drv2", tmp, ["courier"])
        want = env(
            pax,
            "want",
            {
                "item": {
                    "title": "打车 陆家嘴 → 虹桥火车站",
                    "description": "现在出发，可带行李",
                    "tags": ["ride"],
                },
                "budget": {"amount": "80", "currency": "CNY"},
                "where": {"region": "上海", "label": "陆家嘴→虹桥"},
                "need_courier": True,
                "match": {
                    "mode": "one_to_many",
                    "vertical": "ride",
                    "max_accepts": 1,
                    "exclusive": True,
                },
            },
        )
        post(board_url, store, want)
        o1 = env(
            drv1,
            "courier.offer",
            {
                "target_id": want["id"],
                "fee": {"amount": "75", "currency": "CNY"},
                "eta": "3min",
                "vehicle": "网约车-蓝",
                "match": {"mode": "one_to_many", "vertical": "ride"},
            },
            thread=want["id"],
        )
        o2 = env(
            drv2,
            "courier.offer",
            {
                "target_id": want["id"],
                "fee": {"amount": "70", "currency": "CNY"},
                "eta": "6min",
                "vehicle": "网约车-白",
                "match": {"mode": "one_to_many", "vertical": "ride"},
            },
            thread=want["id"],
        )
        post(board_url, store, o1)
        post(board_url, store, o2)
        acc = env(pax, "courier.accept", {"offer_id": o1["id"], "message": "选最近"}, thread=want["id"])
        post(board_url, store, acc)
        deal = env(
            pax,
            "deal",
            {
                "parties": {"buyer": pax["id"], "seller": drv1["id"], "courier": drv1["id"]},
                "item": {"title": "打车 陆家嘴 → 虹桥火车站"},
                "price": {"amount": "75", "currency": "CNY"},
                "based_on": [want["id"], o1["id"], acc["id"]],
                "match": {"mode": "one_to_one", "vertical": "ride"},
                "delivery": {"mode": "courier"},
            },
            thread=want["id"],
        )
        post(board_url, store, deal)
        post(board_url, store, env(drv1, "fulfill", {"deal_id": deal["id"], "event": "picked_up"}))
        post(board_url, store, env(drv1, "fulfill", {"deal_id": deal["id"], "event": "delivered"}))
        post(board_url, store, env(pax, "confirm", {"deal_id": deal["id"], "status": "complete"}))
        post(
            board_url,
            store,
            env(pax, "review", {"subject_id": drv1["id"], "deal_id": deal["id"], "stars": 5, "text": "准时"}),
        )
        return {"vertical": "ride", "mode": "one_to_many offers → passenger picks 1", "want": want["id"], "deal": deal["id"]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def wait_health(url: str, seconds: float = 15.0) -> None:
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        try:
            h = http_json("GET", url.rstrip("/") + "/health")
            if h.get("ok"):
                return
            last = h
        except Exception as e:
            last = str(e)
        time.sleep(0.2)
    raise RuntimeError(f"server not healthy: {last}")


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default=None, help="Existing board URL; if omitted start ephemeral server")
    ap.add_argument("--port", type=int, default=18787)
    args = ap.parse_args()

    proc = None
    board_url = args.board
    store = None
    tmp_board = None

    try:
        if not board_url:
            tmp_board = Path(tempfile.mkdtemp(prefix="fm_board_"))
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(RUNTIME / "server.py"),
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.port),
                    "--board-dir",
                    str(tmp_board),
                ],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            board_url = f"http://127.0.0.1:{args.port}"
            wait_health(board_url)
        else:
            wait_health(board_url)

        # reject platform fee on live API
        try:
            http_json(
                "POST",
                board_url.rstrip("/") + "/api/v1/messages",
                {
                    "v": 1,
                    "id": new_id(),
                    "type": "want",
                    "ts": utc_now(),
                    "from": {"id": "x"},
                    "body": {"item": {"title": "x"}, "platform_fee": 1},
                },
            )
            fee_blocked = False
        except urllib.error.HTTPError as e:
            fee_blocked = e.code == 400
        assert fee_blocked, "platform_fee must be rejected"

        results = {
            "goods_unique": scenario_goods(board_url, store),
            "food_order": scenario_food(board_url, store),
            "geo": scenario_geo(board_url, store),
            "ride": scenario_ride(board_url, store),
            "fee_blocked": fee_blocked,
            "board": board_url,
            "health": http_json("GET", board_url.rstrip("/") + "/health"),
        }
        print(json.dumps({"ok": True, "results": results}, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2))
        if proc and proc.stdout:
            try:
                out = proc.stdout.read1(4000) if hasattr(proc.stdout, "read1") else proc.stdout.read(4000)
                if out:
                    print(out.decode("utf-8", errors="replace"), file=sys.stderr)
            except Exception:
                pass
        return 1
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except Exception:
                proc.kill()
        if tmp_board:
            shutil.rmtree(tmp_board, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
