# Daily-use acceptance criteria

**Goal:** 全部场景日常可用 — all scenarios usable day-to-day.

## Gate commands

```bash
python -m py_compile runtime/fmlib.py runtime/fm.py runtime/server.py runtime/smoke_daily.py
python runtime/smoke_e2e.py
python runtime/smoke_daily.py
```

## Required outcomes (`smoke_daily.py`)

| Vertical | Must complete lifecycle | Notes |
|----------|-------------------------|-------|
| goods_unique | have→bid→accept→deal→fulfill→confirm→review | images in summary |
| food_order | meal deal + courier stage + dual reviews path | awaiting_courier intermediate |
| ride | want→offers→accept→deal→fulfill→confirm | choose-among-offers |
| errand | want→courier→deal→fulfill→confirm | |
| service | have→bid→deal→service_done→confirm→review | |
| bulk_rfq | want→multi bid→accept→deal→ship→confirm | |
| media | POST /api/v1/media works | |
| anti-rent | boost/platform_fee rejected | |

## Operator checklist (manual, 10 min)

1. Start board, open UI, upload a photo listing.  
2. `fm search --nl` finds it with distance when geo set.  
3. Complete one goods or food flow via CLI.  
4. `fm track` shows Completed.  
5. `fm inbox` lists my open/closed items.  

## Non-claim

Daily-usable **reference stack** ≠ global user acquisition network. Discovery still needs your boards/communities.
