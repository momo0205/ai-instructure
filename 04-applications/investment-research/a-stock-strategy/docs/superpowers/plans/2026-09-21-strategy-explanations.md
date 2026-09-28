# Strategy explanations Implementation Plan

> Execute with executing-plans; frontend bounded work may run independently under the execution skill. User approved implementation in conversation.

**Goal:** 在页面解释每次动量选股及信号到成交的过程。
**Architecture:** 同一评估结果用于选择与留痕，引擎记录真实决策，独立前端模块展示。旧结果兼容。
**Tech Stack:** Python/pandas, pytest, vanilla JS, node:test, Playwright。

- [x] 测试：tests/test_decision_explanations.py 对两种动量 evaluate、缺失和同分、引擎持仓/时序、JSON留痕写断言；运行 pytest 观察缺少API失败。
- [x] 策略：momentum.py 与 qlib_momentum.py 提供 evaluate 返回 (Selection|None, list[dict])，select代理；分数与原公式相同，失败候选状态明确。
- [x] 引擎：decision_events 默认列表；在原择股点评估并保存，不重复调用。执行事件关联 signal_date/entry_date/planned_exit_date；application/backtests.py 导出。
- [x] 前端：explanations.js 独立模块，规则与结果渲染；app.js/index.html 接入；tests/explanations.test.cjs 覆盖旧结果及规则。
- [x] 验证：pytest 全套、node --test tests/*.test.cjs、JS语法、git diff --check，浏览器创建样例查看解释、移动宽度。发现差异修复后再汇报。
- [x] 文档：增加验收步骤；仅本轮文件提交，保留其他项目改动，服务空闲时更新本地实例。
