# Changelog

## 0.1.4 — 2026-07-25

- Global public-interest docs rewrite (README, legal, philosophy, contributing)
- Match-mode realism: ride prefer choose-among-offers; food two-stage clarified
- `assets/` showcase: diagrams, UI sketch, demo export script + snapshots
- Smoke ride mode aligned with docs

## 0.1.3 — 2026-07-25

- Legal risk hygiene: `docs/legal-notice.md`, `DISCLAIMER.md`, `TRADEMARKS.md`
- Soften marketing: open protocol framing; no commercial-platform scrape/impersonation
- Skill/CONTRIBUTING/SECURITY: reject unofficial-app and ToS-evasion-as-a-feature PRs
- Health policy: no affiliation with commercial marketplaces

## 0.1.2 — 2026-07-25

- Project nature: **public-interest / 公益** — no paid boost forever in mainline
- Reject boost/sponsored/ad_bid/pin_rank fields in validation
- Docs, skill, CONTRIBUTING, health policy state anti-rent discovery

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
