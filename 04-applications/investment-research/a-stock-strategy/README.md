# A 股日线策略回测

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

```python
from strategy import AStockDataProvider, BaiduKlineFetcher

provider = AStockDataProvider(
    BaiduKlineFetcher().fetch,
    cache_dir="data/cache",
    adjustment="none",  # 必须明确记录：none/前复权/后复权，不由程序猜测
)
bars = provider.load(["510688", "000001"], start="2020-01-01", refresh=True)
```

刷新需要服务器能访问上游网站，不需要 Tushare Token；回测时使用 `refresh=False` 命中本地缓存。若刷新失败但已有缓存，结果会带有
`bars.attrs["warnings"]`，明确标记为 stale cache，避免把旧数据误认为最新数据。百度接口未提供可靠的停牌/涨跌停布尔字段时，适配层会填入保守默认值 `False`；严肃研究应另接交易状态数据源并补齐这些列。

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

下一阶段可在不改变核心接口的前提下增加 FastAPI 只读查询层；如启用，应默认绑定 `127.0.0.1`、放在认证反向代理后，并继续禁止任何交易执行端点。
