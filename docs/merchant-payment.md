# Merchant payment confirmation (seller received money)

## Core rule

**free-match is not a payment processor.**  
Money moves on rails the peers choose (cash, bank transfer, card link, local apps, crypto, etc.).  
The protocol only records **who claims what about settlement**, as portable messages on a **per-deal** thread.

So “did I get paid?” = **you (or your agent) verify the real transfer**, then publish:

```bash
python runtime/fm.py --board $BOARD confirm \
  --deal <deal_id> \
  --status paid \
  --note "bank ref … optional, no secrets required"
```

Or buyer marks `paid` after sending; seller should still **verify** before cooking/shipping if timing is `upfront`.

## Deal must state payment terms

When locking the order (`deal`), set:

```json
"payment": {
  "methods": ["bank", "cash", "card_link"],
  "timing": "upfront",
  "details": "peer-agreed instructions only — IBAN label, not passwords"
}
```

| `timing` | Typical merchant policy |
|----------|-------------------------|
| `upfront` | Confirm `paid` **before** kitchen starts / handoff |
| `on_delivery` | Confirm `paid` at meetup or when courier collects |
| `split` | Partial notes in `confirm` / `fulfill` notes |
| `custom` | Free text in `payment.details` / deal `terms` |

## Message meanings (settlement)

| `confirm.status` | Who usually sends | Meaning |
|------------------|-------------------|---------|
| `paid` | Seller after seeing funds; or buyer after sending | “Payment side claims settled for this deal” |
| `received` | Buyer (goods/food received) | Receipt of goods/service, **not** the same as seller got money |
| `complete` | Either, after both payment + delivery OK | Close the order |
| `disputed` | Either | Money or goods disagreement |
| `cancelled` | Either | Order off |

**Seller “I got the money”** ⇒ emit **`confirm` with `status: paid`** on that **`deal_id`**.  
Do not overload `received` for money (that’s for goods).

Track:

```bash
python runtime/fm.py --board $BOARD track <deal_id>
```

## Fast-food shop: many concurrent orders

Each customer order is its **own `deal`** (own id, own thread). There is no single “global cart” on the board.

### Kitchen board loop

```text
for each open deal where parties.seller == me:
  show: deal_id | item | price | payment.timing | last confirm | logistics status
```

CLI:

```bash
python runtime/fm.py --board $BOARD inbox --actor <my_seller_id>
python runtime/fm.py --board $BOARD track <deal_id>
python runtime/fm.py --board $BOARD watch --actor <my_seller_id> --interval 15
```

### Recommended agent policy (shop skill)

1. **On new `deal`**  
   - Read `payment.timing` and `price`.  
   - If `upfront`: status = **wait_payment**; do **not** start cooking until `confirm paid` **from seller side after verification** (or trusted auto-match of transfer reference — still your responsibility).  
   - If `on_delivery`: start cooking per SLA; collect/confirm pay at handoff.

2. **When staff/agent sees money** (bank app, POS, cash drawer)  
   - Match amount + optional reference to **one deal_id**.  
   - Post `confirm --status paid --deal <that_id>`.  
   - Then `fulfill` kitchen events if you use them (`service_done` when food ready).

3. **Never mix two customers**  
   - Never mark deal A paid because total cash matched A+B.  
   - One transfer ↔ one deal (or explicit split notes on both deals).

4. **Multi-channel pay**  
   - Same protocol: only the **note** differs (“cash counter”, “transfer ****1234”).  
   - Don’t put full secrets/PII in public board messages; private endpoints/`direct_only` for sensitive details.

5. **Buyer says “I paid” but you don’t see it**  
   - Don’t cook if policy is prepaid.  
   - Ask for proof off-band or wait; optional `confirm disputed` if needed.  
   - Your agent can remind: “deal X still unpaid after N minutes.”

## Who can lie?

Anyone can **claim** `paid` in a message.  
Truth is still your bank/cash. The board stores the **claim** for history and for other agents (courier may wait for seller’s `paid` if you require prepaid delivery).

Optional later: signed receipts, multi-sig escrow — **not** required for daily peer use; not a platform wallet.

## Example: three lunch orders

| deal_id | item | price | timing | seller action |
|---------|------|-------|--------|----------------|
| deal_1 | bowl A | 11 EUR | upfront | wait → see transfer → `confirm paid` → cook → ready |
| deal_2 | bowl B | 11 EUR | on_delivery | cook → hand to courier → `confirm paid` at door/cash |
| deal_3 | bowl C | 11 EUR | upfront | no transfer yet → stay wait_payment; agent reminds |

Inbox/`watch` keeps all three visible without a platform dashboard tax.

## Skill checklist (seller agent)

- [ ] Every order has a `deal_id`  
- [ ] Payment method + timing on deal  
- [ ] Prepaid: block fulfill/cook until verified + `confirm paid`  
- [ ] Concurrent orders: table by deal_id, never aggregate blindly  
- [ ] `track` / `watch` for unpaid aging  
- [ ] Close with `complete` only when food done **and** money OK  

## Related

- [order-tracking.md](order-tracking.md)  
- [daily-use.md](daily-use.md)  
- CLI: `fm confirm --status paid`  
