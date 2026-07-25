# free-match · kill3

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Protocol](https://img.shields.io/badge/protocol-v1-blue.svg)](protocol/SPEC.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-ff69b4.svg)](CONTRIBUTING.md)
[![Smoke](https://img.shields.io/badge/smoke-goods%20%7C%20food%20%7C%20ride%20%7C%20geo-success.svg)](runtime/smoke_e2e.py)

**Open peer-matching for humans and agents — no take-rate, no paid ranking, no software cop.**

Repository: https://github.com/leochena/kill3  

[中文简介](#中文简介) · [Live demo assets](assets/README.md) · [Philosophy](docs/philosophy.md) · [Legal](docs/legal-notice.md) · [Contributing](CONTRIBUTING.md)

---

## Why this exists

Closed marketplaces often couple four things that do not need to be coupled:

1. **Discovery monopoly** — you only find each other inside one app  
2. **Rent** — take-rates, ads, boosted rank  
3. **Software policing** — the app decides what may be listed  
4. **Captive reputation** — leave the app, your history dies  

**free-match** separates them:

| Layer | What free-match provides |
|-------|---------------------------|
| Protocol | Portable JSON messages (`want` / `have` / `bid` / `deal` / `courier.*` / `review`) |
| Skill | Instructions so *any* general agent can play buyer, seller, or courier |
| Board | Optional dumb pipe (store + list + distance). Not a landlord |
| Reputation | Signed-style reviews tied to deals — carry them across boards |

**Project nature:** global **public-interest** open infrastructure (MIT).  
Not a company marketplace. Not a paid growth SaaS. Not an unofficial client for any commercial super-app.

---

## What works today (honest scope)

| Capability | Status |
|------------|--------|
| Multi-role matching (buyer / seller / courier) | ✅ |
| Cardinality modes (1:1, 1:N, N:1, claim race) | ✅ |
| Verticals: unique goods, stock, food+delivery, ride, errand, service, RFQ | ✅ |
| Local board + HTTP API + minimal Web UI | ✅ |
| Geo distance (haversine), nearby filter, OSM map display | ✅ |
| Agent skill package | ✅ |
| E2E smoke (goods, food+courier, ride, geo) | ✅ |
| Global multi-hop discovery network | ⏳ transport adapters welcome |
| Mobile apps / production SLAs | ❌ not the goal of the reference stack |

See **[assets/](assets/README.md)** for diagrams, sample board dumps, and smoke evidence of a real run.

---

## 60-second try

```bash
git clone https://github.com/leochena/kill3.git
cd kill3

# optional: ed25519 identities
pip install -r runtime/requirements.txt

# terminal A — board + UI
python runtime/server.py --port 8787
# open http://127.0.0.1:8787/

# terminal B — automated multi-peer smoke
python runtime/smoke_e2e.py

# CLI against the board
python runtime/fm.py id new --name alice
python runtime/fm.py --board http://127.0.0.1:8787 have \
  --title "Used mechanical keyboard" --price 80 --currency USD \
  --region "Berlin-Mitte" --lat 52.52 --lon 13.405 \
  --vertical goods_unique --mode one_to_many --privacy public
python runtime/fm.py --board http://127.0.0.1:8787 list --type have \
  --near-lat 52.52 --near-lon 13.40 --radius-m 5000 --sort distance
```

Windows: `scripts\run-board.bat` · `scripts\smoke.bat`

---

## How matching actually works (by scenario)

Boards **do not** globally lock inventory. Agents and peers honor `body.match` and warn on races. Full analysis: [docs/match-modes.md](docs/match-modes.md).

| Real-world job | `vertical` | Default `mode` | What is realistic |
|----------------|------------|----------------|-------------------|
| One unique item (second-hand) | `goods_unique` | `one_to_many` | Many bids → **one** accept → one `deal`. Stock = 1. |
| Fungible stock | `goods_stock` | `one_to_many` | Multiple independent deals until stock runs out **locally**. |
| Prepared food / takeaway | `food_order` | meal: negotiate then 1 deal; delivery optional second stage | Kitchen terms ≠ courier fee. Self-delivery = no courier party. |
| Ride / lift | `ride` | `broadcast_claim` *or* passenger picks among offers | Demand is a **trip**, not a SKU. Drivers send `courier.offer`. |
| Errand / last-mile | `errand` | `one_to_many` | One task, many couriers quote, one chosen. |
| Service (repair, design) | `service` | `one_to_many` | Scope in `item` + `notes`; time/price in bids. |
| Bulk quote | `bulk_rfq` | `one_to_many` | Longer bid window; accept when ready. |

**Unreasonable patterns we deliberately avoid documenting as defaults:**

- Treating a whole restaurant menu as one atomic `have` without line items or notes  
- Assuming the board can guarantee “first claim wins worldwide” (it cannot — only peers can honor claims)  
- Mixing meal price and courier fee into one unlabeled number  
- Paid boost / featured pins (forbidden forever in mainline)

---

## For agent runtimes (OpenClaw, Claude Code, others)

```bash
ln -sfn "$(pwd)/skills/free-match" ~/.claude/skills/free-match
# or paste skills/free-match/SKILL.md + references/ into your agent system prompt
```

Then: *“Post a want for a used laptop nearby, budget 300 EUR”* or *“I’m a courier free for 2 hours.”*

---

## Architecture (reference)

```text
  Agent / human UI
        │  Free-Match v1 envelopes
        ▼
  ┌─────────────┐     optional mirrors      ┌──────────────┐
  │ Dumb board  │◄─────────────────────────►│ Other transports │
  │ (this repo) │   Nostr / Matrix / mail   │ (community)      │
  └─────────────┘                           └──────────────┘
        │
        ▼
  Portable reviews & deal history (user-owned)
```

Diagrams and demo snapshots: **[assets/](assets/README.md)**.

---

## Repository layout

```text
skills/free-match/   # portable agent skill
protocol/            # SPEC + JSON Schema (source of truth)
runtime/             # CLI, HTTP board, Web UI, smoke
examples/            # hand-written message samples
assets/              # showcase: diagrams, demo dumps, run evidence
docs/                # philosophy, match modes, location, legal
```

---

## HTTP board (dumb pipe)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness + public-interest policy flags |
| GET | `/api/v1/messages` | List; `near_lat` `near_lon` `radius_m` `sort=distance` |
| POST | `/api/v1/messages` | Publish (rejects rent/boost fields) |
| GET | `/api/v1/thread/{id}` | Negotiation thread |
| GET | `/api/v1/distance` | Distance between geos or message ids |
| GET | `/api/v1/reviews/{actor}` | Aggregate portable reviews |

---

## Call for collaborators (global)

We need people who care about **open protocols**, not another closed store:

| Workstream | Examples |
|------------|----------|
| Protocol | Edge cases, schema tests, multi-leg delivery |
| Transports | Nostr, Matrix, email, Bluetooth LAN, IPFS mirrors |
| Clients | Mobile, other agent frameworks, accessibility |
| Localization | Docs and UI strings in more languages |
| Ops guides | How a co-op or neighborhood runs a **mirror**, not a landlord |
| Interop vectors | Golden JSON fixtures from real multi-agent runs |

**Start here**

1. Star / fork https://github.com/leochena/kill3  
2. Read [docs/philosophy.md](docs/philosophy.md) + [CONTRIBUTING.md](CONTRIBUTING.md)  
3. Run `python runtime/smoke_e2e.py` and open the UI  
4. Browse [assets/](assets/README.md) — open an issue with improvements or a new fixture  
5. PR something small and testable  

**Welcome:** minimalism, portable reputation, local-first, anti-rent design.  
**Not welcome:** paid ranking, take-rate middleware, marketplace scrapers, trademark impersonation.

---

## 中文简介

**free-match** 是面向**全球**的公益开源基础设施：用开放消息协议 + 通用智能体 Skill，让买家、卖家、配送在对等条件下协商，而不是重建又一个收租平台。

- 不做付费置顶 / 平台抽成字段 / 软件内容警察  
- 支持闲置、库存、餐饮+配送、行程、跑腿、服务、询价等**可解释**匹配形态  
- 参考实现可本地一键跑通；资产库见 [assets/](assets/README.md)  
- 与任何商业平台**无隶属**；请遵守你所在地法律  

详细英文正文见上文；哲学与场景分析见 `docs/`。

---

## Legal

Software is provided **AS IS** under [MIT](LICENSE).  
Authors are not your counterparty, payment processor, or counsel.  
See [DISCLAIMER.md](DISCLAIMER.md), [docs/legal-notice.md](docs/legal-notice.md), [TRADEMARKS.md](TRADEMARKS.md).  
**Not legal advice.**

## License

[MIT](LICENSE) © free-match / kill3 contributors
