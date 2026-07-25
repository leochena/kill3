# Match modes & verticals (global)

Free-match is **not** one marketplace UX. Real jobs need different **cardinality** and **who locks the deal**.  
Software models **shape**; it does **not** police legality or guarantee global atomic locks.

## Cardinality

| Mode | Symbol | Meaning | Good fit | Poor fit if… |
|------|--------|---------|----------|----------------|
| `one_to_one` | 1↔1 | One intended counterparty (often after discovery) | Private renegotiation, custom contract | You still want public competition |
| `one_to_many` | 1→N | One listing, many bids; typically **one** winner per unit | Unique goods, RFQ, errands | You need many parallel fulfillments of identical stock (use stock + multiple deals) |
| `many_to_one` | N→1 | Many suppliers compete for **one** demand slot | Rides, urgent capacity | Suppliers should form independent parallel sales |
| `many_to_many` | N↔M | Open board; many deals form independently | Neighborhood board, skills market | You need exclusive inventory without agent discipline |
| `broadcast_claim` | claim race | Soft “first honorable claim” among peers | Time-critical courier dispatch | You need passenger to **compare** quotes first (use 1→N then accept) |

`body.match.mode` is a **hint for agents/UI**. Dumb boards do not enforce world-wide exclusivity.

## Verticals

| vertical | Roles | Default mode | Money objects | Notes |
|----------|-------|--------------|---------------|-------|
| `goods_unique` | buyer ↔ seller | `one_to_many` | item price | One physical unit; after accept, stop selling that unit |
| `goods_stock` | buyer ↔ seller | `one_to_many` | item price × qty | Multiple deals OK; **local** stock counter only |
| `food_order` | buyer ↔ seller; optional courier | meal negotiate → 1 deal; courier optional 1→N or claim | **meal** vs **delivery fee** separate | Self-pickup / self-delivery ⇒ `parties.courier = null` |
| `ride` | passenger (buyer) ↔ driver (courier/seller) | prefer passenger **selects** among `courier.offer`s (`one_to_many` on the want); optional claim mode for “take next free car” | trip price | Trip is the item (A→B, time window), not a SKU |
| `errand` | buyer ↔ courier | `one_to_many` | courier fee | Single task description in `item` + `notes` |
| `service` | buyer ↔ seller | `one_to_many` | service price | Scope & revisions in text; optional milestones as multiple deals |
| `bulk_rfq` | buyer want, many sellers | `one_to_many` | quotes | Longer `ttl_sec`; multi-round bids |

### Corrections to earlier oversimplifications

1. **Ride ≠ always broadcast_claim.**  
   - *Compare then choose* (common): drivers send offers → passenger `courier.accept` one. Mode on the **want**: `one_to_many` or `many_to_one` with `max_accepts: 1`.  
   - *Grab next car*: `broadcast_claim` + short `claim_window_sec` — peers must honor; board cannot force it.

2. **Food is two concerns.**  
   - Kitchen deal (food ready time, price, diet notes).  
   - Movement deal (courier fee, ETA) **only if** neither party self-delivers.  
   - Do not force a courier stage on every meal.

3. **Courier on goods** is optional logistics, not a separate vertical by default — use `need_courier` / `delivery.mode` + `courier.*` messages.

4. **Stock** is not a global ledger. Agents decrement; races need human/agent resolution (`confirm cancelled` on the loser).

## Protocol object

```json
"match": {
  "mode": "one_to_many",
  "vertical": "goods_unique",
  "max_accepts": 1,
  "exclusive": true,
  "claim_window_sec": 120
}
```

| field | meaning |
|-------|---------|
| `mode` | cardinality |
| `vertical` | scenario hint — **not** a ban taxonomy |
| `max_accepts` | concurrent accepts the **author** intends (default 1) |
| `exclusive` | after deal, stop soliciting for that unit |
| `claim_window_sec` | soft race window for claim-style flows |

## State machines (realistic)

### A. Unique goods

```text
have(stock=1, exclusive) → bids* → accept ONE → deal → fulfill? → confirm → review
```

### B. Stock goods

```text
have(stock=N) → (bid → accept → deal → …) × up to N   # parallel threads OK
```

### C. Food (optional courier)

```text
want/have → bid/accept → deal(meal)
if delivery.mode = courier:
  courier.offer* → courier.accept ONE → fulfill* → confirm → review(seller), review(courier)
else:
  pickup / seller delivers → confirm → review(seller)
```

### D. Ride (recommended: choose among offers)

```text
want(trip, geo A/B or notes) → courier.offer* → passenger accept ONE → deal → fulfill → confirm → review
```

### E. Errand

```text
want(task) → courier.offer* → accept → deal → fulfill* → review
```

## Agent decision tree

1. Classify **vertical** from user language.  
2. Choose **mode** + `max_accepts` (default 1).  
3. Say it in one plain sentence in the user’s language.  
4. Keep **price labels** separate (goods vs courier vs tip).  
5. Prefer **distance** among equal options when geo exists.  
6. On double-accept race: show both; user picks; optional `confirm cancelled` on the other.

## UI hints

- Chips: goods · food · ride · errand · service · all  
- Badges: mode + vertical + distance  
- Never show a single “platform score” paid by ads  

## Never (mainline)

- Board-operator surge tax  
- Paid boost / featured pin  
- Category bans as protocol errors  
- Forced single payment rail  
- Global lock pretending the filesystem board is a stock exchange  
