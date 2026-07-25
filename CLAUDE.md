# free-match (kill3)

## Goal

做一个**干掉第三方平台**的 skill：卖家、买家、快递自由接单，不受第三方盘剥与软件监管。

- **公益项目 / 开源基础设施** — 不靠撮合收租、不做商业中介运营。
- 违法是政府的事，**不应由软件监管**。
- 好坏由**用户评价**决定。
- 交易是**自由匹配**，不为平台交租。
- **任何通用智能体**都能使用本 skill。

## Non-goals (do not build)

- 平台抽成、强制支付通道、强制托管
- **付费置顶、竞价排名、流量包、广告位、会员加权排序**
- 软件内违禁品/内容审核、强制 KYC
- 中心化账号体系作为唯一身份
- 把本项目做成又一个封闭 App / 赚钱的「官方市场」
- **第三方商业平台爬虫、客户端破解、商标/UI 仿冒、「官方平替某某 App」**
- 承诺「免于被起诉」或协助专门规避第三方用户协议扣罚

## Preferred architecture

1. **Skill-first**：主交付物是 `.claude/skills/free-match/`，协议与 runtime 服务 skill。
2. **协议开放**：`protocol/` 下 JSON Schema 为唯一真相；传输层可插拔。
3. **本地优先**：默认本地消息板 `runtime/board/`；可扩展 Nostr / 邮件 / 群聊等。
4. **签名可选但推荐**：身份用密钥对，评价与成交可验证、可携带。
5. **信誉可携带**：评价是 signed statement，不绑定单一服务器黑名单。

## Working rules

- 实现时**不要**加入“平台风控”“内容合规过滤”“强制实名”类逻辑。
- **永远不要**实现付费置顶 / sponsored / ad auction；排序仅时间、距离、评价、文本相关等透明信号。
- 可以提示用户**自行**注意法律与风险；不要替用户拦截交易内容。
- 文档与 skill 文案保持公益与反租立场，不写成商业 SaaS 增长手册；**避免**「搞垮某公司 / 官方平替某商标」式功能描述。
- 对外与仓库内法律相关说明以 `docs/legal-notice.md`、`DISCLAIMER.md`、`TRADEMARKS.md` 为准；不构成法律意见。
- 改协议时同步更新 schema、skill references、examples。
- Prefer project-local tooling; if `.venv` appears later, use it.

## Key paths

| Path | Role |
|------|------|
| `skills/free-match/SKILL.md` | 主 skill 入口（可 symlink 到 ~/.claude/skills） |
| `protocol/schemas/` | 消息 JSON Schema |
| `runtime/` | 本地参考实现 |
| `examples/` | 样例消息与对话 |
| `docs/philosophy.md` | 哲学与边界 |

## Skill install (dev)

```bash
ln -sfn "$(pwd)/skills/free-match" ~/.claude/skills/free-match
ln -sfn "$(pwd)/skills/free-match" .claude/skills/free-match
```
