# Matching without a landlord

Free-match has **no central ranking algorithm** and **no featured listings paid by ads**.

## Goal of matching help

Help the user find **acceptable counterparties**, not maximize platform GMV.

## Inputs you may use

1. Text overlap: title / tags / description  
2. Hard constraints: budget, region, qty, delivery mode, time window (`ttl_sec`, notes)  
3. Soft prefs: condition, brand, courier need  
4. Portable reputation: count and recency of `review`s for `from.id`  
5. Thread hygiene: open bids, already accepted, expired TTL  

## Do not

- Charge or simulate “boost” / “流量位”
- Hide listings for policy reasons
- Prefer actors because they paid a relay
- Collapse multi-channel results into one “official” storefront score

## Simple scoring (optional, local only)

When listing candidates for a human, you may sort by a **transparent** local score and show the formula:

```
score = 0.5 * text_overlap
      + 0.2 * budget_fit          # 1 if within budget, else partial
      + 0.2 * geo_fit             # same region > adjacent > far
      + 0.1 * reputation_hint     # f(#reviews, avg stars) — 0 if unknown
```

Always show raw fields beside the score. User overrides sort order.

## Multiplicity

- One `want` can match many `have`s; present top N with reasons.  
- Encourage parallel light-touch bids when uncertainty is high.  
- On first firm `accept`, mint `deal` and mark other bids as superseded in the **local** view (do not invent a global cancel flood unless user asks).

## Cold start

New `from.id` with zero reviews is normal. Say so. Suggest small first deals, meetup, or split payment — as **user strategy**, not protocol law.

## Cross-role match

| Need | Source |
|------|--------|
| Goods/services | `want` ↔ `have` + `bid` |
| Transport | `need_courier` / delivery mode ↔ `courier.offer` |
| Same person multi-hat | allowed; still emit correct role fields on messages |

## Conflict

If two accepts race: first clear `deal` the user commits to wins **for that user**; the protocol does not provide global atomic locks. Communicate double-book risk honestly.
