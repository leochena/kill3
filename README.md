# free-match / kill3

> **干掉第三方平台的自由匹配协议 + 通用智能体 Skill**  
> 买家 · 卖家 · 快递/司机 —— 自由接单，不交平台租，不做软件警察。

[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](LICENSE)
[![Protocol](https://img.shields.io/badge/protocol-v1-blue.svg)](protocol/SPEC.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-purple.svg)](CONTRIBUTING.md)

**仓库:** https://github.com/leochena/kill3

---

## 我们在干什么

第三方平台靠 **垄断发现 → 抽成 → 软件监管 → 绑架信誉** 吃饭。

我们的立场：

| 原则 | 含义 |
|------|------|
| **违法是政府的事** | 软件不做违禁品警察、不强制 KYC 作为协议前提 |
| **好坏由用户评价** | 可携带的 `review`，不绑定平台黑分 |
| **交易自由匹配** | 无强制佣金、无强制支付通道、无强制托管 |
| **通用智能体可用** | 任何能加载 Skill 的 Agent 都能当节点 |

这不是又一个电商 App，而是 **开放协议 + Claude/通用 Agent Skill + 可自建的哑消息板**。

## 30 秒上线测试

```bash
git clone https://github.com/leochena/kill3.git
cd kill3

# 可选：签名身份
pip install -r runtime/requirements.txt

# 启动本地板（API + Web UI）
python runtime/server.py --port 8787
# 浏览器打开 http://127.0.0.1:8787/

# 另一终端：端到端冒烟（闲置一对多 / 外卖+骑手 / 打车抢单）
python runtime/smoke_e2e.py

# CLI 远程发单
python runtime/fm.py id new --name alice
python runtime/fm.py --board http://127.0.0.1:8787 have \
  --title "闲置键盘" --price 350 --region "上海" \
  --vertical goods_unique --mode one_to_many
python runtime/fm.py --board http://127.0.0.1:8787 list --type want,have
```

Windows 也可：`scripts\run-board.bat` 、 `scripts\smoke.bat`。

## 定位与距离

发单可写 `where.geo.lat/lon`；列表支持：

```bash
python runtime/fm.py list --type have \
  --near-lat 31.24 --near-lon 121.50 --radius-m 5000 --sort distance
```

Web UI：浏览器定位 / 地图选点 + OpenStreetMap 展示距离。详见 [docs/location.md](docs/location.md)。

## 一对一 / 一对多 / 场景

协议用 `body.match` 表达基数与业态（**板子不强制锁单，智能体按规则提示**）：

| 场景 | vertical | 默认 mode | 说明 |
|------|----------|-----------|------|
| 闲置孤品 | `goods_unique` | `one_to_many` | 多报价 → 成交一单 |
| 多库存 | `goods_stock` | `one_to_many` | 可多 deal |
| 外卖 | `food_order` | 餐 1:N + 骑手 `broadcast_claim` | 餐品与配送可拆两段 |
| 打车 | `ride` | `broadcast_claim` / `many_to_one` | 多车抢一单 |
| 跑腿 | `errand` | `one_to_many` | |
| 服务 | `service` | `one_to_many` | |

详见 [docs/match-modes.md](docs/match-modes.md)。

## 给智能体

```bash
# Claude Code
ln -sfn "$(pwd)/skills/free-match" ~/.claude/skills/free-match
# 然后 /free-match 或直接说「帮我发个闲置」
```

其他 Agent：把 `skills/free-match/SKILL.md` + `references/` 塞进系统提示即可。

## 仓库结构

```
skills/free-match/     # 可移植 Skill（任意通用智能体）
protocol/              # Free-Match v1 规范 + JSON Schema
runtime/               # 参考实现：CLI / HTTP 板 / Web UI / smoke
examples/              # 样例消息
docs/                  # 哲学、架构、匹配模式
```

## API（哑管道）

| Method | Path | 作用 |
|--------|------|------|
| GET | `/health` | 健康检查 + 明确声明无抽成/无审核/无强制 KYC |
| GET | `/api/v1/messages` | 列表 `?type=&q=&region=&summary=1` |
| POST | `/api/v1/messages` | 发消息（校验协议；拒绝 platform_fee 等字段） |
| GET | `/api/v1/messages/{id}` | 单条 |
| GET | `/api/v1/thread/{id}` | 线程 |
| GET | `/api/v1/reviews/{actor}` | 评价汇总 |

板子**只存消息**：不做推荐广告位、不抽成、不内容审查。

## 号召：一起来开源

平台不会自己消失。我们需要：

- **写协议**：更多垂直场景的 `match` 约定与例子  
- **写传输**：Nostr / Matrix / 邮件 / 蓝牙局域网适配器  
- **写客户端**：移动端、其他 Agent 框架的 Skill 包装  
- **写文档**：各地社群怎么用已有群聊当发现层  
- **跑节点**：自己挂一块公开板（记住：你是镜子，不是地主）  
- **提 PR / Issue**：想法、漏洞、互操作测试向量  

### 你可以从这里开始

1. Star & Fork → https://github.com/leochena/kill3  
2. 读 [docs/philosophy.md](docs/philosophy.md) 与 [CONTRIBUTING.md](CONTRIBUTING.md)  
3. 跑 `python runtime/smoke_e2e.py` 确认环境  
4. 开 Issue 认领，或直接 PR  

**欢迎**：协议极简主义、密码学信誉、本地优先、反租主义。  
**不欢迎**：把项目拐回「官方商城 + 抽成 + 审核后台」。

## 法律与责任

- 本软件**不**对交易合法性作判断；参与者自行遵守当地法律。  
- 纠纷走现实世界渠道；软件只提供可验证消息与评价工具。  
- MIT 许可，见 [LICENSE](LICENSE)。

## License

[MIT](LICENSE) © free-match / kill3 contributors
