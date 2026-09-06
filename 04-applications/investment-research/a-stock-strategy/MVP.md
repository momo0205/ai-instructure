# A 股市场广度策略 MVP

本版本用于检验“下跌家数 ≥4000、上证指数跌幅 ≥1% 时买入 ETF”的想法。核心不需要大模型。演示已可离线运行；真实历史收益需要补齐广度与准确的指数/ETF日线，不能从演示收益推断策略有效。

## 直接运行

在本项目目录执行（已有 `.venv`）：

```bash
.venv/bin/python -m strategy compare --config configs/mvp.toml --output reports/mvp
```

双击 `reports/mvp/index.html`。HTML 图表已内嵌，不需要启动服务；下载链接对应旁边的 CSV/JSON 文件，分享时请保留整个目录。

首次安装可执行 `uv sync`；已有依赖缓存可 `uv sync --offline`。运行测试：

```bash
.venv/bin/python -m pytest -q
```

## 策略与时点

- 默认“大盘指数”为上证综指 `000001.SH`；4000 是下跌股票家数，和指数点位无关。4000 与 -1% 边界均包含。
- 下跌家数来自独立的每日全市场广度文件，不从三个候选 ETF 推断。
- D 日收盘确认信号，D+1 交易日开盘买入，D+2 交易日开盘卖出。持有期可配置。它不能回答“D 日尾盘买入”的完整问题，尾盘策略还需要当时已可见的分钟级广度与成交数据。
- 每次空仓触发时使用当前可用现金买入一个 ETF；已有持仓时不叠加仓位。默认 100 份整数单位、双边佣金万三、每笔最低5元、滑点2bps、ETF印花税0。请按真实券商费用调整。
- 固定策略买入 `588000.SH`；动态策略在 `588000.SH`、`510300.SH`、`159915.SZ` 中按短期反转和波动率评分。权重是研究起点，没有根据演示收益调参。
- 当前动态策略只使用候选 ETF 自身历史价格/成交量特征；**尚未实现基于4000家下跌股票的行业分布或成分股下跌比例选ETF**。那一步需要时点一致的行业/成分股数据。

日期按输入交易日推进。示例是90个工作日的合成测试序列，没有使用真实交易所节假日日历；真实 CSV 必须只含实际交易日。报价/停牌/涨跌停状态需使用对应执行时点可见的信息，不能用当日最终状态推断开盘一定可成交。

## 看哪些报告

| 文件 | 内容 |
|---|---|
| `index.html` | 中文比较、净值/回撤图、数据身份、成本与缺失提示 |
| `comparison.csv` / `comparison.json` | 两种策略收益、胜率、最大回撤、交易数、超额收益及全部指标 |
| `fixed_asset/trades.csv` | 固定ETF信号日、买入日、卖出日、成交价、数量、费用、盈亏 |
| `cross_sectional_rank/trades.csv` | 动态ETF对应成交 |
| 各策略 `events.csv` | 每日指数点位、指数收益、下跌家数、是否触发及缺数据原因 |
| 各策略 `equity.csv` / `summary.json` | 每日权益、完整指标、输入文件哈希及配置 |

动态超额收益以“相同事件下买入固定ETF”为基准，不是与始终持有ETF比较。某个标的完全缺失时拒绝比较；数据日期覆盖不完整时显示缺失天数并暂停超额收益计算。缺失广度不补成零、不向后填充；会跳过信号并在报告中列出。年化指标、夏普和胜率在事件数量很少时缺乏稳定性，应结合事件清单判断。

单独回测与某日研究选择：

```bash
.venv/bin/python -m strategy backtest --config configs/mvp.toml --output reports/fixed
.venv/bin/python -m strategy recommend --config configs/mvp.toml --as-of 2024-02-06
```

改 `[strategy].name` 为 `cross_sectional_rank` 后，`recommend` 输出候选排序和特征。比较命令始终运行固定与动态两种策略。

## 接入真实历史数据

### 1. 下载股票广度

申请本人的 Tushare Token，设置到运行命令的终端环境 `TUSHARE_TOKEN`；无需把密钥写进配置或发给助手。随后：

```bash
.venv/bin/python -m strategy download-breadth --start 2024-01-01 --end 2025-12-31 --output data/real
```

下载器按日期获取全市场 `daily`，6000条分页，统计供应商 `pct_chg < 0`，保存原始 CSV、`breadth.csv`、`manifest.json`。不使用今天的股票列表回推历史；每次请求间隔至少1.3秒。失败会报错，不能把网络或权限错误当作零下跌。空工作日记录在 manifest 中，需与交易所日历核验；不自动认定为空的日子就是假日。

最低4000条记录只能排除明显的自选股列表，**不能证明沪深北全部覆盖**。输出 `sh_count/sz_count/bj_count` 可供核验。停牌股票可能不在供应商 `daily` 中，`total_count` 是返回的有效日线数。应核对缺失交易日、北交所和退市覆盖，尤其在正式下结论之前。Token 股票日线权限不意味着有免费 ETF/指数权限。

### 2. 或导入已下载的全市场股票日线

输入列为 `trade_date,ts_code,pct_chg`，例如 `20240102,600000.SH,-1.25`。必须是每天完整截面，不能用候选池或任意4000只股票凑数。

```bash
.venv/bin/python -m strategy import-breadth --input /path/to/all_daily.csv --source "供应商名称及导出日期" --output data/real/breadth.csv
```

也可提供已有广度 CSV：`date,declining_count,total_count,source`。日期必须唯一；计数必须为非负整数，且下跌数不大于总数。

### 3. 准备准确的指数与 ETF 行情

在 `data/real/market.csv` 放入指数 `000001.SH` 及配置候选 ETF 的日线，列为：

```text
date,symbol,open,high,low,close,volume,amount,is_suspended,limit_up,limit_down
```

证券代码需带交易所后缀，指数和个股必须区分。旧百度缓存 `000001` 实际返回平安银行，不能直接改名成 `000001.SH` 冒充指数。必须用明确的指数接口重新获取；项目已有 `MootdxIndexFetcher` 与 `MootdxBarFetcher` 可注入，但网络实测未拿到可靠指数数据，不能保证当前环境可下载。

本次没有获得完整可核验的真实市场数据组合。ETF/指数可从可靠行情工具导出，再转换成上述标准 CSV；未来可增加经过实测的免费适配器。未复权日线的ETF分红/拆分不在当前现金流模型内，跨越这些事件会影响收益；正式研究应补充公司行动或核验一致复权口径。未知交易状态不能当作确认可成交。

### 4. 跑真实比较

检查 `configs/real_breadth.toml` 的来源、候选池、文件路径和复权说明后执行：

```bash
.venv/bin/python -m strategy compare --config configs/real_breadth.toml --output reports/real
```

真实数据缺失时会明确失败，不会悄悄退回示例数据。

## 当前交付边界

已具备：修正后的触发条件、固定/动态ETF策略、日线撮合、交易成本、市场广度下载/导入、报告对比和异常测试。

仍未完成：真实历史策略有效性结论、真实尾盘执行验证、行业/成分股广度驱动选股。系统目前无自动交易、账户接入或定时下单。

免费数据权限与开源项目选择见 [调查记录](docs/data-source-review.md)。
