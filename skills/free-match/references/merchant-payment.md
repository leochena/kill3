# Seller payment confirmation (skill)

Full doc: repo `docs/merchant-payment.md`.

## When seller asks “did I get paid?” / multi-order shop

1. **free-match does not move money.** Peers pay outside (cash, bank, …).  
2. Each customer order = **one `deal_id`**.  
3. After **you verify** funds for that deal, post:

```text
confirm { deal_id, status: "paid", note?: "optional ref" }
```

CLI: `fm confirm --deal <id> --status paid`

4. Use `received` only for **goods received** (usually buyer).  
5. Use `complete` when payment **and** fulfillment are OK.  
6. Concurrent orders: `inbox` / `watch` / table by deal_id — **never** mark the wrong deal paid.

## Fast food policy defaults (suggest, user can override)

- Delivery prepaid → wait for seller-verified `paid` before cooking.  
- Counter / on_delivery → cook; confirm `paid` at handoff.  
- Unpaid aging → remind buyer; don’t start prepaid tickets.

## Buyer claims paid, seller doesn’t see it

Do not treat buyer-only claim as final for prepaid. Wait for verification or dispute.
