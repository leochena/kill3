# Match modes (skill brief)

Read full doc: repo `docs/match-modes.md`.

## Always classify

When user speaks, emit in working notes:

1. **vertical**: goods_unique | goods_stock | food_order | ride | errand | service | bulk_rfq  
2. **mode**: one_to_one | one_to_many | many_to_one | many_to_many | broadcast_claim  
3. **max_accepts** (default 1)

Say it out loud to the user, e.g.  
「按**闲置孤品 / 一对多**处理：可以收多个报价，最终只锁一单。」  
「按**打车 / 抢单**处理：多车可报价，你选一辆（或先到先得本地承认）。」  
「按**外卖**处理：先定餐品，再单独匹配骑手。」

## Quick map

| 用户说法 | vertical | mode |
|----------|----------|------|
| 出闲置/收二手 | goods_unique | one_to_many |
| 店铺有货多件 | goods_stock | one_to_many |
| 点外卖/送餐 | food_order | meal 1:N then courier claim |
| 打车/网约车 | ride | broadcast_claim |
| 跑腿 | errand | one_to_many |
| 找人修/设计 | service | one_to_many |
| 批量询价 | bulk_rfq | one_to_many |

## Race conditions

Boards are dumb: **no global lock**. If two accepts race, present both deals and let the user choose which to honor; mark the other cancelled via `confirm status=cancelled` if they want history clean.
