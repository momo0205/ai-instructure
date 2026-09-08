# 标的数据管理 Implementation Plan

> 使用 subagent-driven-development 执行，按 TDD 验证。用户已在对话批准下拉选择与独立新增代码的设计，沿用现有功能分支及工作目录。

**Goal:** 将下载与回测解耦；只能选择数据就绪且交易模型支持的标的。

**Architecture:** 独立数据管理服务维护下载任务；下载到临时版本，校验后发布不可变数据集。原始数据集和已有任务快照保持不变。HTTP 提供目录与下载接口，原生页面选择目录中标的。

**Tech Stack:** 现有 Python、SQLite、pandas、原生 JS。

- [ ] 后端：新增 instruments.py 与下载任务服务和测试。代码/交易所/名称校验；下载失败可重试；重启未完成任务中断；股票允许准备行情但不进入 ETF 回测列表。新数据保留来源和哈希。
- [ ] 集成：datasets 返回 instruments（symbol/name/kind/backtest_supported/start/end）；请求校验阻止未支持证券；版本目录可冻结到现有任务中。
- [ ] HTTP：GET /api/downloads，POST /api/downloads，GET /api/instruments；保持原有 Host/Origin 边界，下载后台执行。
- [ ] 前端：单选/多选标的，按选中数据集及共同覆盖设置日期；新增独立数据管理区域，代码、区间、提交按钮、状态、重试。
- [ ] 验收：成功与失败下载、旧数据不变、未支持股票拒绝、复制参数及数据切换；完整测试、JS 检查、实际 API 和浏览器验证；更新 README。

接口约定：GET /api/instruments 返回目录列表；GET /api/downloads 返回任务列表，含 id/status/request/error/dataset_id。POST /api/downloads 参数 symbol/start/end，成功返回排队任务。数据集 instruments 是回测表单唯一标的来源。
