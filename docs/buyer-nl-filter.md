# Buyer natural-language filter (using the skill)

## Goal

Buyer says plain language; agent turns it into **structured filters + ranked candidates** from free-match boards — without a platform search monopoly.

Example:

> “Find vegan lunch under 12 EUR within 2 km that can deliver in under 40 minutes.”

## Pipeline (agent)

```text
1. Parse NL → constraints
2. Query board(s) (API/CLI)
3. Score candidates (transparent formula)
4. Show table + media previews
5. Ask user which to bid / accept
6. Emit bid/accept messages
```

## Constraint extraction

| NL cue | Maps to |
|--------|---------|
| price / budget / under X | `budget` or filter `price.amount` ≤ X + currency |
| near me / within N km | `near_lat/lon` + `radius_m` |
| vegan / spicy / brand | `q` search + `tags` / description match |
| open now / tonight | `ttl_sec`, `notes`, agent clock (soft) |
| delivery / pickup | `need_courier`, `delivery.mode`, notes |
| rating | `review-summary` on `from.id` |
| vertical | food_order, goods_*, ride, … |

Agent should **echo constraints back** before searching:

```text
Filters: vertical=food_order, max_price=12 EUR, radius=2000m,
tags~vegan, need_delivery=true, sort=distance
```

## Board queries

```bash
# text + geo
python runtime/fm.py --board $BOARD list --type have \
  --q "vegan" --near-lat … --near-lon … --radius-m 2000 --sort distance

# then for top ids
python runtime/fm.py --board $BOARD get <id>
python runtime/fm.py --board $BOARD review-summary <seller_id>
```

HTTP:

```http
GET /api/v1/messages?type=have&q=vegan&near_lat=&near_lon=&radius_m=2000&sort=distance&summary=1
```

## Ranking (local, transparent — never paid)

Default skill formula (show to user):

```text
score =
  0.35 * budget_fit
+ 0.30 * distance_fit      # 1 if within radius, else decay
+ 0.20 * text_tag_overlap
+ 0.15 * reputation_hint   # 0 if no reviews
```

**Forbidden:** boost, sponsored, “featured for fee”.

## Presentation format

Always use a table:

| # | title | price | distance | tags | reviews | media | id |
|---|-------|-------|----------|------|---------|-------|-----|
| 1 | … | … | 700 m | vegan | 5★×3 | 2 imgs | fm… |

Then: “Reply 1 to bid, or tighten filters.”

## Multi-board

If user has several board URLs, query each, merge by `id`, prefer closer + more reviews. Do not pretend there is one global official index.

## Skill entry phrases

- “Find …” / “筛选 …” / “search nearby …”  
- “Cheaper than …” / “with photos” / “open to meetup only”  

Implementation detail for agents: `skills/free-match/references/buyer-nl.md`.
