# Strategy Extension Implementation Plan

> 使用 superpowers:subagent-driven-development 执行，TDD与独立审查。

**Goal:** 新策略通过注册定义接入后端，无须更改工作台策略分支。
**Architecture:** registry 定义参数校验、标的提取、预热与构造合同；workbench 保留数据及任务约束。
**Tech Stack:** Python、pytest，现有原生JS页面。

- [x] 在 tests/test_strategy_extension.py 注册带不同标的字段的测试策略，验证工作台运行及预热、不合法参数与默认值隔离，先跑失败测试。
- [x] registry.py 引入 StrategyDefinition 与显式 register/get 定义接口；共用数值校验移至 validation.py；内置策略定义拥有其参数处理和预热规则。catalog 保持JSON兼容。
- [x] workbench.py 使用 definition.normalize_parameters、symbols、warmup_sessions、build；去掉策略名、权重名和参数名判断。既有策略代码不更改。
- [x] 验证第三策略集成与旧校验；比较重构前后两个策略完整业务结果；全pytest及Node测试。
- [x] 独立代码审查，README新增策略示例，记录边界与验证结果，提交现有开发分支。


2026-09-09 验收：237 项 Python 测试、6 项 Node 测试通过，JS语法与git diff检查通过。两策略×样例/真实股票四组的 metrics、equity、trades、events、execution_events、request、warnings 与 0c7521eb 重构前结果完全一致，catalog JSON 相等。

审查：独立审查未发现后端范围额外阻断问题；随后补齐 string/array/object/boolean 类型及非负整数预热合同，并由主代理检查实现和全测试。测试第三策略使用 assets/history 字段，无需修改工作台分支。前端特殊字段语义与旧CLI统一留在后续批次，详见 backend-architecture.md。
