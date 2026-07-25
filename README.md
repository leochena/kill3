# free-match · kill3

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Protocol](https://img.shields.io/badge/protocol-v1-blue.svg)](protocol/SPEC.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-ff69b4.svg)](CONTRIBUTING.md)

**Open peer-matching for humans and agents — no take-rate, no paid ranking, no software cop.**

https://github.com/leochena/kill3  

[Why this exists](#why-this-exists) · [What you can do now](#what-you-can-do-now) · [Roadmaps](docs/roadmaps/README.md) · [Assets](assets/README.md) · [中文](#中文简介)

---

## Why this exists

Around the world, closed delivery, ride, and retail apps often:

1. **Charge high “management” / commission fees**  
2. **Monopolize discovery** — you only meet counterparties inside their app  
3. **Squeeze merchants and drivers** with ranking rules and ads  
4. **Trap reputation** so leaving means starting from zero  

Matching should not require a permanent landlord.  
With modern **agents + LLMs**, peers can negotiate in natural language and structured messages **directly**:

```text
merchant agent  ←→  free-match protocol  ←→  buyer agent
                           ↕
                    courier / driver agent
```

**free-match** is the **public-interest open language + skill + reference board** for that.  
Not another rent-seeking marketplace. Not a scraper for commercial super-apps.

Full story: [docs/origin.md](docs/origin.md).

---

## What you can do now

| Need | How |
|------|-----|
| **Merchant: text + photos** | `item.description` + `item.attachments[]`; UI upload → `/media/`; CLI `--image` / `--image-uri` · [docs/media-and-catalog.md](docs/media-and-catalog.md) |
| **Buyer: NL filter** | `fm search --nl "vegan under 12 EUR within 2km" --near-lat …` · transparent rank · [docs/buyer-nl-filter.md](docs/buyer-nl-filter.md) |
| **Order status + reminders** | `fm track <id>` / `GET /api/v1/track/{id}`; agent host schedules reminders · [docs/order-tracking.md](docs/order-tracking.md) |
| **Distance / map** | Haversine + Leaflet; free OSM tiles (`FM_TILE_URL`); GPS/map pick · [docs/maps-free.md](docs/maps-free.md) |
| **Scenarios** | goods, food±courier, ride (choose among offers), errand, service · [docs/match-modes.md](docs/match-modes.md) |
| **Per-scenario build plan** | [docs/roadmaps/](docs/roadmaps/README.md) — Now / Next / Later / Done when |

---

## 60-second try

```bash
git clone https://github.com/leochena/kill3.git && cd kill3
pip install -r runtime/requirements.txt   # optional

python runtime/server.py --port 8787
# UI http://127.0.0.1:8787/

python runtime/smoke_e2e.py
python runtime/fm.py id new --name alice
python runtime/fm.py --board http://127.0.0.1:8787 have \
  --title "Veggie bowl" --price 9.5 --currency EUR --desc "Vegan quinoa bowl" \
  --tags vegan,lunch --image-uri "https://picsum.photos/seed/bowl/400/300" \
  --region "Lisbon" --lat 38.71 --lon -9.14 --vertical food_order --privacy public
python runtime/fm.py --board http://127.0.0.1:8787 search \
  --nl "vegan lunch under 12 EUR within 3 km" --near-lat 38.71 --near-lon -9.14
```

---

## Agent skill

```bash
ln -sfn "$(pwd)/skills/free-match" ~/.claude/skills/free-match
```

---

## Call for collaborators

Protocol, transports, localization, co-op board ops, fixtures, clients — see [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/roadmaps/](docs/roadmaps/README.md).

**Welcome:** anti-rent infrastructure. **Not welcome:** paid boost, take-rate middleware, scrapers.

---

## 中文简介

很多人受不了第三方平台**管理费/抽成过高、垄断流量、商家与运力被规则左右**。外卖、打车等场景里，真正创造价值的是买卖与配送，不是中介房东。

智能体已能用自然语言理解需求并维护结构化对话——**撮合不必再交给收租平台**。  
**free-match** = 开放协议 + 通用 Skill + 可自建哑板：商品图文、买家自然语言筛选、订单状态跟踪、免费地图距离；主线永不做付费置顶。

详见 [docs/origin.md](docs/origin.md) 与 [docs/roadmaps/](docs/roadmaps/README.md)。

---

## Legal

MIT · AS IS · [DISCLAIMER.md](DISCLAIMER.md) · [docs/legal-notice.md](docs/legal-notice.md) · [TRADEMARKS.md](TRADEMARKS.md)  
**Not legal advice.**
