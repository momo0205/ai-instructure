# 后端模块与扩展路线

本项目保持单进程单体应用，模块通过 Python 接口合作。模块拆分以新增功能时需要修改的范围衡量，不以目录数量衡量。

## 当前依赖与职责

| 模块 | 责任 | 当前边界 |
| --- | --- | --- |
| web.py | HTTP 路由、安全校验、JSON 响应 | 转发给工作台与任务服务 |
| registry.py / strategies/ | 策略目录、参数规范、标的与预热要求、选股算法 | 工作台调用统一定义；内置注册在启动时完成 |
| workbench.py | 回测请求的数据约束与执行编排 | 数据目录、快照仍在此；待拆分 |
| backtest.py | 日频订单、资金、持仓和净值 | 调用费用与交易状态规则 |
| fees.py | 费用规则匹配与资金预算 | 按日期、证券类型、方向计算 |
| tradability.py | 状态证据接口与成交资格 | 可替换 StatusProvider；真实历史状态尚未齐备 |
| jobs.py | 持久任务与本地工作线程 | SQLite 与线程调度仍在同一个类中 |
| instruments.py | 标的识别、可回测目录、下载任务及发布 | 仍需拆开目录、下载编排及版本存储 |
| market_download.py / data_sources.py | 外部数据获取 | 行情下载仍以腾讯实现为主，尚非统一提供方接口 |

## 后续分批顺序

1. 策略定义合同：新增后端策略不修改工作台的具体策略分支。保持原 API 参数形状和回测结果。
2. 数据服务：分离标的目录、数据源适配、数据版本仓库；下载服务负责调度和发布，不直接决定交易规则。
3. 回测应用服务：分离请求校验、快照存储和执行编排，让网页与 CLI 接入同一应用入口；迁移旧 CLI 必须显式处理其历史触发和费用语义。
4. 任务与存储：提取任务仓库接口，保留 SQLite 实现及单线程执行器；未来按实际负载替换执行器。

不在此次重构中引入分布式队列、微服务或运行时任意 Python 上传。真实状态数据、完整公司行动与严格成交模型属于数据/模型能力建设，不会因接口拆分自动完成。

## 扩展合同的边界

当前策略扩展重构覆盖后端工作台。前端标的选择控件仍按 symbol/candidate_symbols 字段约定渲染；使用其他字段名称的新策略可通过后端接口接入，但其页面控件需要后续增加语义角色声明。旧 CLI 仍采用兼容入口，尚未统一为工作台请求模型。

策略必须只用信号日期当时可知的数据，参数应为 JSON 可序列化值。注册仅用于受信任的仓库代码；测试注册应隔离，避免污染生产目录。回测冻结 Python 源码用于审计，不自动重放任意历史运行环境。

## 新增后端策略示例

在 `strategies/` 实现 `select(as_of, market, universe)`，返回 `Selection` 或 `None`。然后在 `registry.py` 的受信任启动注册代码中添加定义，例如复用固定标的算法形成一个独立实验入口：

```python
register_strategy(StrategyDefinition(
    id='fixed_experiment',
    name='固定标的实验',
    description='独立版本的固定标的实验入口',
    version='1',
    parameters=[dict(name='symbol', label='标的代码', type='string', default='588000.SH')],
    constructor=FixedAssetStrategy,
    symbol_selector=lambda parameters: [parameters['symbol']],
    warmup=lambda parameters: 0,
))
```

`normalize_parameters` 负责参数类型、范围与默认值；需要对象内部校验时覆写该方法并先调用父实现。`symbols` 声明实际使用的数据标的，`warmup_sessions` 声明需要的历史交易日数；`build` 构造算法实例。工作台统一验证所声明标的的可回测资格和数据覆盖，不自行理解策略的字段名。

`catalog()` 返回独立的 JSON 目录副本；不要修改已注册定义作为配置手段。费用、初始资金、持有期属于回测请求，不应混进选股算法的参数。新增规则后先用样例集测试参数拒绝与预热，再与已知真实结果对比。
