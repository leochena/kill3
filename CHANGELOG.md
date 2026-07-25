# Changelog

## 0.1.1 — 2026-07-25

- Geo: haversine distance, `where.geo` on posts
- API: `near_lat/near_lon/radius_m/sort=distance`, `/api/v1/distance`
- CLI: `--lat/--lon`, `list --near-*`, `distance`
- Web UI: GPS, map pick, OSM markers, distance badges
- Smoke: nearby sort + radius filter

## 0.1.0 — 2026-07-25

- Free-Match protocol v1 (envelope + body types)
- Portable agent skill `skills/free-match`
- Local board CLI `runtime/fm.py` (local dir or `--board` URL)
- HTTP dumb board + Web UI `runtime/server.py`
- Match modes: one_to_one / one_to_many / many_to_one / broadcast_claim
- Verticals: goods, food_order, ride, errand, service, bulk_rfq
- E2E smoke: 闲置 / 外卖+骑手 / 打车
- MIT license, contributing guide
