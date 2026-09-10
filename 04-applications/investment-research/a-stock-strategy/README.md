# A 股日线策略回测

## 当前最小版本（2026-09-06）

**请从 [MVP 使用说明](MVP.md) 开始。** 正确策略是“全市场下跌家数 ≥4000，且上证指数当日收益 ≤-1%”。新版入口为 `configs/mvp.toml`（合成演示）和 `configs/real_breadth.toml`（真实数据模板）。

```bash
.venv/bin/python -m strategy compare --config configs/mvp.toml --output reports/mvp
```

打开 `reports/mvp/index.html` 查看固定科创50ETF与候选ETF动态评分比较；同时生成逐笔成交、每日净值、每日触发审计和指标。示例数据只用于验证软件。

## 浏览器工作台

在项目目录启动本机服务：

```bash
.venv/bin/python -m strategy serve
```

访问 `http://127.0.0.1:8765`。页面支持选择现有策略、按策略定义生成参数表单、执行回测、保存任务历史、查看净值/回撤/交易/触发记录、复制参数重跑及多任务指标对比。服务只监听本机回环地址；任务使用 SQLite 和独立目录保存在 `reports/workbench/`，关闭浏览器不会终止任务。

新增后端策略时，在 `src/strategy/strategies/registry.py` 显式注册 `StrategyDefinition`，声明参数、构造器、标的提取与预热需求；工作台通过同一合同执行，不再判断具体策略名。参数目录保持兼容。扩展示例与尚未拆分的边界见 [后端模块说明](docs/backend-architecture.md)。当前执行模型是日频、100 份整数手、单持仓和固定持有期；组合持仓、盘中撮合及用户上传 Python 策略不在第一版范围内。

从腾讯下载上证指数与 ETF 日线：

```bash
.venv/bin/python -m strategy download-market \
  --start 2024-01-01 --end 2025-12-31 \
  --symbols 588000.SH 510300.SH 159915.SZ \
  --adjustment none --output data/real
```

命令会自动加入 `000001.SH`，按年度保存原始响应，并要求行情日期与已有 `breadth.csv` 完全一致后才发布 `market.csv`。`none` 是实际开盘价近似，但尚未计入 ETF 分红现金流；`qfq` 适合连续收益研究，但不是历史实际成交价。任务会冻结行情、广度、清单、请求和 Python 源码哈希，避免排队期间的数据刷新改变结果。

下方旧版文档和 `baseline.toml`/`real_baidu.toml` 仅用于兼容旧实验：其“指数点位 ≥4000”是对需求的误解。旧 `data/real_baidu/000001.csv` 为十几元的股票行情，并非上证指数，不可用于该策略验证。真实数据来源与局限见 [数据源调查](docs/data-source-review.md)。

---

这是一个仅使用本地 CSV 的研究/模拟工具，用同一套事件驱动引擎运行固定科创 50 ETF 与动态横截面选股策略。核心计算、推荐和四类报告都不需要网络、券商账户或大模型 API Key。输出仅用于研究与软件测试，不构成投资建议、收益承诺或买卖指令。

## 安装

需要 Python 3.11+ 和 [uv](https://docs.astral.sh/uv/)。在本目录执行：

```bash
uv sync --offline
uv run --offline pytest -q
```

`--offline` 只表示运行阶段不访问网络；首次部署仍需先在线执行一次 `uv sync`
（或把 `uv.lock` 中的 wheel 预先放入 uv 缓存）。如果目标机器没有缓存依赖，直接执行
`uv sync --offline` 会因无法下载 pandas 等包而失败。

若没有 uv，也可以使用标准 venv（依赖仍需从已配置的本地镜像或网络安装）：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

## 使用

基线配置运行固定策略并生成 `reports/`：

```bash
uv run --offline python -m strategy backtest \
  --config configs/baseline.toml --output reports
```

在项目目录之外运行时，显式指定项目目录即可（不会改变当前工作目录）：

```bash
PROJECT=/path/to/a-stock-strategy
uv run --offline --project "$PROJECT" python -m strategy backtest \
  --config "$PROJECT/configs/baseline.toml" --output "$PROJECT/reports"
```

指定交易日输出推荐（仍然是研究结果，不是交易指令）：

```bash
uv run --offline python -m strategy recommend \
  --config configs/baseline.toml --as-of 2026-08-03
```

回测会打印 JSON，其中列出输出目录、文件路径和警告。每次运行包含四个 artifact：`trades.csv`、`equity.csv`、`summary.json`、`report.png`。`summary.json` 回显数据范围、复权口径、成本、生成时间、警告和 LLM 状态。

## 配置参考

`configs/baseline.toml` 是可复制的最小配置：

- `[data]`：`source`、相对于配置文件的 `path`、`format`（当前为 `csv`）、`adjustment`（例如 `none`）。
- `[strategy]`：`name = "fixed_asset"` 或 `"cross_sectional_rank"`；固定策略在 `parameters.symbol` 指定代码。动态策略还可配置 `candidate_symbols`、四个特征窗口、`weights` 和 `min_volume`。
- `[backtest]`：初始现金和持有交易日数。
- `[market]`：市场代理指数代码、触发点位和日收益阈值。信号只读取 `as_of` 及之前的收盘数据，并在下一交易日开盘模拟执行。
- `[costs]`：佣金、卖出印花税、最低佣金和滑点（bps）。这些值会写入报告。
- `[metadata]`：数据来源、时区、复现标记等说明；`offline = true` 与 `llm_enabled = false` 表示基线不联网、不调用模型。

## 数据格式

CSV 每行是一个交易日/代码组合，必需列为：

`date,symbol,open,high,low,close,volume,amount,is_suspended,limit_up,limit_down`

日期使用交易所本地日历；四个价格必须为正且有限。价格的前复权/后复权口径必须在配置的 `adjustment` 中明确记录。布尔字段接受 `0/1`、`true/false` 等常见写法。示例数据见 `data/sample/market.csv`。

## 接入 a-stock-data 真实行情

`a-stock-data` 是上游行情调用说明与实现集合，不是本项目的回测依赖。研究环境可把它的百度 K 线调用（或自定义 mootdx 调用）注入
`AStockDataProvider`；provider 会统一日期、六位证券代码和字段名，并按证券保存 CSV 缓存。这样网络、限流和数据源变更只影响适配层，回测仍可对缓存文件离线运行。

使用 mootdx 获取指数历史日线前，安装可选实时数据依赖：

```bash
uv sync --extra live
```

`MootdxIndexFetcher` 使用 `client.index`，`MootdxBarFetcher` 使用 `client.bars`；两者都需要服务器能够访问通达信 TCP 行情端口。

```python
from strategy import AStockDataProvider, BaiduKlineFetcher

provider = AStockDataProvider(
    BaiduKlineFetcher().fetch,
    cache_dir="data/cache",
    adjustment="none",  # 必须明确记录：none/前复权/后复权，不由程序猜测
)
bars = provider.load(["588000", "000001"], start="2020-01-01", refresh=True)
```

刷新需要服务器能访问上游网站，不需要 Tushare Token；回测时使用 `refresh=False` 命中本地缓存。若刷新失败但已有缓存，结果会带有
`bars.attrs["warnings"]`，明确标记为 stale cache，避免把旧数据误认为最新数据。百度接口未提供可靠的停牌/涨跌停布尔字段时，适配层会为满足 CSV 契约暂填 `False`；这不是可交易性证明，严肃研究应另接交易状态数据源并补齐这些列。

## 可复现性与限制

给定相同的 CSV、TOML、Python 版本和代码提交，策略、撮合、指标及 CSV/JSON 内容是确定性的；图表使用固定 Agg 后端。`generated_at` 是报告生成时刻，因此每次报告的时间戳会不同。系统不会在回测过程中隐式联网或补齐缺失行情，停牌、涨跌停和无下一交易日会保留警告。

## Mac 独立运行部署

建议使用专用用户和项目目录，限制配置、行情和报告目录权限（例如 `chmod 700`），不要把任何 API Key 写入 TOML 或日志。回测是离线进程，不连接券商，也绝不会自动下单。

### Python venv + launchd

```bash
cd /path/to/a-stock-strategy
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

保存以下 plist 为 `~/Library/LaunchAgents/com.example.astock-backtest.plist`，将路径替换为实际绝对路径：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.example.astock-backtest</string>
  <key>ProgramArguments</key><array>
    <string>/path/to/a-stock-strategy/.venv/bin/python</string>
    <string>-m</string><string>strategy</string><string>backtest</string>
    <string>--config</string><string>/path/to/a-stock-strategy/configs/baseline.toml</string>
    <string>--output</string><string>/path/to/a-stock-strategy/reports</string>
  </array>
  <key>WorkingDirectory</key><string>/path/to/a-stock-strategy</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/path/to/a-stock-strategy/reports/launchd.out.log</string>
  <key>StandardErrorPath</key><string>/path/to/a-stock-strategy/reports/launchd.err.log</string>
</dict></plist>
```

首次加载前先创建报告目录并校验 plist；macOS Ventura/Sonoma 推荐使用 bootstrap/bootout（旧版 `load/unload` 已逐步弃用）：

```bash
mkdir -p /path/to/a-stock-strategy/reports
plutil -lint ~/Library/LaunchAgents/com.example.astock-backtest.plist
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.example.astock-backtest.plist
launchctl kickstart -k "gui/$(id -u)/com.example.astock-backtest"
```

查看状态/日志：

```bash
launchctl print "gui/$(id -u)/com.example.astock-backtest"
tail -f /path/to/a-stock-strategy/reports/launchd.out.log
```

停止并移除任务：

```bash
launchctl bootout "gui/$(id -u)" ~/Library/LaunchAgents/com.example.astock-backtest.plist
```

如果任务已经加载，先执行 `bootout` 再重新 `bootstrap`；不要同时使用同一输出目录运行 cron 和 launchd，避免报告文件相互覆盖。

### Cron 替代方案

在 `crontab -e` 中加入每日 18:00 任务（使用绝对路径）：

```cron
0 18 * * 1-5 /path/to/a-stock-strategy/.venv/bin/python -m strategy backtest --config /path/to/a-stock-strategy/configs/baseline.toml --output /path/to/a-stock-strategy/reports >> /path/to/a-stock-strategy/reports/cron.log 2>&1
```

如果将工作台部署到其他机器或开放局域网访问，需要另加身份认证和 HTTPS；当前服务只适合本机单人使用。

### 标的选择与独立数据准备

回测页面的固定标的使用单选下拉框，排名策略使用多选框（Ctrl / Command 多选）。只展示当前数据集中已准备且交易规则支持的证券；共同日期范围会随选择更新。下载不会在提交回测时自动发生。

在页面下方“标的数据管理”输入代码及日期，点击“新增代码并下载行情”。系统独立排队下载、获取名称、校验交易日和文件哈希，成功后生成 `data/managed_<任务ID>` 新版本。选择对应数据集后即可使用其中可回测的标的；失败或中断记录可以重试。

- 当前支持 `588000.SH`、`510300.SH`、`159915.SZ` 及已识别名称和类型的沪深普通主板股票（000/001/002/003.SZ，600/601/603/605.SH）。当前名称含 ST/退、其他板块和未知证券仍为“仅行情”。协鑫能科为 `002015.SZ`。股票回测日期从 2022-07-01 起。
- 协鑫能科使用 `002015.SZ`；错误交易所会明确提示。
- 下载范围必须在真实基线 `data/real` 的覆盖范围内；没有真实基线时不允许将下载行情与合成样例混合。扩展市场广度年份仍使用 CLI。
- 每次版本以 `data/real` 为基线，加入或更新本次证券；不会累计其他下载版本的新增证券，也不会修改已有回测快照。
- 为避免前复权价格跨下载日期拼接，更新已有 ETF 会在新版本里整支替换成所选下载区间，不保留该 ETF 区间外旧行情；其他标的不变。
- 原始行情单位沿用各自来源，结果保留相关警告；证券类型扩展必须先验证交易模型。
- 下载记录在 `reports/workbench/downloads.sqlite3` 中持久保存。请仅运行一个工作台实例管理同一状态目录。

前端日期与标的规则测试：`node --test tests/instrument-options.test.cjs`；后端测试：`.venv/bin/pytest -q`。


### 股票日频近似回测与模块边界

工作台复用已下载的数据，无需为协鑫能科重新下载。选择包含该股票的数据集，在固定标的或多候选策略中选择股票，提交后可查看佣金、印花税、过户费及成交／取消／延后日志。旧任务仍保持原结果。

- `backtesting/fees.py` 集中管理按证券类型、日期和方向匹配的费用规则；回测引擎调用费用计算及可买数量计算。股票卖出印花税在 2023-08-28 前为 0.1%，此后为 0.05%；过户费双边 0.001%。佣金由用户配置，视为含交易规费。ETF 印花税及过户费为零。
- `backtesting/tradability.py` 将状态提供方与判断规则分开。`TradingStatus` 保留 True / False / None（未知）；现有日线适配器不会把下载器填充的 False 当作已验证状态。以后可通过 `StatusProvider` 接入开盘时已知的历史停牌和涨跌停证据。
- 引擎负责订单及资金生命周期：100 股／份买入，至少下一交易日卖出；已知停牌阻断、股票买入涨停取消、卖出跌停延后。未知状态在当前 approximate 模式下允许估算，结果保留限制说明。工作台对缺行、非法价格仍前置拒绝，不会自动补齐行情。

当前尚未接入可靠历史停牌、涨跌停、ST及退市状态。前复权价格不是实际成交价，数量和费用金额只是近似；未模拟部分成交、排队、分红配股与持股数量变化。没有利用当天收盘、最高最低价或全天成交量判断开盘是否可成交。

费率依据及实施范围见 [实施计划](docs/superpowers/plans/2026-09-08-stock-backtest.md)。本次规则仅接入网页工作台路径；旧 CLI 配置保留原兼容行为，不会自动识别股票类型。
