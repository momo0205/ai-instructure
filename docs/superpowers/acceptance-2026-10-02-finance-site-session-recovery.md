# 2026-10-02 金融学习站会话恢复与部署核对

## 本轮范围与证据

用户要求先恢复和总结前一会话，再判断后续工作。本轮读取本机会话日志、项目文档、Git 状态、Sites 当前状态及公开 DNS，并核对本地页面。未发布新版本、修改站点访问权限或绑定域名。

共享链接的网页抓取未成功；本机保留了对应工作会话：`01a0ec2b-935f-7490-8eb5-15f1eca8d2c6`，包括 2026-09-29 至 2026-10-02 的内容扩展与部署排查记录。结论以该日志、当前文件和实时返回值交叉核对。

## 主线与支线

| 对象 | 当前状态 | 接续方向 |
| --- | --- | --- |
| `a-stock-strategy` 投资研究平台 | 已有回测、行情与数据管理、实验档案和批量研究、固定期与均线退出、独立技术分析及 SMA/EMA/布林带/量均线 | 依据现有研究路线继续扩展退出规则、同口径参数研究，再设计冻结预测和到期评估 |
| `notes.ironmao.com` Agent 工程笔记 | 已部署的独立 Sites 站点，本轮现网 HTTP 200 | 可参考其 Worker 部署流程与域名配置 |
| `finance-ironmao` 金融学习站 | 入门五课、进阶五篇、图解和教学交互已实现；线上部署失败 | 收尾部署与域名，再回到投资平台主线 |

金融学习站是独立仓库，位于 `04-applications/investment-research/finance-ironmao/`；不是投资研究平台的线上服务。其内容依次覆盖 K 线、均线、布林带、成交量/额和综合读图。此前新增 15 幅图解。

## 新站部署状态

- 项目：`appgprj_6abb620df58c8191ad4ac4247280cca4`，名称「Ironmao 金融学习」，slug `ironmao-finance-learning`。
- Sites 已保存 4 个版本；当前预览与正式 URL 均为空，域名绑定列表为空，访问模式为 `custom`（仅所有者）。
- 第 3 版（提交 `6b63e27`）部署 `appgdep_6abcd5442bc08191899ed5cc490b552e`：`failed`。
- 第 4 版（提交 `b92ca08`）部署 `appgdep_6abcda94b9c88191a705bba3692b003f`：`failed`，更新于 2026-09-30 09:47:08 UTC。
- 两次部署都返回 `AppGen deployment failed.`，`provider_deployment_id` 为空。日志工具返回生产日志不可用。
- 之前发现的压缩包目录问题已通过官方打包脚本修正，并保存为新版本后再次部署，仍失败。因此不能把现状仅归因于旧压缩包格式。
- 当前无法证明根因是代码、静态发布路径、项目开通状态或部署服务故障；`expected_url: null` 只能作为线索。

## 域名与旧站

- `notes.ironmao.com` 的公开 CNAME 为 `custom-domains.chatgpt.site.`；HTTPS 返回 200。
- 旧站交接文档给出的平台地址是 `https://agent-engineering-notes.team-gpt-8741.chatgpt.site`；旧站使用 Worker 产物。
- 本轮 `dig +short finance.ironmao.com` 无结果；新 Sites 项目也没有域名绑定。
- 当前连接列出的站点只有新站；用旧站项目 ID 查询返回 `Sites project not found`。这不代表旧站下线，其现网状态和 DNS 已独立验证。

## 中断点与本地核对

上次正在比较静态发布与 Worker 发布，实验尚未完成。独立仓库 HEAD 为 `b92ca08`，留下两处未提交改动：

1. `.openai/hosting.json`：移除了 `static.directory`，只保留项目 ID。
2. `vite.config.ts`：对可选的 D1/R2 配置添加类型声明。

当前 `next.config.ts` 仍保留 `output: 'export'`。不能把这组配置当成已经完成的 Worker 方案；接续时应先核对并统一构建模式。当前没有本机 8787 Worker 监听，只有 5173 学习站预览。

本轮新鲜验证：

- `node --experimental-strip-types --test tests/*.test.mjs`：21 passed，0 failed（包括计算、十篇课程、14 个静态页面、图解和禁止索引）。
- `npx tsc --noEmit`：退出码 0。
- `git diff --check`（金融站仓库）：退出码 0。
- 本地 `/learn` 和 `/learn/advanced`：HTTP 200。

没有在本轮重新运行生产构建或投资平台全量测试；投资平台功能状态根据现有 README、设计及已提交实现恢复。

## 建议的接续顺序

1. 完成一次受控 Worker 对照：先隔离现有实验改动，核对与旧站相同的构建模式；验证 Worker 首页、十篇课程和客户端交互，检查正式部署包清单、入口与静态资源路径。
2. 将验证后的配置保存为独立新提交和 Sites 新版本，避免沿用旧版本归档；先得到所有者私有可访问地址。
3. 若同一项目的有效 Worker 包仍只有通用错误，保留部署 ID、版本 SHA、包校验和与返回值，进入 Sites 项目/部署服务排查；不要继续盲目修改课程内容。Cloudflare Pages 可作为另行选择的备选托管方案。
4. Sites 部署成功后，按平台实际要求绑定 `finance.ironmao.com` 并配置 Cloudflare DNS，再核对课程路由、访问权限和索引策略。域名配置本身不要求重新构建；代码或部署模式变更才需要重新构建。
5. 学习站收尾后回到投资平台，细化布林带等退出规则、退出参数研究、冻结预测和到期评估的下一阶段设计。

## 记忆同步

工作区 `git pull --ff-only` 显示已是最新。按 SOP 尝试两次 Mem0 查询及一次回写，均因缺少 `DEEPSEEK_API_KEY` 失败；本文件作为可同步的恢复记录。其他项目和未提交的 Worker 实验改动不纳入本轮提交。
