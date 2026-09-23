# 数据管理模块拆分

沿用已批准的单体模块化路线。本轮保持下载与回测分离、API/CSV/清单格式兼容，不引入新外部服务。

instrument_catalog.py：纯代码校验和支持范围判断，不联网、不持有队列。
market_provider.py：MarketDataProvider 接口（resolve/download），TencentMarketDataProvider 适配现有报价与日线下载器；CallableMarketDataProvider 兼容旧 downloader/resolver 注入。
dataset_repository.py：数据集列举、哈希校验、prepare 基线冻结、publish 合并及原子重命名。仓库不联网、不依赖工作台/任务模块；发布来源取实际下载清单，不硬编码腾讯。
instruments.py：保留旧导入兼容入口及 DownloadManager 任务生命周期；_publish 仅协调 prepare、resolve、download、publish。
workbench.py：调用仓库目录与校验，移除下载模块循环依赖；回测执行和快照暂留本轮范围外。

提供方输出合同为 market.csv 与 market_manifest.json，标准日线列及目标日期完整覆盖；raw_dir如存在必须位于暂存数据目录。股票缺行继续拒绝，不猜测停牌。复权、来源和内容哈希应验证，错误不得发布managed版本，基线不修改。

验证：替换假的非腾讯提供方可成功下载与发布，实际来源正确；仓库可以独立列举/发布；失败不出现可见版本，旧注入与路由继续通过；真实目录及两策略结果与重构前一致。通过后提交既有分支。
