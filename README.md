# AstraFin · Stocks & Crypto

**v0.1.0 — 可运行本地首版 / runnable local first release**

双语个人交易工作台，包含两组Radar、股票及Crypto独立账本、风险计算、行情CSV、蜡烛图、复盘与配置。默认只做手动记录，不发送券商订单。此版本未完成Approved规格的全部扩展能力；具体状态见 `docs/STATUS.md`。

A bilingual personal trading workspace with separate golden-cross and independent-strategy lists, stock and crypto ledgers, risk sizing, candle imports, charts, review and configuration. It records manual activity and sends no broker orders. This release does not implement every extension in the approved specification; see `docs/STATUS.md`.

## 启动 / Start

需要 Python 3.12 或更新版本。无第三方Python依赖，无npm安装步骤。
Requires Python 3.12 or later. No third-party Python packages or npm installation.

```sh
python3 start.py
```

Windows：双击 `start.bat`，或执行 `py -3 start.py`。macOS：双击 `start.command`，或使用上面的命令。启动后自动尝试打开本地浏览器；如未打开，访问 `http://127.0.0.1:8765/`。关闭终端或Ctrl+C停止。

On Windows, double-click `start.bat` or run `py -3 start.py`. On macOS, use `start.command` or the command above. The launcher opens the local browser; if it does not, visit `http://127.0.0.1:8765/`. Press Ctrl+C to stop.

## 第一次使用 / First use

1. 右上角 `EN / 中文` 切换语言。界面偏好只在设备本地保存；账本与配置保存在服务器SQLite。
2. Configuration选择Stocks。默认账户未入金，先在本地录入本金；单笔0.5%、组合2%、最多5只为可调整的模板值，费用未核实。填写券商真实费用、依据和生效日期，再勾选“费用已核实”。复杂分档费用未实现，参阅限制。
3. Stock Radar → 导入CSV。填写股票代码、交易所、报价币及板块。板块必须与重点板块配置匹配，或把该代码加入自选名单；空的板块不自动属于重点板块。
4. 预览校验后导入，然后运行扫描。金叉核心组与突破／回踩组独立显示。预览不会写入数据库。
5. 查看K线及计划。过期数据、未核实费用、风险不足等条件会阻止计划数量计算。
6. 在券商端自行执行后，在Portfolio录入**实际**数量、价格、费用和时间。按时间顺序录入；分批退出归为一个完整交易周期。风险违规的真实成交仍记录并留痕。
7. 更新持仓真实报价及汇率，系统据此更新估值、回撤与退出复核。没有后台自动估值，因此回撤仅反映记录到的时间点。
8. Crypto在独立入口。可导入CSV，或尝试Kraken公开历史行情适配器；扫描不要求资金。实盘计划须先配置独立本金、风险、报价币汇率和费用。首次Crypto风险未确认，不能默认挪用股票本金。
9. Review导出JSON报告或完整备份。备份包含账户资料，请自行妥善保管；源代码压缩包不包含交易数据。

Use the language switch at the top right. Configure verified broker fees first. Import actual completed candles, run Radar, review the two signal lists and risk plans, then record actual fills after executing at your broker. Update marks explicitly; the app does not continuously mark positions. Crypto has an independent ledger and funding configuration. Review exports JSON reports and checksum-protected backups.

## 行情CSV格式 / Candle CSV format

```csv
time,open,high,low,close,volume,complete
```

每行必须为真实OHLCV；本包不提供虚构市场价格。`time`是K线**结束**时间，推荐ISO 8601含UTC偏移；`complete`为`true`或`false`。时间递增且不能重复。导入一组交易所／股票或交易对／报价币／周期，最多10,000行。同一个组合再次导入会替换该数据集，保留导入审计。股票支持日线；Crypto支持4H／日线。

Each row must contain actual OHLCV data; no invented market prices are shipped. `time` is candle **close** time, preferably ISO 8601 with offset. `complete` is true/false. Timestamps must increase without duplicates. Import one venue/symbol/quote-currency/timeframe at a time, up to 10,000 rows. Reimporting the same identity replaces its dataset and adds an audit entry. Stocks: daily; crypto: 4H/daily.

## 计算口径 / Calculation basis

- 信号：完整导入历史计算EMA，暖机至少3倍慢周期；突破窗口排除当前K线。未完成或未来K线不确认信号。
- 仓位：Decimal计算，数量向下按步长取整；通过二分搜索同时约束风险、现金、集中度、预留现金和费用。0.5%是账户风险比例，非股价止损比例。
- 费用：支持最低佣金、比例佣金、比例其他费用及滑点。不支持全部交易所的分档税费／最高费用封顶。实际成交费用由用户录入，不使用计划费用伪造实际费用。
- 退出：固定目标、趋势转弱、按导入K线计数的周期退出，以及按已录入最高估值计算的移动止损，生成手动复核提示。分批目标考虑已卖出数量。不开自动平仓。
- 胜率：完整建仓至清仓为一笔；净利润>0为赢，持平计入分母，未平仓不计。股票／Crypto、模拟／实盘分开。
- 历史测试：用户指定样本外起始时间；固定最小交易单位、次根开盘、固定目标、止损优先，报告Wilson95%区间与未平仓交易。不等于多资产组合回测，也不验证全部Portfolio退出模式。
- 净值：以MYR显示，使用录入的汇率与估值。资金流不作利润；现金流调整高点。净值与回撤的采样频率取决于用户记录，不能声称连续监控的最大回撤。

Signals use completed history and explicit warmup; the breakout window excludes the current bar. Sizing uses Decimal arithmetic and lot-size rounding with fees and cash/risk constraints. Fills use actual manually entered costs. Exit modes generate manual review hints. A round trip counts as one trade. Historical tests are fixed-quantity strategy experiments, not portfolio backtests. Net asset value is sampled from recorded marks and FX rates; it is not continuous monitoring.

## Docker / 自部署

已提供 `Dockerfile` 与 `compose.yaml`；本次环境没有Docker，镜像构建及启动尚未验证。
A Dockerfile and Compose configuration are included. Docker was unavailable in the development environment; image build/start has **not** been validated.

```sh
cp .env.example .env
# Edit .env: set a long random RADAR_TOKEN.
docker compose up -d --build
```

打开 `http://127.0.0.1:8765/`，填入你设置的访问令牌。Compose只映射本机回环地址。若需远程访问，可在你控制的服务器上使用SSH端口转发；公网服务需另行配置HTTPS、认证、限流和适合生产环境的服务容器，本包不自动公开暴露账户。

Open the local URL and enter your configured token. Compose binds only to loopback. For remote use, use SSH forwarding on a server you control. Public hosting requires additional HTTPS, authentication, rate limiting and production-serving setup; account data is not automatically exposed.

## 验证 / Verify

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
```

本次通过19项测试，包含独立临时数据库中的HTTP工作流。所有测试价格均为明确的合成fixture，不写入用户账本。浏览器视觉／交互验收被自动审批拒绝，需要用户明确授权浏览器测试；未伪称已通过。

19 tests passed, including an HTTP workflow against an isolated temporary database. Synthetic fixtures are test-only and never inserted into the user's book. Browser visual/interaction QA was blocked by automatic approval review requiring explicit browser-test authorization; no visual pass is claimed.

## GitHub Source of Truth

源码仓库为 `accentgrove/AstraFin`。真实账户余额和凭据不进入Git；公开源码的新账户默认未入金，需在本地Portfolio记录本金。也可在首次启动时通过本地环境变量 `RADAR_INITIAL_STOCK_CAPITAL` 设置股票本金。此变量的实际值不上传。

The source repository is `accentgrove/AstraFin`. Public defaults contain no actual account balances or credentials. New accounts start unfunded; configure opening capital locally, optionally through `RADAR_INITIAL_STOCK_CAPITAL` on first startup.

首版审查分支为 `codex/astrafin-v0.1.0`。同步状态以GitHub实际分支及commit为准；CI结果见对应PR的Checks。公开仓库保留原有README名称和Python忽略规则，代码通过独立分支及PR进入。源码提交不等于公网部署。

Verify synchronization against actual GitHub branches and commits. A repository label is not proof of a push or CI run. Source is submitted on a separate review branch while preserving the existing repository files.
