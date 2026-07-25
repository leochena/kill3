# End-to-end demo (monitor meetup)

1. Ada posts `01_want_monitor.json` (optional if she found Bob's have first).
2. Bob posts `02_have_monitor.json`.
3. Ada bids `03_bid.json` at 450 CNY.
4. Bob accepts `04_accept.json`.
5. Bob (or either agent) freezes terms in `05_deal.json`.
6. Optional: Cy offers courier `08_courier_offer.json` (not used in meetup path).
7. Ada confirms `06_confirm.json` complete.
8. Ada leaves portable review `07_review.json`.

Load onto local board:

```bash
python runtime/fm.py id new --name demo
for f in examples/0*.json; do python runtime/fm.py post --file "$f" --force; done
python runtime/fm.py list --type want,have,deal,review
python runtime/fm.py thread 01demo_have_monitor01
python runtime/fm.py review-summary demo_seller_bob
```

No platform fee fields appear anywhere in the thread.
