# Package Layout Implementation Plan

> 使用Superpowers分工、TDD和独立审查，沿用用户批准的分支。

**Goal:** 业务代码按职责组织，回测校验/存储/编排独立，旧调用兼容。
**Architecture:** 规范包路径+集中旧模块别名；页面资源随Web包发布。
**Tech Stack:** Python/setuptools/pytest、原生JS。

- [x] 保存目录、请求与回测结果基线；增加新包导入/快照/CLI路径测试先红。
- [x] workbench拆requests/backtests/snapshots，保留行为与返回格式。
- [x] 移动模块并统一内部导入；集中旧别名，修正__file__路径和资源打包。
- [x] 完整测试、基线比较、wheel资源和独立导入检查；代码审查。
- [x] 更新架构文档、运行服务、提交推送。


2026-09-10验收：271项Python测试、6项Node测试通过。四组（两策略×样例/真实）metrics/equity/trades/events/execution_events/request/warnings均与重构前一致；目录JSON一致。离线wheel构建成功，隔离进程从解包wheel导入、读取静态资源、执行回测成功，无旧平铺业务文件残留。

review说明：拆分实现先以旧workbench为基准验证；主代理复核规范导入、CLI路径、源码快照、对象别名与wheel。独立最终审查代理因额度不可用未完成，未宣称其批准。已验证旧新模块身份、运行任务快照包含完整子包。SQLite与旧CLI编排边界保留并在架构文档明确。
