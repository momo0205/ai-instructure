# 2026-09-28 会话恢复与退出规则交付核对

## 恢复位置

原会话末尾停在退出规则功能的收尾阶段。实现提交为 `ce8b0240`（2026-09-24），包含固定持有期兼容、收盘低于均线退出、规则参数与退出证据、实验记录和页面操作。恢复时项目目录没有未提交修改，但本地分支 `codex/a-stock-breadth-mvp` 比远端领先一个提交；原计划中“提交并推送”的勾选不能作为推送成功的证据。本轮补做分支同步。

## 本轮验证

- `MPLCONFIGDIR=/private/tmp/a-stock-mpl .venv/bin/pytest -q`：479 passed，52.27 秒。
- `node --test tests/*.test.cjs`：85 passed，0 failed。
- `git diff --check HEAD~1 HEAD`：通过。
- 恢复工作台（启用独立实验解释器），`http://127.0.0.1:8765/`、`/api/exit-policies` 和 `/api/jobs` 返回 HTTP 200。
- 退出规则目录包含 `fixed_holding` 和 `close_below_sma`；均线窗口与最长持有期仍可配置。
- 历史任务列表保留 109 条记录。均线任务 `2168742021ff4c7a99b73777d88662c3` 和固定期任务 `96b4e4ece07a4759af9898eba5acfe3e` 均为 `succeeded`，实验状态均为 `synced`。
- 恢复 MLflow 本机服务，`http://127.0.0.1:5000/health` 返回 `OK`。

本轮执行自动化回归和服务/历史数据核对；浏览器交互与 390px 布局的验收记录来自 2026-09-24，见 [退出规则说明](../exit-policies.md)。本轮没有重新生成验收回测或修改策略行为。

## 后续工作边界

已确认设计和实施计划中的首批均线退出功能已实现。后续路线依次考虑布林带等指标规则、同口径退出参数研究，再进入预测记录冻结和到期评估。它们仍是待细化的后续工作，不属于本次恢复已实现的功能。参见 [研究演进路线](../research-evolution-roadmap.md)。

## 记忆与环境

按工作空间 SOP 尝试了 Mem0 查询及任务回写，均因未设置 `DEEPSEEK_API_KEY` 失败。本文件作为可通过 Git 同步的恢复记录；没有修改其他项目的未提交文件。服务启动方式见 [实验记录与比较](../experiment-tracking.md)。
