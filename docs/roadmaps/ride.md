# Roadmap — ride / lift

## User story

Passenger: “Brooklyn to JFK, 2 bags, under 55 USD.”  
Drivers offer fee+ETA; passenger picks (default), not forced first-claim.

## Now

- [x] `want` + `courier.offer` + accept + deal + fulfill  
- [x] Default mode: choose among offers  
- [x] Geo on want/offers  

## Implementation path

### Phase A — Trip schema clarity

1. Standardize `item.title` as “A → B”; put windows in `notes`.  
2. Optional `delivery.from` / `delivery.to` places with geo.  
3. Skill template for passenger/driver.  

### Phase B — Driver NL

1. “Show open rides within 3 km with budget ≥ X.”  
2. Sort by distance to pickup geo.  

### Phase C — Live feel (still peer)

1. Fulfill `picked_up` / `in_transit` / `delivered`.  
2. Optional periodic geo update messages (new optional type later — do not require).  
3. Reminders for no driver offers / no passenger confirm.  

## Done when

Smoke + UI demo: two drivers, passenger selects lower ETA, track to complete.

## Non-goals

City-scale forced dispatch monopoly, surge fee to board operator.
