# 统一诊断实施计划

**Goal:** 将失败与无成交原因在前端明确展示。
**Architecture:** 独立诊断模块；HTTP 和任务管理器适配；引擎提供资金证据，页面只展示。
**Tech Stack:** Python、SQLite、原生 JavaScript。

- [x] 测试 diagnostics 的 JSON 持久化往返、旧文本兼容、未知异常脱敏、无成交/持仓分类。
- [x] 实现 application/diagnostics.py，接入 jobs.py、downloads.py 和 web/server.py。保留 error 字符串。
- [x] 测试并扩展 insufficient_cash 事件的 cash/required_cash/minimum_quantity，使用 FeeRules.calculate。
- [x] backtests.py 输出 diagnostics；历史任务 get 时补摘要。
- [x] 用 Node 测试中文诊断、错误码和零成交胜率；接入 app.js 的接口异常、任务详情及下载列表。
- [x] 运行 pytest、Node 测试与浏览器验收；审查 diff、更新文档并提交当前开发分支。
