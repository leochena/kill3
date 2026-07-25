# Free-Match Protocol v1

Transport-agnostic peer matching for buyers, sellers, and couriers.

## Design laws

1. **No rent fields** — no platform fee, no mandatory payment processor.
2. **No policy fields** — no banned-item codes, no KYC status, no compliance flags in the protocol.
3. **Roles are hats** — any actor may wear buyer / seller / courier.
4. **Boards are optional** — messages may be direct (`to`) or public (board broadcast).
5. **Signatures recommended** — verify when present; unsigned is allowed for local throwaway boards.

## Message lifecycle

```
identity.announce? → want | have
        ↓
       bid  ←→  reject
        ↓
      accept
        ↓
       deal
        ↓
  courier.offer? → courier.accept?
        ↓
     fulfill*
        ↓
     confirm*   (received / paid / complete / disputed / cancelled)
        ↓
     review*    (each party may review others)
```

`*` = zero or more events.

## Envelope

See `schemas/envelope.json`. Every message:

| Field | Required | Notes |
|-------|----------|-------|
| `v` | yes | `1` |
| `id` | yes | unique |
| `type` | yes | enum |
| `ts` | yes | ISO-8601 |
| `from` | yes | actor ref |
| `body` | yes | type-specific |
| `to` | no | direct peer |
| `thread` | no | negotiation root |
| `reply_to` | no | parent |
| `ttl_sec` | no | soft expiry |
| `sig` | no | signature |

## Body types

Defined in `schemas/bodies.json` under `$defs/*_body`.

| `type` | Body def | Purpose |
|--------|----------|---------|
| `want` | `want_body` | Buyer demand |
| `have` | `have_body` | Seller offer |
| `bid` | `bid_body` | Counterparty quote |
| `accept` / `reject` | … | Resolve a bid |
| `deal` | `deal_body` | Locked terms snapshot |
| `fulfill` | `fulfill_body` | Logistics / service progress |
| `confirm` | `confirm_body` | Settlement / receipt status |
| `review` | `review_body` | Portable reputation atom |
| `courier.offer` / `courier.accept` | … | Third-party delivery match |
| `identity.announce` | … | Optional presence |

## Canonical JSON for signing (recommended)

1. Take envelope **without** `sig`.
2. UTF-8 JSON with sorted keys, no insignificant whitespace.
3. Sign with actor private key (`ed25519` preferred).
4. Put base64 signature in `sig`.

Receivers: if `sig` present and `from.id` binds to a known pubkey, verify; if fail, treat as unauthenticated (user choice to ignore).

## Match cardinality (optional body.match)

Peers SHOULD declare how many counterparties are expected. Boards do **not** globally enforce locks.

```json
"match": {
  "mode": "one_to_many",
  "vertical": "goods_unique",
  "max_accepts": 1,
  "exclusive": true,
  "claim_window_sec": 120
}
```

| mode | meaning |
|------|---------|
| `one_to_one` | single intended counterparty |
| `one_to_many` | one listing, many bids, typically one winner |
| `many_to_one` | many suppliers compete for one demand slot |
| `many_to_many` | open board, independent deals |
| `broadcast_claim` | race-friendly claims (rides, courier dispatch) |

Common `vertical` values: `goods_unique`, `goods_stock`, `food_order`, `ride`, `errand`, `service`, `bulk_rfq`.

See `docs/match-modes.md`.

## Discovery (non-normative)

Protocol does **not** mandate a discovery network. Implementations may:

- Drop JSON files into a shared folder / git repo / S3 bucket
- Post to Nostr kinds (custom), Matrix room, Telegram channel, email list
- Run a dumb HTTP board that only stores and lists envelopes
- Gossip over LAN

Any “board” is a **mirror**, not a landlord: it should not rewrite body content or inject fees.

## Extensibility

- Unknown `type` values: ignore or store raw.
- Extra body fields: ignore if not understood (producers should stick to schema for interoperability).
- `v > 1`: negotiate or dual-publish.

## Out of scope

- Legal classification of goods/services
- Tax reporting
- Chargebacks / platform dispute court
- Global ban lists
