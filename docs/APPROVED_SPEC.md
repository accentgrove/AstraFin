# AstraFin · Public implementation specification

This is the public, non-personal specification. Private account details, capital allocations and original private planning material are excluded.
此文件是去除个人资料的公开实施规格；真实资金、账户明细及私人规划不提交仓库。

## Product / 产品

A bilingual personal stock and spot-crypto research and manual-trading ledger. GitHub repository: accentgrove/AstraFin. The current release is an initial implementation; remaining work is listed in STATUS.md.
中英文个人股票与现货Crypto研究／手动交易账本。GitHub为源码权威来源；初版未完成全部扩展，详见STATUS.md。

- Independent stock / crypto portfolios and live / paper books.
- Separate EMA/MACD golden-cross and breakout/pullback lists, with resonance flags.
- User-configured watchlists, priority sectors and imported OHLCV.
- Completed-candle confirmation, no look-ahead, explicit data freshness.
- Deterministic sizing based on fees, quantity steps, cash, concentration and risk budgets.
- Manual fill recording, partial exits counted as one complete trade cycle.
- Configurable exit modes, mark-based drawdown review and manual resume.
- Schema-validated configuration with revision tracking, export/import and backups.
- Full Chinese / English UI, responsive navigation, tabs, accordions and back-to-top.
- Local SQLite persistence; local startup and optional Docker deployment files.
- No actual capital configured in public source; new accounts start unfunded.
- Broker execution and scheduled tasks remain disabled until implemented and verified.
- Public APIs and backtests do not imply a verified winning percentage or return.
- Credentials, actual balances, fills and private specifications stay outside Git.

## Configuration groups / 配置分组

Preferences; markets; sessions; market data; stock universe; crypto universe; golden cross; independent strategies; filters; signal lifecycle; capital; fees; risk; drawdown; exits; execution; alerts; review; backup; deployment.
基础偏好、市场、交易时段、行情、股票范围、Crypto范围、金叉、独立策略、确认过滤、信号生命周期、资金、费用、风险、回撤、退出、执行、提醒、复盘、备份、部署。

Use configuration-catalog.json for the field-level inventory and STATUS.md for implementation boundaries. Code changes go through a reviewable branch and pull request. Only a pushed and verified GitHub version may be described as synchronized or released.
字段详见configuration-catalog.json；实施边界详见STATUS.md。代码通过可审查分支及PR管理；只有实际推送并核实的版本才能称为已同步或已发布。
