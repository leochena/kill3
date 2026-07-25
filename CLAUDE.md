# free-match (kill3)

## Goal

Global **public-interest** free-match: buyers, sellers, couriers peer-match without intermediary rent or software policing.

- Public-interest infrastructure — not a commercial marketplace operator  
- Law is for public authorities; quality is peer reviews  
- Free matching; no paid ranking  
- Any general agent can load the skill  

## Non-goals

- Take-rate, forced payment rails, forced escrow  
- Paid boost / sponsored rank / ad auctions  
- Default content police / mandatory KYC as protocol  
- Closed single-vendor app as the product  
- Scrapers or unofficial clients for commercial marketplaces  
- Promising lawsuit immunity  

## Architecture prefs

1. Skill-first: `skills/free-match/`  
2. Protocol truth: `protocol/`  
3. Local-first board: `runtime/`  
4. Optional signatures; portable reviews  
5. Showcase evidence: `assets/`  

## Working rules

- No platform risk-control / content ban engines as core  
- No paid discovery ever in mainline  
- Match scenarios must stay realistic (see `docs/match-modes.md`)  
- Docs are **global**; avoid single-country product framing  
- Legal hygiene: `docs/legal-notice.md`  
- Sync schema ↔ skill ↔ examples ↔ assets export when protocol changes  
- Prefer project-local tooling; if `.venv` appears later, use it  

## Key paths

| Path | Role |
|------|------|
| `skills/free-match/SKILL.md` | Agent skill |
| `protocol/` | SPEC + schemas |
| `runtime/` | CLI, board, UI, smoke |
| `assets/` | Public gallery / run evidence |
| `docs/` | Philosophy, match modes, location, legal |
