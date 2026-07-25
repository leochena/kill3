# Order tracking & reminders (skill reference)

Design: `docs/order-tracking.md`.

## Commands

```bash
python runtime/fm.py --board $BOARD track <deal_or_root_id>
```

Status labels: listed → negotiating → accepted → ordered → awaiting_courier → courier_assigned → in_fulfillment → delivered → completed.

## Reminders

Agent host should schedule checks (board has no paid push):

| If | Then remind |
|----|-------------|
| bid open & half TTL | seller/buyer to respond |
| deal + food + no fulfill 20m | kitchen / courier |
| delivered + no confirm 2h | buyer to confirm |
| complete + no review 1d | leave portable review |

On each check: `track` → if status changed, notify user in their language.
