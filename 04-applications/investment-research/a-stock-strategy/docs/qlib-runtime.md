# Qlib 因子引擎

## 当前接入范围

「Qlib 动量择强（独立因子引擎）」实际调用 Qlib 0.9.7 的 `D.features`，计算固定表达式 `$close/Ref($close, N)-1`。它计算分数，本系统处理市场触发、候选门槛、下一交易日开盘成交、持有期和费用。未接入 Qlib 模型训练、TopkDropout 组合管理或 RD-Agent。

与「动量择强（价格规则适配）」不同：后者是本地公式实现，不调用 Qlib；前者需要独立环境，按统一行情日历计算窗口，窗口缺报价时跳过候选。Qlib provider 使用 float32，临界门槛或极近的分数可能与本地浮点计算不同。不强行声称两个策略逐笔相同。

## 安装与启动

在项目根目录执行：

```sh
uv venv --python 3.11 reports/qlib-env
uv pip install --python reports/qlib-env/bin/python 'pyqlib==0.9.7'
.venv/bin/python -m strategy serve --experiment-python reports/experiment-env/bin/python
```

默认使用项目的 `reports/qlib-env/bin/python`。其他安装位置可在启动前设置 `A_STOCK_QLIB_PYTHON` 为解释器绝对路径；此路径仅由服务管理员配置，页面不能传入。应用打包部署时也建议显式配置路径。独立环境不修改基础回测依赖。

## 页面使用

选择「Qlib 动量择强（独立因子引擎）」，选已有候选标的、动量回看交易日和最低动量（0.05 表示5%），按原流程执行回测。页面显示「Qlib 计算因子」阶段，随后进入本地回测。计算有120秒超时，可取消。Qlib 缺失或失败会返回 `QLIB_UNAVAILABLE` / `QLIB_FAILED`，没有隐藏的本地计算回退。

成功结果可同步 MLflow、进行实验比较和批量持有期验证。每个回测任务独立计算因子，当前尚无跨任务缓存；批量任务也会分别计算。日常只需要页面，不需要使用 Qlib 命令或英文界面。

## 审计与边界

任务目录的 `qlib/` 保存输入 CSV、请求、close-only provider、输出 JSON 和 worker.log。结果 `metadata.factor_runtime` 保存实际 Qlib 版本、表达式、日历语义、精度说明、输入/输出 SHA256 及因子值；MLflow 的 result.json artifact 包含这些信息。

行情在任务结束日截断后送入 worker，保留前段历史供指标预热。当前只使用正向历史窗口，不接收任意表达式，不填充缺失报价，不伪造复权 factor；仅计算价格比值，不用 Qlib 模拟订单。原始行情的复权及交易状态限制仍然存在。使用者仍需独立验证策略效果。

官方依据：[Qlib Data Layer](https://qlib.readthedocs.io/en/latest/component/data.html)。本项目只创建该固定表达式所需的 close 字段，并未构造可供任意 Qlib 策略或模型直接使用的完整数据集。

本机实测依赖版本记录在 [qlib-runtime-requirements.txt](research/qlib-runtime-requirements.txt)，用于复现本轮环境；其他平台需重新验证可用 wheel 和版本兼容性。
