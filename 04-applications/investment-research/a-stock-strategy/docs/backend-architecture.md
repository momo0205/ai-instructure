# 后端架构与阅读入口

系统是单进程单体应用，业务实现按职责组织。项目入口仍为 `python -m strategy`。

```text
src/strategy/
├── __main__.py                 # 命令入口
├── __init__.py                 # 公共导出
├── _compat.py                  # 集中兼容旧模块导入名
├── domain.py                   # 共享交易/市场领域对象
├── validation.py               # 公共数值校验
├── strategies/
│   ├── base.py                 # 选股接口
│   ├── registry.py             # 注册、参数、标的与预热合同
│   ├── fixed.py
│   └── rank.py
├── market_data/
│   ├── catalog.py              # 证券代码和交易支持范围
│   ├── provider.py             # 提供方接口与适配器
│   ├── tencent.py              # 腾讯日线解析、下载与原始证据
│   ├── repository.py           # 数据目录、冻结基线、校验、原子发布
│   ├── csv.py                  # CSV读取和数据合同
│   ├── breadth.py              # 市场广度
│   ├── ingest.py               # 广度导入/下载
│   └── sources.py              # 旧行情源接入
├── backtesting/
│   ├── engine.py               # 订单、持仓、现金和净值
│   ├── fees.py                 # 日期/证券类型/买卖方向费用
│   ├── tradability.py          # 状态证据与成交资格
│   ├── signals.py              # 市场触发条件
│   └── evaluation.py           # 收益和风险指标
├── application/
│   ├── requests.py             # 工作台请求校验和数据覆盖约束
│   ├── backtests.py            # 回测执行编排
│   ├── jobs.py                 # 回测队列与SQLite状态
│   ├── downloads.py            # 下载队列、提供方/仓库协调
│   ├── comparison.py           # 旧CLI策略比较流程
│   ├── recommendation.py       # 旧推荐流程
│   └── llm.py                  # 可选报告解释接口，回测不需要
├── storage/
│   ├── snapshots.py            # 冻结数据/源码/请求及结果JSON
│   └── reports.py              # 导出报告和图表
└── interfaces/
    ├── cli/
    │   ├── main.py             # CLI参数和命令路由
    │   └── config.py           # 旧TOML配置解析
    └── web/
        ├── server.py           # HTTP接口、安全校验
        └── static/             # HTML、JS和CSS，随wheel发布
```

建议从 `application/backtests.py` 阅读回测主流程；随后看 `strategies/registry.py`、`backtesting/engine.py`。下载流程从 `application/downloads.py` 开始。

## 主要调用关系

回测：Web → jobs → requests → backtests → snapshots + 策略定义 + engine → evaluation → 结果。

下载：Web → downloads → provider.resolve → repository.prepare → provider.download → repository.publish。

请求校验不负责文件复制；快照存储不负责运行策略；引擎不负责HTTP、下载或任务数据库。源码快照仍捕获整个 strategy 包，包含嵌套子包。

## 新增策略

在 `strategies/` 实现 `select(as_of, market, universe)`，只使用信号日期当时可知的数据，返回 `Selection` 或 `None`。在 `strategies/registry.py` 的受信任启动代码中注册定义，例如：

```python
register_strategy(StrategyDefinition(
    id='fixed_experiment', name='固定标的实验', description='固定标的独立实验', version='1',
    parameters=[dict(name='symbol', label='标的代码', type='string', default='588000.SH')],
    constructor=FixedAssetStrategy,
    symbol_selector=lambda parameters: [parameters['symbol']],
    warmup=lambda parameters: 0,
))
```

定义负责参数归一化、标的提取、预热交易日数和构造；复杂对象参数可覆写 `normalize_parameters`，先调用父实现。工作台验证所声明标的的交易支持和覆盖，不理解具体策略字段名。注册用于仓库内受信任代码，不支持上传任意Python。

## 替换行情提供方

实现 `market_data.provider.MarketDataProvider` 的 `resolve` 和 `download`，通过 `DownloadManager(root, state_dir, provider=YourProvider())` 注入。resolve返回symbol/name/kind；download向指定目录写标准market.csv及包含source/adjustment/market_sha256的清单。

仓库验证CSV、哈希、复权和交易日覆盖；原始响应如声明，目录必须在download内、文件哈希匹配且无符号链接。发布按整支证券替换，并原子重命名；失败暂存不进入可用目录。默认仍使用腾讯，尚未新增第二个真实供应商。

旧downloader/resolver通过Callable适配器兼容：补本地哈希，缺来源标legacy-callable，缺复权按调用参数假设并记录警告。新提供方缺声明会被拒绝。

## 兼容与未完成边界

旧 `strategy.workbench`、`strategy.backtest` 等Python导入由 `_compat.py` 映射到规范模块，保持对象身份及旧测试注入行为。兼容映射随包导入初始化；新代码应使用新路径，不应向别名表添加业务逻辑。磁盘旧平铺文件已移走，直接引用这些旧文件路径的外部脚本需要更新。

当前CLI命令、HTTP接口、请求格式和历史结果保留。旧CLI费用和触发语义尚未统一为工作台请求，comparison仍复用旧CLI辅助函数；本轮没有改写这些行为。网页标的控件仍使用symbol/candidate_symbols约定，新字段名策略的前端控件需后续支持。

任务调度与SQLite仍在jobs/downloads中，尚未提取数据库仓库接口。storage当前承接快照和报告，market_data.repository管理数据版本。真实历史停牌、公司行动及严格成交模型也仍待建设，目录整理不会自动补齐这些能力。
