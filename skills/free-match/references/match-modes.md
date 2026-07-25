# Match modes (skill brief)

Full analysis: repo `docs/match-modes.md`.

## Always classify

1. **vertical**: goods_unique | goods_stock | food_order | ride | errand | service | bulk_rfq  
2. **mode**: one_to_one | one_to_many | many_to_one | many_to_many | broadcast_claim  
3. **max_accepts** (default 1)

State it in the user’s language in one sentence.

## Realistic defaults

| Job | vertical | mode |
|-----|----------|------|
| Unique second-hand item | goods_unique | one_to_many |
| Stocked goods | goods_stock | one_to_many (many deals OK) |
| Prepared food | food_order | meal negotiate → optional courier stage |
| Ride / lift | ride | **prefer** one_to_many offers then passenger picks; claim only if user wants grab-next |
| Errand | errand | one_to_many |
| Service | service | one_to_many |
| RFQ | bulk_rfq | one_to_many |

## Avoid unreasonable defaults

- Forcing courier on every food order  
- Treating ride as only “first claim wins” when the user wants to compare prices  
- Merging meal price + courier fee without labels  
- Pretending the board globally locks stock  

## Races

Boards are dumb. On double accept: show both deals; user chooses; optional `confirm cancelled` on the other.
