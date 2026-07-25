# Assets & living showcase

This folder is the **public gallery** of free-match: diagrams, demo board dumps, and evidence from real smoke runs.  
Use it in the GitHub README, talks, and agent demos — so newcomers see **what actually runs**, not only theory.

## Gallery

| Asset | Description |
|-------|-------------|
| [diagrams/architecture.svg](diagrams/architecture.svg) | Agents ↔ dumb board ↔ optional transports |
| [diagrams/match-modes.svg](diagrams/match-modes.svg) | Cardinality cheat-sheet |
| [diagrams/food-two-stage.svg](diagrams/food-two-stage.svg) | Meal deal vs optional courier stage |
| [demo/board-snapshot.json](demo/board-snapshot.json) | Multi-message board dump (goods + food + ride + geo) |
| [demo/smoke-result.sample.json](demo/smoke-result.sample.json) | Last known good `smoke_e2e` summary shape |
| [demo/ui-map.svg](demo/ui-map.svg) | Web UI + map layout sketch (OSM display) |
| [demo/HOW_TO_RECORD.md](demo/HOW_TO_RECORD.md) | How to refresh demos / capture screenshots |

## Regenerate demo dump

```bash
# from repo root — writes assets/demo/board-snapshot.json + smoke-result.sample.json
python scripts/export_demo_assets.py
```

## Principles for assets

- **No secrets** (no private keys, no real phone numbers)  
- **No third-party trademarks/logos**  
- Prefer **global** sample places (or clearly fictional labels)  
- Show **distance** and **match mode** when relevant  
- Keep files small and text-friendly (SVG/JSON over huge binaries)

## For contributors

PRs that add:

- a new vertical fixture under `demo/fixtures/`  
- a clearer diagram  
- a short screen recording link (optional, external host)  

…are highly welcome. See [CONTRIBUTING.md](../CONTRIBUTING.md).
