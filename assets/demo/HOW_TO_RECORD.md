# How to refresh demo assets

## Automated dump

```bash
python scripts/export_demo_assets.py
```

Writes:

- `assets/demo/board-snapshot.json` — messages after multi-scenario seed  
- `assets/demo/smoke-result.sample.json` — smoke summary  

Commit when the public gallery should update.

## Optional screenshots

1. `python runtime/server.py --port 8787`  
2. Open `http://127.0.0.1:8787/`  
3. Use browser locate or map pick; publish a public geo `have`  
4. Capture window (PNG) into `assets/demo/screenshots/` if desired  
5. **Do not** include personal addresses, faces, or API keys  

## Rules

- Fictional or generic region labels preferred  
- No third-party marketplace logos  
- Prefer SVG/JSON for git-friendliness  
