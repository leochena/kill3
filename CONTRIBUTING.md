# Contributing to free-match (kill3)

先谢谢你。这个项目要靠很多人才能从「协议 demo」长成「到处能用的自由匹配层」。

## 北极星

1. **无平台租** — 不引入强制佣金、强制支付、强制唯一中继。  
2. **无软件监管** — 不把违禁品清单 / KYC / 内容审核做成协议或默认服务器逻辑。  
3. **信誉可携带** — 评价是消息，不是服务器黑箱分。  
4. **智能体优先** — Skill + 开放 JSON，任何通用 Agent 都能当节点。  
5. **哑管道板** — 中继只存取消息；发现可以有很多门。

违反以上方向的 PR 会被关闭并说明原因。

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
