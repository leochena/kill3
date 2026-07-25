# Location & distance

## Goal

Peers can **see how far** a listing is without a platform map monopoly.

- Protocol stores optional WGS84 `where.geo.{lat,lon,radius_m}`
- Clients compute **haversine** distance in meters
- Web UI: browser GPS / map pick + OpenStreetMap tiles (display only)
- Board remains a dumb pipe — no paid geo boost, no forced map vendor in protocol

## Message shape

```json
"where": {
  "region": "上海-浦东",
  "label": "店门口",
  "geo": { "lat": 31.235, "lon": 121.505, "radius_m": 3000 },
  "privacy": "public"
}
```

`privacy`: `public` | `after_deal` | `direct_only` — clients SHOULD hide precise address until appropriate; coordinates may still be coarse public pin.

## API

```
GET /api/v1/messages?near_lat=&near_lon=&radius_m=&sort=distance&summary=1
GET /api/v1/distance?from_id=A&to_id=B
GET /api/v1/distance?from_lat=&from_lon=&to_lat=&to_lon=
```

Summary rows include `lat`, `lon`, `distance_m`, `distance_text`.

## CLI

```bash
python runtime/fm.py have --title "黄焖鸡" --price 26 \
  --region "上海-浦东" --lat 31.235 --lon 121.505 --place-radius 3000

python runtime/fm.py list --type have \
  --near-lat 31.24 --near-lon 121.50 --radius-m 5000 --sort distance

python runtime/fm.py distance --from-id <id1> --to-id <id2>
```

## Agent skill rules

1. When user mentions 附近/距离/同城, ask for or use device location → fill `where.geo`.
2. When listing candidates, show `distance_text` beside price.
3. For ride/food, prefer sorting by distance among otherwise equal offers.
4. Do not invent paid “热门商圈” or sponsored nearby pins — 公益项目禁止流量变现.
5. Respect privacy: default `after_deal` for fine address in notes; pin can be public shop location.

## Non-goals (still)

- Turn-by-turn navigation SDK lock-in
- Live driver GPS streaming protocol (future optional)
- Server-side geocoding of free text (client may do it)
- **Paid map pins / 付费置顶附近商户** — 公益项目，永远不做
