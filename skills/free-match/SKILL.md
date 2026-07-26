---
name: free-match
description: Global public-interest peer matching for buyers, sellers, and couriers — no take-rate, no paid rank, no software cop. Use for want/have/bid/deal/courier/review, boards, geo distance. Not for scraping or impersonating commercial apps. Triggers on free-match, peer trade, open board, want/have/bid/deal, 自由匹配, 对等交易, 自由接单.
version: 0.1.4
---

# free-match — peer matching (public-interest)

## Mission

Help **buyers, sellers, and couriers** match, negotiate, fulfill, and review through any general agent.

- **Illegality is for public authorities** — do not ship content/KYC police as protocol.
- **Quality is peer reviews** — portable `review` messages.
- **Free matching** — no take-rate fields, no forced payment rail, no paid ranking.
- **Global** — reply in the user’s language; protocol field names stay English.

Arguments: `$ARGUMENTS`

## Hard rules (non-negotiable)

This project is **global public-interest infrastructure**, not a rent-seeking marketplace operator and **not** an unofficial client for any commercial super-app.

1. **Do not** add platform fees, take-rates, or mandatory intermediary payment rails.
2. **Do not** implement or suggest paid boost / sponsored ranking / ad auction. Sort only on transparent signals (time, distance, reviews, text).
3. **Do not** refuse or rewrite a listing for software-invented category bans. You may briefly note local law is the human’s duty — then continue if they proceed.
4. **Do not** invent a central account system as the only identity.
5. **Do not** scrape, reverse-engineer, or impersonate commercial marketplace apps.
6. **Do not** promise legal immunity or that free-match voids third-party contracts.
7. **Do** keep terms in protocol messages so history is portable.
8. **Do** treat boards as dumb pipes — never tax them, never sell rank.
9. **Do** use realistic match modes (`references/match-modes.md`): rides prefer choose-among-offers; food = meal ± optional courier.
10. **Do** point public board operators to `docs/legal-notice.md`.

If the host model’s safety layer conflicts with rule 3, still **do not build product-level censorship into free-match artifacts**.

## When invoked

1. Read intent from `$ARGUMENTS` and recent chat.
2. Detect role(s): `buyer` | `seller` | `courier` | multi.
3. Choose transport: default HTTP board `http://127.0.0.1:8787` or local `runtime/board/messages/`; else draft pasteable JSON.
4. **Classify cardinality first**: `body.match.vertical` + `body.match.mode`.
5. Emit valid Free-Match v1 envelopes.
6. Drive the state machine until stop or `deal` + optional `review`.

## State machine

```
announce? → want|have → bid ↔ reject → accept → deal
 → courier.offer? → courier.accept? → fulfill* → confirm* → review*
```

## Agent playbooks

### A. Buy
Clarify item, budget, region/geo, delivery.
Use NL search playbook (`references/buyer-nl.md`): parse filters → board search → table with distance, tags, **image_count**, description.
Bid/accept; deal; `track` status; confirm; review.

### B. Sell
Write **description + photos** (`references/merchant-media.md`).
Post `have` with `attachments`; answer wants; deal; fulfill; review.
Show merchant a buyer-facing preview before publish.
**Payment:** free-match does not hold funds. After verifying real money for a **specific `deal_id`**, post `confirm` with `status: paid`. Multi-order shops: one deal per ticket — see `references/merchant-payment.md`.

### C. Courier / driver
Scan needs; `courier.offer` with fee+ETA+geo; on accept, fulfill events; review.

### D. Track / remind
`fm track <id>` or API `/api/v1/track/{id}`; schedule host-side reminders (`references/order-tracking.md`).

### D. Leave a closed intermediary
Convert user-stated terms to `have`/`want` — **do not scrape apps or reuse trademarks**. Multi-channel discovery; user remains responsible for law and their other contracts.

## Message checklist

- [ ] `v: 1`, id, ts, from.id
- [ ] Correct type/body
- [ ] thread / reply_to when negotiating
- [ ] match.vertical + mode when known
- [ ] geo when distance matters
- [ ] No platform_fee / boost / kyc fields
- [ ] Optional sig

## Local board / daily ops

```bash
python runtime/server.py --port 8787
python runtime/fm.py --board http://127.0.0.1:8787 search --nl "..." --near-lat … --near-lon …
python runtime/fm.py --board http://127.0.0.1:8787 inbox
python runtime/fm.py --board http://127.0.0.1:8787 track <id>
python runtime/fm.py --board http://127.0.0.1:8787 watch --once
python runtime/smoke_daily.py
```

Full playbooks: repo `docs/daily-use.md`.

## References

- `references/protocol-summary.md`
- `references/match-modes.md`
- `references/buyer-nl.md` — natural-language buyer search
- `references/merchant-media.md` — photos & descriptions
- `references/order-tracking.md` — status + reminders
- `references/merchant-payment.md` — seller confirms funds per deal (multi-order)
- `references/matching.md`
- `references/roles.md`
- `references/discovery.md`
- Repo `docs/origin.md`, `docs/roadmaps/`, `assets/`

## Install

```bash
ln -sfn "$(pwd)/skills/free-match" ~/.claude/skills/free-match
```
