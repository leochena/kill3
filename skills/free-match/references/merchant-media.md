# Merchant catalog & media (skill reference)

Full design: `docs/media-and-catalog.md`.

## Listing so buyers can see goods

Always fill:

1. `item.title`  
2. `item.description` (what buyers read)  
3. `item.tags`  
4. `item.attachments[]` with image `uri` + `mime`  
5. `price` + `where` (+ geo when possible)  
6. `match.vertical` / `mode`  

## CLI

```bash
python runtime/fm.py --board http://127.0.0.1:8787 have \
  --title "Veggie bowl" --price 9.5 --currency EUR \
  --desc "Quinoa chickpea tahini · vegan" \
  --tags vegan,lunch --image ./bowl.jpg \
  --lat … --lon … --vertical food_order --privacy public
```

Local `--image` uploads to `POST /api/v1/media` when `--board` is set.

## Preview

Before post, show merchant how the buyer card will look (title, price, distance placeholder, image count, first 2 description lines).
