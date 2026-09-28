# 市场基础数据更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将指数和全市场广度更新为不可变版本，让近期行情资产能够准备研究并回测。

**Architecture:** 基础数据更新使用独立后台队列与暂存目录；腾讯提供指数，Tushare 提供逐日全市场涨跌截面。验证指数与广度日期完全一致后原子发布 foundation_*。研究准备自动选择覆盖资产最多的完整基础版本；旧 real/managed_* 不改变。Token 只驻留内存或环境变量，不进入任务数据库、日志或清单。

**Tech Stack:** Python/pandas/SQLite，原生 JavaScript。

## Task 1 基础版本与研究组装
- [x] 先在 tests/test_foundations.py 验证近期资产可以选中新基础版本、损坏版本不被使用、旧文件不改变。
- [x] market_data/foundations.py 实现更新与完整校验：download(start,end,stage)、指数/广度日期一致、哈希和相对原始证据路径、原子 rename。
- [x] application/data_management.py 枚举基础版本并按真实共同覆盖选取；repository.py 为 LocalDatasetRepository 增加 baseline_id 参数，默认 real，记录真实父版本。
- [x] 跑定向 pytest，确认缺口、失败发布、日期验证。

## Task 2 后台任务与接口
- [x] tests/test_foundation_updates.py 覆盖错误日期、凭据不持久化、成功和失败任务状态。
- [x] application/foundation_updates.py 单队列更新；GET/POST /api/foundation-updates，GET 凭据可用状态放入 data-management。
- [x] server.py 管理生命周期；令更新任务在页面自动轮询。

## Task 3 页面与真实验收
- [x] 基础数据页新增日期、密码型临时 token、更新按钮和状态；资产缺依赖引导进入该页。
- [x] JS 测试验证请求、错误显示和凭据清除。
- [x] 尝试真实源下载最近闭市区间，再准备已有茅台资产并运行回测。
- [x] 完整 pytest/node 测试，文档记录实际能力与外部权限限制。

## 验证记录
2026-09-23：旧版本不变；近期茅台浏览器回测成功（1笔成交）；实际后台基础更新成功至2026-09-22。自动化验证见本轮交付记录。

最终验证：406 项 Python 测试、62 项 JavaScript 测试通过；浏览器近期茅台回测成功。审查修复研究版本广度证据引用、必需清单校验、任务状态与目录读取时序。
