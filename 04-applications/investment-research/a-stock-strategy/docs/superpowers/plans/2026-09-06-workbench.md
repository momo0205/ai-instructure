# 回测工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 本机浏览器独立运行并比较两种策略，保留可复现任务记录。

**Architecture:** Python 回测服务复用现有引擎；SQLite 任务记录与独立结果目录；同源网页根据策略目录生成表单。

**Tech Stack:** Python 标准库 HTTP/SQLite、pandas、原生 JavaScript/SVG。

## Task 1: 策略和执行服务
- [ ] 在 tests/test_workbench.py 先测未知参数、候选缺失、日期范围、区间之前不成交以及结果快照。
- [ ] 运行 `.venv/bin/pytest tests/test_workbench.py -q` 确认 RED。
- [ ] 添加 registry.py、workbench.py；将策略定义和校验集中，保持固定与排名构造行为。引擎增加可选交易起止日期，历史数据可用于预热。
- [ ] 添加 jobs.py 和 tests/test_jobs.py，先验证独立任务结果与持久化，再实现串行后台任务、取消和重启恢复。
- [ ] 执行新增测试与原有回测测试，审查规范与实现质量。

## Task 2: HTTP 和网页
- [ ] 在 tests/test_web.py 先测 GET 目录、POST 校验、跨源拒绝、非法路径、任务返回结果。
- [ ] 实现 web.py：仅 localhost 的 JSON 路由、静态资源白名单与错误码。
- [ ] 创建 static/index.html、app.js、style.css：策略参数表单、数据集区间、任务状态、结果图表和交易表、复制参数、指标对比。
- [ ] 用真实数据在浏览器运行两个任务，检查控制台与刷新后历史持久化。

## Task 3: 下载与交付
- [ ] 添加 market_download.py 和 tests/test_market_download.py，先验证腾讯原始数据字段解析、重复冲突和截断。
- [ ] CLI 增加 serve 和 download-market，更新 README 的启动、数据准备、新策略注册与限制说明。
- [ ] 完整 pytest，diff --check，审查范围，只提交本任务文件。保存验收结果与启动地址。
