# Data Modules Implementation Plan

> 使用 subagent-driven-development 分工，TDD与独立审查。

**Goal:** 目录、数据提供方、版本仓库与下载任务职责分离。
**Architecture:** MarketDataProvider resolve/download；LocalDatasetRepository list/prepare/publish；DownloadManager协调，旧入口兼容。
**Tech Stack:** Python、pandas、SQLite、pytest。

- [x] 提供方TDD：Tencent与Callable适配器；目录纯函数移动并保留兼容导入。
- [x] 仓库TDD：prepare冻结基线，publish验证数据并原子发布；datasets/verify_manifests迁出workbench；不再依赖网络或任务。
- [x] 任务接线：provider/repository可注入，旧downloader/resolver保留；实际source清单传播。
- [x] 替换提供方测试、损坏内容/复权失败测试、完整回归、真实目录和结果对比。
- [x] 文档与代码审查、服务更新、提交推送。


验收：256项Python测试、6项Node测试通过；JS语法及git diff检查通过。真实目录与重构前JSON一致，固定/排名策略真实数据的metrics/equity/trades/events/execution_events/request/warnings完全一致。

独立审查修复：新提供方必需来源/复权/hash；raw目录限制在download内并核对文件哈希，禁止符号链接避免原子重命名后证据失效；兼容旧函数仅在适配器补本地证据，缺复权明确warning。测试验证替换提供方、错误不发布、整段替换、原始证据发布后可读、旧队列路由行为。没有下载新的真实行情或修改旧数据。
