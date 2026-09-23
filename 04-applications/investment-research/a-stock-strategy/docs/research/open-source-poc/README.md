# 开源复用实测（2026-09-14）

结论：优先将 Qlib 作为独立研究环境试接，复用其因子表达式、策略组件和实验记录；现有网页、数据下载和回测引擎继续保留。RQAlpha 暂不接入核心依赖。本次是兼容性探索，不是生产集成，也没有证明任何策略具备样本外收益。

## 实测范围与结果

| 对象 | 已验证 | 未验证 |
| --- | --- | --- |
| Qlib 0.9.7 | 本地 CSV 转入二进制数据；3 只 ETF、485 个交易日、1455 行特征；20 日动量与 pandas 计算一致；内置 TopkDropoutStrategy 跑完 447 日；MLflow SQLite 记录和 artifact 保存、重读 | 模型训练、全市场选股、跨引擎成交一致性、生产任务集成 |
| RQAlpha 6.3.0 | 独立安装、调用 run_func；默认数据源缺少 bundle 时返回明确异常 | 自定义 CSV 数据源、完整回测、与当前引擎结果对比 |

Qlib 输入是 `data/real/market.csv`，包含 2024-01-02 至 2025-12-31 的上证指数及 588000.SH、510300.SH、159915.SZ。策略仅使用三只 ETF，以历史 20 日动量排序，复用内置单标的轮动策略，下一交易日开盘成交。回测区间为 2024-03-01 至 2025-12-30，最后一日留给数据日历边界。

初始账户 100000，期末账户 133504.06639056624。这个数字只是接口运行证据，不能与已有市场宽度策略的收益直接比较：信号、仓位、退出方式和成交规则均未对齐。本次没有调参或进行样本外验证。

Qlib 实验 ID、指标及边界见 `qlib-result.json`；RQAlpha 启动结果见 `rqalpha-result.json`。RQAlpha 的缺失 bundle 是本次有意不下载外部数据包的启动检查，不能据此推断 RQAlpha 无法支持 CSV，或其回测能力存在缺陷。采用它需要进一步实现官方数据源接口或准备完整 bundle。

## 数据与运行限制

- 原始行情是前复权近似数据，转换时 `factor=1` 只是接口占位，不能代表已验证复权因子。价格、交易数量与费用仍有近似误差。
- 成交量单位未重新校验；未引入真实停牌、历史涨跌停、分红及 ST 数据。Qlib 的统一 20% 价格阈值仅为 PoC 配置，不代表完整交易规则。
- Qlib 输出过空数组均值、未来日历回退及 Gym/NumPy 兼容性警告。账户序列非空、有成交、特征计算和文件重读断言通过，不意味着所有指标和可选模块都已验证。
- Qlib Recorder 尝试收集当前目录的 Git 信息。实验在临时目录执行，未采集生产工作区的未提交修改；相应 Git 信息收集失败不影响本次指标和文件持久化。
- Qlib 本次安装 191 个包，RQAlpha 41 个包；各环境使用不同 NumPy 主版本。实际依赖已分别冻结，未修改生产 `pyproject.toml` 或 `.venv`。

## 复现

脚本带有关键数据格式和近似假设注释。先将本目录下两个 `probe_*.py` 复制到独立实验目录，再在该目录执行；脚本会在自身目录生成 provider、SQLite 和结果文件。不要直接在生产 Git 工作目录启动 Qlib Recorder。

```bash
uv venv --python 3.11 /private/tmp/a-stock-open-source/qlib-env
uv pip install --python /private/tmp/a-stock-open-source/qlib-env/bin/python -r qlib-requirements.txt
uv venv --python 3.11 /private/tmp/a-stock-open-source/rqalpha-env
uv pip install --python /private/tmp/a-stock-open-source/rqalpha-env/bin/python -r rqalpha-requirements.txt

# 以下从临时实验目录执行，并替换真实 CSV 的绝对路径。
MPLCONFIGDIR=/private/tmp/a-stock-open-source/mpl /private/tmp/a-stock-open-source/qlib-env/bin/python probe_qlib.py /absolute/path/to/data/real/market.csv
MPLCONFIGDIR=/private/tmp/a-stock-open-source/mpl /private/tmp/a-stock-open-source/rqalpha-env/bin/python probe_rqalpha.py
```

默认 PyPI 大文件下载在本机长时间停滞，改用清华镜像后安装完成。版本文件记录实测解析结果，不保证其他操作系统完全兼容。

## 下一步范围

1. 接入实验记录：先用独立 MLflow 记录当前回测任务的策略版本、数据版本、参数、基准、随机对照和输出文件。Qlib 自带 Recorder 基于 MLflow，可以共享这一底座；无需另写实验数据库和比较平台。
2. 做一个来源明确的策略适配：优先动量或均线策略，将其信号接入当前执行引擎，在同样数据、成本和成交时点下比较。复用数学规则与直接复制第三方源码要分别处理。
3. 再扩展参数实验、训练/验证/测试时间切分和滚动验证。完成这些证据链后再评估 RD-Agent 的自动研究循环。

此处仍需要自建的部分是本地数据版本适配、当前交易规则、统一任务协议，以及面向用户的页面。通用因子库、实验追踪、参数搜索和模型训练框架应尽量复用。

## 官方依据

- [Qlib](https://github.com/microsoft/qlib)：研究流程与模块；MIT 许可。
- [Recorder](https://qlib.readthedocs.io/en/latest/component/recorder.html)：参数、指标、产物和实验记录。
- [Qlib 数据转换](https://github.com/microsoft/qlib/blob/main/scripts/dump_bin.py)：二进制格式参考。
- [Qlib 内置回测接口](https://github.com/microsoft/qlib/blob/main/qlib/contrib/evaluate.py)：日频回测配置。
- [RQAlpha 数据源接口](https://github.com/ricequant/rqalpha/blob/master/rqalpha/interface.py)：自定义数据适配所需接口。
- [RQAlpha 许可](https://github.com/ricequant/rqalpha/blob/master/LICENSE)：区分非商业与商业使用，不能按无限制 Apache 项目处理长期集成。
- [RD-Agent](https://github.com/microsoft/RD-Agent)：后续自动研究候选，本次未安装验证。

## 后续进展（2026-09-19）

该目录保留原始 PoC 结论。当前已另行完成独立 Qlib 因子运行时入口，使用现有工作台执行交易，详见 [运行时说明](../../qlib-runtime.md)。不代表本 PoC 中的 TopkDropout、模型训练或 RQAlpha 已接入。
