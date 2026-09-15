# Implementation status / 实施状态 — v0.1.0

This is a runnable initial implementation, not full completion of the public implementation specification.
本版是可运行的首个实现，尚不等于公开规格的全部扩展完成。

| Area / 范围 | Implemented / 已实现 | Remaining / 待完成 |
|---|---|---|
| UI / 界面 | 中文/English全局文案切换、6入口、Burger、Tabs、Accordion、响应式CSS、Back to top | 浏览器视觉与交互QA被自动审批拒绝，尚未验收；数据源标识及审计原始键保留原文 |
| Configuration / 配置 | 20分组、71字段、类型和交叉校验、revision冲突检测、导入导出、独立股票/Crypto设置 | 全部继承层级的覆盖编辑器、交易所规则档案、多版本费用表尚未实现；未支持开关不可启用 |
| Radar | CSV预览/导入、EMA/MACD、突破/回踩、过滤与分组、共振、覆盖范围、数据时效、蜡烛图 | 股票实时行情未连接、全市场股票池未连接、相对强弱基准过滤和更多金叉模板尚未实现 |
| Crypto | 独立扫描和Portfolio，4H/日线、现货、交易所标识、资金配置阻断 | Kraken适配器已写入但网络超时，未验证真实行情返回；未来交易所需适配 |
| Portfolio | 实盘/模拟分开，手动成交，去重，Decimal账本，分批卖出，估值，止损收紧，退出复核 | 券商CSV映射导入、成交更正工作流、公司行动、自动估值、配对跨账户转账尚未实现 |
| Risk / 风控 | 现金、费用、数量步长、风险上限、集中度、回撤空间、暂停及复核恢复 | 连续市场监控、精细相关性模型、正式交易所结算规则和多资金币种现金子账尚未实现 |
| Validation / 验证 | 固定数量历史测试、样本外日期、止损优先、95%胜率区间、样本不足标记 | 多策略/多资产完整Portfolio回测、所有退出组合的验证、历史股票池幸存者偏差处理尚未完成 |
| Execution / 执行 | 手动计划和真实成交记录；券商自动下单完全关闭 | 真实审批接口、券商对账、撤单、部分成交API尚未接入；没有授权或能力执行真实订单 |
| Automation / 自动化 | 手动触发，应用内退出与风险提示 | 定时扫描、定时备份、Email通知未实现，开关明确锁定 |
| Data / 数据 | SQLite持久化、JSON校验和备份、恢复前SQLite副本、过期旧计划 | 高级保留策略、外部备份目的地、全部数据库迁移回滚方案待扩展 |
| Deployment / 部署 | Python标准库本地启动、Mac/Windows启动器、Docker/Compose配置、CI文件 | Python启动与HTTP接口已验证；Docker不可用未测试；生产公网服务未验收 |
| GitHub | 公开源码已去除私人资金资料；独立分支及PR管理；包含CI工作流 | 以GitHub提交及PR Checks为验证依据；分支提交不等于已合并main或已部署 |

## Source references / 实现依据

- Python SQLite backup API: https://docs.python.org/3/library/sqlite3.html
- Python HTTP server runtime: https://docs.python.org/3/library/http.server.html
- Kraken public OHLC: https://docs.kraken.com/api/docs/rest-api/get-ohlc-data/

These references document runtime/API behavior, not trading profitability. Public network access was unavailable during live adapter verification. The default candle importer is the validated path.
以上资料说明接口/运行时行为，不证明策略收益。真实公开行情适配验证遇到网络不可达；已验证的数据路径是用户导入CSV。
