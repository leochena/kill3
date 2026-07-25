#!/usr/bin/env python3
"""Seed a demo board and export assets/demo snapshots for the public gallery."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime"
ASSETS = ROOT / "assets" / "demo"
sys.path.insert(0, str(RUNTIME))

from fmlib import new_id, utc_now  # noqa: E402


def http_json(method: str, url: str, body: dict | None = None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def envelope(typ: str, actor: dict, body: dict, **extra):
    msg = {
        "v": 1,
        "id": new_id(),
        "type": typ,
        "ts": utc_now(),
        "from": actor,
        "body": body,
        "sig": None,
    }
    msg.update(extra)
    return msg


def main() -> int:
    ASSETS.mkdir(parents=True, exist_ok=True)
    port = 19091
    board_dir = Path(tempfile.mkdtemp(prefix="fm_demo_assets_"))
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
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                http_json("GET", base + "/health")
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("board failed to start")

        seller = {"id": "demo_seller_eu", "display": "Mira", "roles": ["seller"]}
        buyer = {"id": "demo_buyer_eu", "display": "Sam", "roles": ["buyer"]}
        cook = {"id": "demo_kitchen", "display": "NoriBowl", "roles": ["seller"]}
        rider = {"id": "demo_rider", "display": "Kai", "roles": ["courier"]}
        pax = {"id": "demo_pax", "display": "Alex", "roles": ["buyer"]}
        drv = {"id": "demo_driver", "display": "Riley", "roles": ["courier"]}

        # Berlin second-hand
        have = envelope(
            "have",
            seller,
            {
                "item": {"title": "Used mechanical keyboard", "condition": "used", "tags": ["goods"]},
                "price": {"amount": "80", "currency": "EUR"},
                "where": {
                    "region": "Berlin-Mitte",
                    "geo": {"lat": 52.5200, "lon": 13.4050, "radius_m": 4000},
                    "privacy": "public",
                },
                "stock": 1,
                "match": {
                    "mode": "one_to_many",
                    "vertical": "goods_unique",
                    "max_accepts": 1,
                    "exclusive": True,
                },
            },
        )
        http_json("POST", base + "/api/v1/messages?force=1", have)

        bid = envelope(
            "bid",
            buyer,
            {
                "target_id": have["id"],
                "price": {"amount": "70", "currency": "EUR"},
                "message": "Can meet near Alexanderplatz",
                "delivery": {"mode": "meetup"},
            },
            thread=have["id"],
            reply_to=have["id"],
        )
        http_json("POST", base + "/api/v1/messages?force=1", bid)

        # Lisbon food + optional courier
        meal_have = envelope(
            "have",
            cook,
            {
                "item": {"title": "Vegetarian lunch bowl", "tags": ["food"]},
                "price": {"amount": "9.5", "currency": "EUR"},
                "where": {
                    "region": "Lisbon-Baixa",
                    "geo": {"lat": 38.7100, "lon": -9.1360},
                    "privacy": "public",
                },
                "match": {"mode": "one_to_many", "vertical": "food_order", "max_accepts": 1},
                "notes": "Ready in 20m · vegetarian",
            },
        )
        http_json("POST", base + "/api/v1/messages?force=1", meal_have)
        meal_deal = envelope(
            "deal",
            cook,
            {
                "parties": {"buyer": buyer["id"], "seller": cook["id"], "courier": None},
                "item": {"title": "Vegetarian lunch bowl"},
                "price": {"amount": "9.5", "currency": "EUR"},
                "delivery": {"mode": "courier"},
                "based_on": [meal_have["id"]],
                "match": {"mode": "one_to_one", "vertical": "food_order"},
            },
            thread=meal_have["id"],
        )
        http_json("POST", base + "/api/v1/messages?force=1", meal_deal)
        offer = envelope(
            "courier.offer",
            rider,
            {
                "target_id": meal_deal["id"],
                "fee": {"amount": "3.5", "currency": "EUR"},
                "eta": "15m",
                "match": {"mode": "one_to_many", "vertical": "food_order"},
                "where": {"region": "Lisbon", "geo": {"lat": 38.712, "lon": -9.14}, "privacy": "public"},
            },
        )
        http_json("POST", base + "/api/v1/messages?force=1", offer)

        # NYC-ish ride want + driver offer
        ride = envelope(
            "want",
            pax,
            {
                "item": {
                    "title": "Ride Brooklyn → JFK",
                    "description": "2 bags · flexible 10min",
                    "tags": ["ride"],
                },
                "budget": {"amount": "55", "currency": "USD"},
                "where": {
                    "region": "New York",
                    "label": "Brooklyn → JFK",
                    "geo": {"lat": 40.6782, "lon": -73.9442},
                    "privacy": "public",
                },
                "need_courier": True,
                "match": {
                    "mode": "one_to_many",
                    "vertical": "ride",
                    "max_accepts": 1,
                    "exclusive": True,
                },
            },
        )
        http_json("POST", base + "/api/v1/messages?force=1", ride)
        drv_offer = envelope(
            "courier.offer",
            drv,
            {
                "target_id": ride["id"],
                "fee": {"amount": "48", "currency": "USD"},
                "eta": "6min",
                "vehicle": "sedan",
                "match": {"mode": "one_to_many", "vertical": "ride"},
                "where": {"geo": {"lat": 40.68, "lon": -73.95}, "privacy": "public"},
            },
            thread=ride["id"],
        )
        http_json("POST", base + "/api/v1/messages?force=1", drv_offer)

        # nearby list from Berlin center
        nearby = http_json(
            "GET",
            base
            + "/api/v1/messages?type=have,want,courier.offer,deal&summary=1&near_lat=52.52&near_lon=13.405&radius_m=5000000&sort=distance&limit=50",
        )
        all_msgs = http_json("GET", base + "/api/v1/messages?limit=100")
        health = http_json("GET", base + "/health")

        snapshot = {
            "generated_at": utc_now(),
            "purpose": "Public gallery demo — fictional peers, global sample cities",
            "health": health,
            "messages": all_msgs.get("messages") or all_msgs,
            "nearby_from_berlin_sample": nearby,
        }
        (ASSETS / "board-snapshot.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        # run smoke and capture
        smoke = subprocess.run(
            [sys.executable, str(RUNTIME / "smoke_e2e.py"), "--port", "19092"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        sample = {
            "generated_at": utc_now(),
            "smoke_exit_code": smoke.returncode,
            "stdout_json": None,
            "note": "Re-run scripts/export_demo_assets.py to refresh",
        }
        try:
            sample["stdout_json"] = json.loads(smoke.stdout)
        except Exception:
            sample["stdout_raw"] = (smoke.stdout or "")[-4000:]
            sample["stderr_raw"] = (smoke.stderr or "")[-2000:]
        (ASSETS / "smoke-result.sample.json").write_text(
            json.dumps(sample, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        print(
            json.dumps(
                {
                    "ok": smoke.returncode == 0,
                    "wrote": [
                        str(ASSETS / "board-snapshot.json"),
                        str(ASSETS / "smoke-result.sample.json"),
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if smoke.returncode == 0 else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()
        shutil.rmtree(board_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
