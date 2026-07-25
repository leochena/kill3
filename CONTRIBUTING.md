# Contributing to free-match (kill3)

Thank you. This is a **global public-interest** protocol project — success looks like many interoperable peers, not one rent-collecting app.

## North star

1. **No intermediary rent** in protocol/mainline board  
2. **No paid discovery** (boost, sponsored rank, traffic packs)  
3. **No default software cop** as protocol  
4. **Portable reputation** via messages  
5. **Agent-first** portable skill  
6. **Dumb pipes** for boards  
7. **Lawful neutral tooling** — no scrapers, no trademark impersonation, no “unofficial Brand X client”  

PRs that violate the above are closed with a pointer here.

## Legal / trademarks

Read [docs/legal-notice.md](docs/legal-notice.md), [DISCLAIMER.md](DISCLAIMER.md), [TRADEMARKS.md](TRADEMARKS.md).  
Docs are hygiene, not legal advice.

## Dev loop

```bash
git clone https://github.com/leochena/kill3.git
cd kill3
pip install -r runtime/requirements.txt   # optional
python runtime/smoke_e2e.py
python runtime/server.py --port 8787
python scripts/export_demo_assets.py      # refresh assets/demo when scenarios change
```

### Protocol changes

1. Update `protocol/SPEC.md` + schemas  
2. Sync skill references + `docs/match-modes.md`  
3. Add examples or extend smoke  
4. Prefer backward compatible `v: 1` or document `v: 2`  

### Runtime

- No take-rate, paid rank, mandatory login, or content police by default  
- User-local filters OK if off by default  
- New transports: separate modules  

### Assets / showcase

- Add diagrams or fixtures under `assets/`  
- Keep secrets and third-party logos out  
- Prefer global/fictional sample geography  

### PR tips

- Small, testable; name the **vertical** and **mode**  
- English for protocol fields; any language for human docs  
- Do not commit private keys under `runtime/board/identities/`  

## Conduct

Be sharp on ideas, kind to people. Do not turn the project into an enforcement arm of any state or firm.

## License

Contributions under **MIT** (same as the repository).
