# Cumulative Data Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** 累计基础覆盖，按缺口更新，并提供每只证券的可研究时间轴。
**Architecture:** coverage.py 负责读取兼容来源、冲突检测、日期集合和连续区间；foundation_planning.py 负责补齐与来源快照；DataManagementService 连接资产交集与研究组装；timeline.js 展示后端区间。
**Tech Stack:** Python/pandas、SQLite现有任务、原生JS/SVG。

- [x] Task 1：tests/test_coverage.py 先验证分段合并、中间缺口、重复冲突、坏版本隔离、缓存失效；实现 market_data/coverage.py 与 snapshot API。
- [x] Task 2：tests/test_foundation_planning.py 验证全覆盖零请求、只补缺失、单日缺口、错误不污染；实现 application/foundation_planning.py；更新任务调用规划。
- [x] Task 3：tests/test_data_management.py 增加跨版本研究组装、明确区间选择、股票版本不拼接；调整 data_management.py 和路由。
- [x] Task 4：tests/timeline.test.cjs 覆盖日期比例、区间导航、缺口补齐、文本安全；实现 timeline.js、HTML和CSS，接入服务端 coverage。
- [x] Task 5：完整 pytest/node 验证；浏览器实测本机累计覆盖和零网络复用；更新文档并提交当前分支。

验收：428项Python测试通过；浏览器全覆盖零凭据复用、时间轴选区间回测和390px布局通过。旧研究版本通过同一累计快照组装流程，避免显示与执行使用不同依赖。
