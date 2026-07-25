# Roadmap — order tracking & reminders

## Now

- [x] Message types for full lifecycle  
- [x] Doc status model [order-tracking.md](../order-tracking.md)  

## Next

1. `fmlib.derive_status(thread_msgs)`  
2. `fm track <id>` prints status + timeline  
3. `fm watch --actor-id` polls and prints diffs  
4. UI badge on thread view  
5. Skill: reminder table for host schedulers  

## Later

- Web Push / email adapters (optional, user-owned keys)  
- Desktop notifications via agent host only  

## Done when

Buyer and merchant can answer “where is this order?” from one command without reading raw JSON.
