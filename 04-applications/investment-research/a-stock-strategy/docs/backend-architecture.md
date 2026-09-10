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
│   ├── jobs.py                 # 回测队列，依赖任务仓库接口
│   ├── downloads.py            # 下载队列、提供方/仓库协调
│   ├── simulation.py           # Web/CLI/比较共用运行合同
│   ├── legacy_config.py        # 旧TOML输入适配
│   ├── configuration.py        # TOML配置模型与解析
│   ├── comparison.py           # 策略比较应用流程
│   ├── recommendation.py       # 旧推荐流程
│   └── llm.py                  # 可选报告解释接口，回测不需要
├── storage/
│   ├── snapshots.py            # 冻结数据/源码/请求及结果JSON
│   ├── task_repository.py      # 任务存储接口与SQLite实现
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
    parameters=[dict(name='symbol', label='标的代码', type='string', role='instrument', default='588000.SH')],
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

当前CLI命令、HTTP接口、请求格式和历史结果保留。Web和CLI --request调用同一个backtests.execute；旧TOML经legacy_config转换为SimulationPlan，Web与旧配置均经run_simulation运行，比较流程也调用该服务。旧配置的触发和费用语义保留为legacy_toml profile，报告明确标记；应用层不再反向依赖CLI。

jobs/downloads已通过TaskRepository访问任务数据，SQLiteTaskRepository保持原表结构；可注入替代存储。任务管理器拥有仓库生命周期并负责关闭；同一仓库不应共享给多个管理器。执行仍采用本地单线程队列，没有引入分布式执行器。真实历史停牌、公司行动及严格成交模型仍待建设。


## 参数驱动页面

页面不识别特定参数名称。标的字段声明 `role='instrument'`，`type='string'` 渲染单选、`type='array'` 渲染多选。可以使用 assets、target 等任意名称，symbols回调须返回实际使用标的。没有标的角色声明的策略明确显示尚未配置可视化，仍可从后端接口执行。

boolean渲染复选框（false合法）；number/integer渲染数字输入；string配合options或enum渲染选项；普通array/object使用JSON输入。复制任务会保留实际数据类型。后端仍最终校验类型、范围和枚举值。新的业务参数只需定义schema，新的控件种类仍需要扩展通用渲染器。

## 任务存储合同

`TaskRepository`提供create/get/list/transition/interrupt/close；transition必须原子检查期望状态，避免取消后再写成功。SQLite实现兼容旧jobs/downloads表，查询回测历史不加载result。通过 `JobManager(..., task_repository=...)` 或 `DownloadManager(..., task_repository=...)` 注入；下载的数据版本仓库仍使用独立repository参数。

## CLI与网页相同请求

保存请求JSON，例如 `{"dataset_id":"mvp_sample","strategy_id":"fixed_asset","parameters":{"symbol":"588000.SH"}}` 到request.json：

```bash
.venv/bin/python -m strategy backtest --request request.json --project-root . --output reports/request-run
```

结果为与网页相同的result.json和snapshot。--request与--config互斥；旧--config仍生成原CSV/图表报告，其内部执行已共用SimulationPlan，不再由CLI构造运行逻辑。两种输入的默认规则可能不同，因此比较时应使用同一请求或明确审查legacy_toml成本参数。
