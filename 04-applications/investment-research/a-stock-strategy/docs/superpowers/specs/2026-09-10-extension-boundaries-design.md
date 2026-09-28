# 完成三处扩展边界

用户授权继续解决任务存储耦合、CLI/Web重复业务及前端字段名依赖。保持单体、本地数据和旧历史结果兼容。

任务：storage定义任务仓库接口，SQLite实现保留原数据库schema。jobs/downloads只负责任务生命周期与业务调用，条件状态更新避免取消后写成功；可注入替代仓库验证无SQLite执行。队列/线程继续本地单线程，不引入分布式基础设施。

入口：CLI backtest支持互斥--request JSON与--config旧TOML，JSON和网页调用相同application.backtests.execute。提取共用SimulationPlan/run_simulation，工作台与旧配置适配器均转换到同一运行合同；旧成本、trigger与默认参数以legacy profile明确保留。CLI只路由/输出；比较流程不得反向依赖CLI辅助函数。

表单：策略参数schema增加role=instrument，数组按type决定多选；布尔、数值、枚举、字符串、数组和对象使用通用控件/序列化。候选标的汇总按role选择，不按名称。注册第三策略的任意字段名在UI级测试可提交并由后端执行；后端继续最终校验类型、范围与选项。

验证：旧SQLite文件兼容、取消/失败/重启、替代存储；CLI/Web同请求结果一致、旧TOML结果不变；新字段名与bool/enum参数往返及旧表单回归。独立模块测试、全回归、真实数据基线、浏览器与发布。
