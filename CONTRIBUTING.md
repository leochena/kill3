# Contributing to free-match (kill3)

先谢谢你。这个项目要靠很多人才能从「协议 demo」长成「到处能用的自由匹配层」。

## 北极星

本仓库是 **公益项目 / 公共协议基础设施**，不是要运营收租的 App 公司。

1. **无平台租** — 不引入强制佣金、强制支付、强制唯一中继。  
2. **无流量变现** — 不做付费置顶、竞价排名、广告位、推广通、会员加权排序。  
3. **无软件监管** — 不把违禁品清单 / KYC / 内容审核做成协议或默认服务器逻辑。  
4. **信誉可携带** — 评价是消息，不是服务器黑箱分。  
5. **智能体优先** — Skill + 开放 JSON，任何通用 Agent 都能当节点。  
6. **哑管道板** — 中继只存取消息；发现可以有很多门。  
7. **合法中立工具** — 不做第三方平台爬虫/破解/商标仿冒；不把「搞垮某公司」写成功能。

违反以上方向的 PR（付费置顶、平台爬虫、仿冒商标等）会被关闭并说明原因。

法律与商标： [docs/legal-notice.md](docs/legal-notice.md)、[TRADEMARKS.md](TRADEMARKS.md)、[DISCLAIMER.md](DISCLAIMER.md)。

## 开发流程

```bash
git clone https://github.com/leochena/kill3.git
cd kill3
pip install -r runtime/requirements.txt   # optional pynacl
python runtime/smoke_e2e.py               # must stay green
python runtime/server.py --port 8787      # manual UI test
```

### 改协议

1. 更新 `protocol/SPEC.md` 与 `protocol/schemas/`  
2. 同步 `skills/free-match/references/` 与 `docs/`  
3. 增加 `examples/` 或扩展 `runtime/smoke_e2e.py`  
4. 保持 **向后兼容** 或明确 `v: 2` 迁移说明  

### 改 runtime

- 不要加 `platform_fee` / 审核拦截 / 强制登录。  
- 用户本地偏好（个人黑名单）可以，须默认关闭且非协议强制。  
- 新传输适配器：独立模块，CLI 用 `--board` 或 endpoint 配置接入。

### PR 建议

- 小而可测；说明 **场景**（闲置 / 外卖 / 打车…）与 **基数**（1:1 / 1:N / 抢单）。  
- 中英文均可；协议字段名保持英文。  
- 不要提交 `runtime/board/identities/*` 私钥或真实个人信息。

## Issue 标签（建议）

- `protocol` `runtime` `skill` `transport` `docs` `good first issue` `vertical:ride` …

## 行为

讨论可以尖锐，对人保持尊重。不搞人身攻击，不把项目变成任何国家的执法外包。

## 许可

贡献默认按 **MIT** 授权（与仓库 LICENSE 一致）。
