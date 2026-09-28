# Qlib 因子运行时接入

目标：网页新策略 qlib_momentum 实际通过 Qlib 0.9.7 表达式引擎计算动量，再用现有本地引擎执行。保留 price_momentum 作为不依赖 Qlib 的独立规则策略。

设计：StrategyDefinition 新增可选 prepare 回调（默认原样返回策略），工作台冻结行情后调用，返回含预计算信号的策略。适配器仅接受固定模板表达式和归一化窗口；读取启动配置 A_STOCK_QLIB_PYTHON，默认项目 reports/qlib-env/bin/python。HTTP 不接受程序路径。隔离 worker 读取任务 CSV、创建 close-only Qlib provider，调用 D.features，一次生成所有信号。缺失报价不填充，以市场日历计算窗口；策略仅在截至信号日完整 N+1 窗口且可交易时选股。子进程超时120秒、可取消、退出清理。无静默fallback。

审计：任务 qlib/ 保存输入、输出、provider、运行日志；metadata.factor_runtime 保存实际版本、固定表达式、calendar语义、输入/输出 SHA256、完整因子值（供 result artifact）。只使用 close，不伪造复权factor，不调用 Qlib 回测或训练。

步骤：
1. RED：无环境明确诊断、子进程失败/超时/取消、固定表达式/输出校验、策略未来数据隔离/日历缺口/排序测试。
2. 实现 adapters/qlib_worker.py 与 qlib_factors.py；新策略及 prepare 合同、回测元数据、页面进度。
3. 独立环境安装版本；真实 Qlib 因子与手算/pandas 对照，真实行情端到端、前缀一致性验证。
4. 网页运行任务并同步 MLflow；文档说明策略规则适配和 Qlib runtime 区别及运行成本。定向验证。

完成证据：99 项相关 Python 测试、25 项前端测试通过，JS语法和diff检查通过。独立审查补充了未prepare显式错误保护。实际 Qlib 0.9.7：3只ETF ×485日 =1455条因子，独立pandas计算容差一致，历史前缀与全历史重叠输出完全一致，真实行情回测17笔交易。浏览器任务259c9985f5434143917d81d0d6a80dd5成功且已同步MLflow run9cd2ff706ec54570a123533f5dd16c27，结果保存实际运行版本。独立环境安装完成，工作台已重启加载。当前不做跨任务缓存、模型训练或Qlib交易引擎替换。
