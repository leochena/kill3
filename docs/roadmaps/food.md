# Roadmap — food / takeaway

## User story

Kitchen posts bowls with photos; diner NL-filters vegan nearby; optional courier quotes separately.

## Now

- [x] Two-stage model documented (meal ± courier)  
- [x] Smoke food path  
- [x] Match modes corrected (courier not mandatory)  

## Implementation path

### Phase A — Menu as media

1. Per-dish `have` with image attachments.  
2. Tags: vegan, halal, spicy, …  
3. `notes`: prep time, allergens (free text).  

### Phase B — Diner agent

1. NL: diet + budget + radius + delivery/pickup.  
2. Never merge meal price + courier fee in one column.  
3. If delivery: second search for `courier.offer` on deal.  

### Phase C — Kitchen ops

1. Merchant view: open deals by status.  
2. Fulfill `service_done` when food ready for pickup.  
3. Reminders: unaccepted order, courier late.  

## Done when

Demo assets show Lisbon-style bowl with image, distance, and optional courier fee column.

## Non-goals

Platform fleet dispatch tax, dark-kitchen exclusive lock-in protocol.
