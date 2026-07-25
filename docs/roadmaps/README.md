# Roadmap index — implementation paths by scenario

These are **engineering roadmaps** for contributors and agent builders.  
Philosophy: [origin.md](../origin.md) · Match shapes: [match-modes.md](../match-modes.md)

| Roadmap | Focus |
|---------|--------|
| [00-core.md](00-core.md) | Protocol, board, skill, assets, global hygiene |
| [goods.md](goods.md) | Second-hand & stocked goods |
| [food.md](food.md) | Food / takeaway + optional courier |
| [ride.md](ride.md) | Rides / lifts |
| [errand-service.md](errand-service.md) | Errands & services |
| [media.md](media.md) | Photos, catalogs, media hosting |
| [buyer-nl.md](buyer-nl.md) | Natural-language buyer search |
| [order-tracking.md](order-tracking.md) | Status + reminders |
| [maps.md](maps.md) | Free map stack |

## How to read a roadmap

Each file uses:

- **Now** — already in repo / smoke  
- **Next** — small PRs, high value  
- **Later** — larger work  
- **Done when** — acceptance checks  
- **Non-goals** — will not do in mainline  

## Suggested contributor order

1. Media upload + UI gallery (unlocks real merchant demos)  
2. `fm track` / status derive (unlocks trust in multi-step orders)  
3. Buyer NL skill polish + fixture tests  
4. Configurable free tiles + optional Nominatim  
5. Transport adapters (Nostr/Matrix) for multi-board discovery  
