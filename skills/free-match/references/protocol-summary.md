# Protocol summary (v1)

Full specs: repo `protocol/SPEC.md`, `docs/match-modes.md`, `protocol/schemas/*.json`.

## Cardinality first (一对一 / 一对多 / …)

Before drafting a message, pick **vertical + match.mode**:

| vertical | Default mode | Story |
|----------|--------------|--------|
| `goods_unique` | `one_to_many` | 闲置孤品：多买家报价，成交一单 |
| `goods_stock` | `one_to_many` | 多库存：可多 deal，注意 stock |
| `food_order` | meal `one_to_many` + courier `broadcast_claim` | 外卖：餐品与配送可拆两段 |
| `ride` | `broadcast_claim` / `many_to_one` | 打车：一单需求，多车抢/报价 |
| `errand` | `one_to_many` | 跑腿 |
| `service` | `one_to_many` | 服务 |
| `bulk_rfq` | `one_to_many` | 询价 |

Optional body:

```json
"match": {
  "mode": "one_to_many",
  "vertical": "goods_unique",
  "max_accepts": 1,
  "exclusive": true,
  "claim_window_sec": 120
}
```

Always tell the human in one line which cardinality you are using.

## Envelope skeleton

```json
{
  "v": 1,
  "id": "<ulid-or-uuid>",
  "type": "want",
  "ts": "2026-07-25T12:00:00Z",
  "from": {
    "id": "actor_abc",
    "display": "Ada",
    "roles": ["buyer"]
  },
  "to": null,
  "thread": null,
  "reply_to": null,
  "ttl_sec": 86400,
  "body": {},
  "sig": null
}
```

## Types cheat sheet

| type | body must include | notes |
|------|-------------------|--------|
| `want` | `item` | optional `budget`, `where`, `need_courier`, `match` |
| `have` | `item` | optional `price`, `where`, `stock`, `match` |
| `bid` | `target_id`, `price` | optional payment/delivery |
| `accept` | `bid_id` | |
| `reject` | `bid_id` | optional free-text reason |
| `deal` | `parties`, `item`, `price` | snapshot of agreed terms |
| `fulfill` | `deal_id`, `event` | shipped/picked_up/delivered/… |
| `confirm` | `deal_id`, `status` | received/paid/complete/disputed/cancelled |
| `review` | `subject_id`, `deal_id`, `stars` | 1–5, portable |
| `courier.offer` | `target_id`, `fee` | drivers/riders |
| `courier.accept` | `offer_id` | |
| `identity.announce` | free | pubkey, roles, bio |

## Money

```json
{ "amount": "500", "currency": "CNY" }
```

Use decimal **strings**.

## Minimal want (闲置买家)

```json
{
  "v": 1,
  "id": "01wantexample0001",
  "type": "want",
  "ts": "2026-07-25T12:00:00Z",
  "from": { "id": "buyer1", "display": "买买", "roles": ["buyer"] },
  "ttl_sec": 172800,
  "body": {
    "item": {
      "title": "二手 24寸 1080p 显示器",
      "condition": "used",
      "qty": 1
    },
    "budget": { "amount": "500", "currency": "CNY" },
    "where": { "region": "上海-浦东", "privacy": "after_deal" },
    "need_courier": false,
    "notes": "可自取，工作日晚上",
    "match": { "mode": "one_to_many", "vertical": "goods_unique", "max_accepts": 1, "exclusive": true }
  },
  "sig": null
}
```

## Ride want (打车)

```json
{
  "type": "want",
  "body": {
    "item": { "title": "陆家嘴 → 虹桥火车站", "tags": ["ride"] },
    "budget": { "amount": "80", "currency": "CNY" },
    "where": { "region": "上海" },
    "need_courier": true,
    "match": { "mode": "broadcast_claim", "vertical": "ride", "max_accepts": 1, "claim_window_sec": 120 }
  }
}
```

## Forbidden in protocol messages

Do **not** invent fields like:

- `platform_fee`, `commission`, `service_charge`
- `boost`, `sponsored`, `ad_bid`, `featured_until`, `pin_rank`, `traffic_pack`（付费置顶/流量变现）
- `kyc_level`, `banned`, `compliance_status`, `risk_score`

Peers may write free-text notes — the **protocol** does not classify legality.
