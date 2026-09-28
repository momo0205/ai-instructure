# 按职责组织包与回测服务拆分

用户批准按策略、行情、回测、应用、存储和入口划分包。本次将实现文件移动到对应目录，顶层保留__init__/__main__、共享domain/validation及集中兼容映射。旧 strategy.xxx 模块导入映射到新模块，避免保留大量平铺转发文件；内部统一使用规范新路径。

workbench拆为application.requests（请求/数据约束）、application.backtests（编排）、storage.snapshots（冻结及结果文件）。任务队列归application，SQLite持久化本轮不改变。Web与CLI入口分别归interfaces.web和interfaces.cli；静态资源迁入Web包并更新打包配置。策略注册归strategies；行情提供方和仓库归market_data；引擎/费用/状态/指标归backtesting。旧CLI业务语义不变，不趁迁移改历史结果。

验证重点：旧新导入对象一致、第三策略和monkeypatch兼容；源码快照包含完整子包、复制前后内容校验仍有效；CLI默认项目根路径保持、wheel包含静态页面和新包；已有四组数据结果一致；完整Python/Node测试和本地API启动。
