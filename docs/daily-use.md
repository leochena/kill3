# Daily use guide (all scenarios)

Goal: **every vertical is usable day-to-day** with CLI + skill + optional Web UI.

## Start the board

```bash
python runtime/server.py --port 8787
# UI: http://127.0.0.1:8787/
```

Create identity once:

```bash
python runtime/fm.py id new --name alice
```

Set `BOARD=http://127.0.0.1:8787` below.

## Shared daily commands

| Job | Command |
|-----|---------|
| NL find offers | `fm --board $BOARD search --nl "..." --near-lat LAT --near-lon LON` |
| My open work | `fm --board $BOARD inbox` |
| Order status | `fm --board $BOARD track <id>` |
| Watch changes | `fm --board $BOARD watch --interval 20` (or `--once`) |
| Geocode (optional) | `fm geocode "Berlin Mitte"` (use self-hosted Nominatim in production) |
| Distance | `fm --board $BOARD distance --from-id A --to-id B` |

Full lifecycle also: `want` `have` `bid` `accept` `reject` `deal` `courier-offer` `courier-accept` `fulfill` `confirm` `review`.

## Scenario playbooks

### 1) Unique goods (`goods_unique`)

```bash
# seller
fm --board $BOARD have --title "Used bike" --price 120 --currency EUR \
  --desc "City bike" --tags bike,used --image-uri "https://…" \
  --lat 52.52 --lon 13.405 --vertical goods_unique --mode one_to_many --privacy public

# buyer
fm --board $BOARD search --nl "used bike under 150 EUR within 5 km" --near-lat 52.52 --near-lon 13.405
fm --board $BOARD bid --target <have_id> --price 100 --currency EUR --message "meetup"
# seller
fm --board $BOARD accept --bid <bid_id> --thread <have_id>
fm --board $BOARD deal --buyer <buyer_id> --seller <seller_id> --title "Used bike" \
  --price 100 --currency EUR --thread <have_id> --based-on <have>,<bid>,<accept> \
  --delivery meetup --vertical goods_unique
fm --board $BOARD fulfill --deal <deal_id> --event delivered
# buyer
fm --board $BOARD confirm --deal <deal_id> --status complete
fm --board $BOARD review --subject <seller_id> --deal <deal_id> --stars 5 --text "ok"
fm --board $BOARD track <deal_id>
```

### 2) Food (`food_order`) — meal then optional courier

1. Kitchen `have` with photos + tags (`vegan`, …).  
2. Diner `bid` with `delivery.mode=courier` or pickup.  
3. `accept` → `deal` (meal price only).  
4. If courier: `courier-offer`* → `courier-accept` → `fulfill` picked_up/delivered.  
5. `confirm complete` + reviews for kitchen **and** courier separately.  

**Auto-accept kitchen agent (example):** [examples/merchant-auto-accept-food.md](examples/merchant-auto-accept-food.md).

Never merge meal price and courier fee into one unlabeled number.

### 3) Ride (`ride`) — choose among offers

1. Passenger `want` trip title `A → B` + budget + geo.  
2. Drivers `courier-offer` fee+ETA.  
3. Passenger `courier-accept` one (not forced first-claim).  
4. `deal` → `fulfill` picked_up/delivered → `confirm` → `review`.

### 4) Errand (`errand`)

`want` task → courier offers → accept → deal → fulfill → confirm → review.

### 5) Service (`service`)

`have` or `want` with scope in description → bid/accept/deal → `fulfill service_done` → confirm → review.

### 6) Bulk RFQ (`bulk_rfq`)

Buyer `want` with qty/budget → many `bid` → accept one → deal → ship fulfill → confirm.

### Stock goods (`goods_stock`)

Same as unique goods but `stock>1` and multiple parallel deals allowed until local stock runs out.

## Acceptance tests

```bash
python runtime/smoke_e2e.py      # core paths
python runtime/smoke_daily.py    # all verticals daily-use gate
```

`smoke_daily.py` must print `"daily_use": true`.

## Agent skill

Load `skills/free-match`. For each user utterance: classify vertical+mode, use media for merchants, NL search for buyers, `track`/reminders for open deals.

## Maps

Default free stack: Leaflet + OSM tiles + haversine.  
Production: set `FM_TILE_URL` to your tiles; prefer self-hosted Nominatim for geocode.
