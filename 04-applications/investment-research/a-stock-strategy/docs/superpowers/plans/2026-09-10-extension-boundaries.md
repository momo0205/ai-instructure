# Extension Boundaries Implementation Plan

> Superpowers分工、TDD、审查与完成验证。

**Goal:** 完成任务存储接口、共用回测入口、schema驱动表单。
**Architecture:** 仓库注入；SimulationPlan共用运行服务；参数role/type驱动渲染。
**Tech Stack:** Python/SQLite/pytest、原生JS/Node。

- [x] 存储接口/SQLite适配器测试先红；迁移两个任务管理器并验证替代仓库和旧数据库。
- [x] 共用运行服务和旧配置适配器；CLI增加--request，保留--config；比较流程移除CLI依赖。
- [x] 参数schema与通用控件/序列化；新字段名第三策略、布尔/枚举往返测试。
- [x] 两入口相同请求及旧配置基线，全量测试与浏览器；模块审查和文档。
- [x] 更新服务、提交推送。


验收：281项Python、9项Node通过；Node测试运行真实表单渲染/序列化/复制函数。三组旧TOML mvp/baseline/real_breadth及两种工作台策略真实数据业务结果与重构前一致。CLI --request结果与Web应用execute完整JSON相等；替代内存仓库真实执行回测与下载且不创建SQLite。独立只读审查未发现阻断问题。

服务更新后旧数据库正常读取，新任务0f1c3e7298844070a3c01f2410a5a30d成功持久化；schema包含instrument角色。浏览器工具没有可用连接，实际浏览器交互验收未完成，不声称通过；已执行真实DOM函数测试及本地API验收。

边界：工作线程仍本地单线程，SQLite是默认仓库实现；旧TOML适配器保留历史模型差异并报告legacy_toml。可视化策略须声明标的role，新增控件类型仍需扩展通用渲染器。三个既定耦合点已解决，未引入新数据源或严格成交模型。
