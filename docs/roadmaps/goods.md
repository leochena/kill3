# Roadmap — goods (unique & stock)

## User story

Merchant: “Sell this used keyboard with photos.”  
Buyer: “Find keyboards under 100 EUR within 5 km.”

## Now

- [x] `have` / `want` / `bid` / `accept` / `deal` / `review`  
- [x] `goods_unique` + `goods_stock` modes  
- [x] Geo + distance sort  

## Implementation path

### Phase A — Catalog quality (Next)

1. Merchant skill: force description ≥ N chars when photos present.  
2. `--image-uri` / media upload on `have`.  
3. UI detail drawer with gallery.  
4. Example fixtures in `assets/demo/fixtures/goods/`.  

### Phase B — Buyer NL

1. Map “used / like new / sealed” → `condition` + q.  
2. Meetup vs ship filters from NL.  
3. Table output with distance + media count.  

### Phase C — Fulfillment

1. `fulfill shipped|delivered` for ship mode.  
2. Track status for buyer/seller agents.  
3. Reminder: deal age &gt; 48h without confirm.  

## Done when

Smoke + manual UI: photo `have` → NL find → bid → deal → confirm → review.

## Non-goals

Platform escrow, paid homepage slots.
