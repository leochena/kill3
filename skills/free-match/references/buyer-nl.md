# Buyer NL (skill reference)

Full design: repo `docs/buyer-nl-filter.md`.

## When buyer speaks naturally

Examples:

- "Find vegan lunch under 12 EUR within 2 km"
- "Used keyboard near me under 100"
- "Ride to the airport under 55 USD"

## Steps

1. Echo parsed filters in one line.  
2. Call board:

```bash
python runtime/fm.py --board $BOARD search --nl "..." --near-lat LAT --near-lon LON
```

or `list` with `--q` / geo flags, then rank mentally with the transparent score.

3. Present a **table**: title | price | distance | tags | images | reviews | id  
4. Include description snippet and image count from `attachments`.  
5. Ask which row to bid on.  
6. Emit `bid` / later `accept` / `deal`.

## Never

- Invent photos or prices not in messages  
- Paid ranking  
- Scrape commercial apps for listings  
