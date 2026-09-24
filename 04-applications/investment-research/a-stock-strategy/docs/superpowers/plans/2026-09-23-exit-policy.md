# Exit Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Follow TDD for each behavior change.

**Goal:** 工作台可选择固定期或收盘低于均线退出，结果可审计并兼容旧任务。
**Architecture:** 指标纯计算、退出规则负责意图、原引擎负责撮合。请求与页面通过退出规则目录对接。
**Tech Stack:** Python/pandas、原生 JS、pytest、Node tests。

## 1. 指标、规则与成交
- [x] 在 tests/test_exit_policies.py 添加手算均线、未来数据隔离、暖机/缺失、固定兼容、次日开盘退出、延期不撤销、最长持有和期末持仓测试。先运行验证失败。
- [x] 新增 indicators 与 exit_policies，修改 backtesting/engine.py；保持旧构造签名兼容，追加 exit_policy 与 exit_decision_events。
- [x] 规则采用 `{id:'fixed_holding',parameters:{}}` 或 `{id:'close_below_sma',parameters:{window:20,max_holding_days:20}}`。固定期天数仍来自 holding_period_days。
- [x] 运行新测试及既有 engine/stock/effectiveness 测试，检查普通与 prepared 路径一致。

## 2. 请求、实验和服务
- [x] 在 tests/test_exit_integration.py 验证请求默认/严格校验、API目录、真实执行与保存证据、不兼容对照/批量拒绝；先验证失败。
- [x] requests.py 接受 exit_policy；backtests.py 传入引擎并写入规则/指标版本与退出证据；server.py 提供 /api/exit-policies。
- [x] effectiveness.py 与 studies.py 拒绝非固定退出；实验适配器持久化规则参数；历史比较区分规则和生效参数。
- [x] 运行目标测试，检查新旧请求及快照复制恢复。

## 3. 页面闭环
- [x] tests/exit-policies.test.cjs 验证目录驱动表单、恢复请求、禁用不适用对照、证据和旧任务提示，先验证失败。
- [x] 新增 exit-policies.js；index/app/explanations/research/studies 接入规则配置、规则解释、退出证据及比较标签。
- [x] 更新静态白名单，运行 Node tests 与语法检查。

## 4. 验证、文档与交付
- [x] 全套 pytest、Node tests、git diff --check。
- [x] 本机浏览器执行均线回测、查看证据、复制参数；固定期回归；390px 检查与截图。
- [x] 代码审查、修复问题，写验收文档；只提交本项目文件并推送现有分支。

## 执行合同

后端模块导出 `normalize_exit_policy(value)`（None 映射固定默认，严格参数校验）、`exit_policy_catalog()` 返回 list，每项有 id/name/version/parameters(list: name,label,type,default,minimum,maximum)/description/supports_effectiveness/supports_studies；`build_exit_policy(value, holding_period_days)` 构建引擎规则。新结果 metadata.exit_policy 存规范规则及版本。exit_decision_events 每项至少含 date,symbol,rule,status,reason,close,sma,window,available,held_sessions,planned_exit_date,exit_signal_date。固定期旧成交原因保持 holding period。

已有功能分支 codex/a-stock-breadth-mvp，复用当前独立项目目录，不改动工作空间其他脏文件。用户已确认设计和实现，无需重复审批。
