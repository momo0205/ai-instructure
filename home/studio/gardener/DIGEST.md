# 账本摘要

> 由 `home/studio/gardener/gardener.py` 生成，账本本身不改。

## 未分类（4 条）

最近：Root cause 1 of the Mem0 fix: the local mem0ai package had been upgraded to 2.0.7, which removed top-level user_id/limit parameters — search must now use top_k plus filters={user_id}, get_all must use filters, while delete_all/add still us…

更早：User fixed the unavailable Mem0 cross-agent memory system in the ai-instructure/.memory project, identifying three root causes and verifying the fix by success…

## agent-evidence-lab/deep-review（2 条）

最近：【agent-evidence-lab/deep-review】工具调用改造成功：REPORT 阶段改为 schema-only 工具 emit_research_report + tool_choice=required 后，用同一份已存导出（v2+v4、4份材料）单次调用即得到首份通过结构/引用校验的报告——REPORT_VALIDATED，25955ms、6848/3968/10816 Token，6条发现/6个子问题/16处引用。关键踩坑：1) DeepSeek 的…

更早：【agent-evidence-lab/deep-review】把 REPORT 阶段从"模型写自由 JSON 文本"改成"工具调用提交"。关键决策：新增 schema-only 工具 emit_research_report + tool_choice=required，schema 的必填字段与 maxLengt…

## ai-instructure/工作区治理（1 条）

最近：【ai-instructure/工作区治理】2026-10-24 把工作区改造成可迁移形态。1) 重写 .gitignore 并从索引移除 1150 个构建产物（跟踪文件 1640→512），APK 与 keystore 移出索引；2) 新增 projects.yaml（21 个项目清单）、bootstrap.sh（环境检查/子模块/依赖）、.env.example；3) 重写 README 与 AGENTS 记忆 SOP，根目录会话记录归档到 docs/sessions，…

## ai-instructure/发布（1 条）

最近：【ai-instructure/发布】2026-10-24 两次 PR（#3 workspace/portability、#4 consolidate/research-into-main）已合入 main：跟踪文件 1,640→513，移除 1150 个构建产物，APK 与 keystore 出库，CI workflow 与 VPS 手册回到 main，子模块指针更新为 jev 9ec897c / mira-flutter 1e559f9 / agent-evidence…

## 工作区协作（1 条）

最近：【工作区协作】采纳父仓 main 的并发写机制：ledger 回写统一走 ./scripts/mem-commit.sh（先 pull --rebase --autostash、只提交 .memory/ledger.jsonl、推送被拒重试 3 次），冲突由 .gitattributes 的 merge=union 自动取并集；子模块代码只在 worktree 里改、只推子模块分支，子模块指针等合并时统一更新，父仓代码/文档走短命分支+PR。独立验证：在临时仓库用 merg…

## finance-ironmao（1 条）

最近：【finance-ironmao】2026-10-24 为独立仓库补上 remote：分支从 feature/finance-learning-site 改名为 main，推送到 github.com/momo0205/finance-ironmao（私有，9 个提交、154 个文件）。推送前安全检查通过：无密钥、无 >1MB 大文件。父仓的 projects.yaml 与 README 已更新。同时完成父仓历史重写：用 git filter-repo --invert-p…

## Mira/服务端（1 条）

最近：【Mira/服务端】mira-server 同时服务两类客户端，端口 8080。Flutter 走 REST：GET /health、GET /api/services、GET /api/services/{id}/reports、GET /api/services/{id}/reports/{reportId}；PWA 走即席查询：POST /research、POST /briefing、POST /industry，另有 POST /api/trigger 供 cro…

## Android/Flutter 构建环境（1 条）

最近：【Android/Flutter 构建环境】踩过的坑：Python3.9 不支持 dict|None 语法，要用 Optional；pip 装包用清华镜像；sdkmanager 不认 http_proxy 环境变量，必须 --proxy=http --proxy_host=127.0.0.1 --proxy_port=7890；Gradle 代理要写进 ~/.gradle/gradle.properties 的 systemProp.http[s].proxyHost/Po…

## home/Agent 空间（1 条）

最近：【home/Agent 空间】2026-10-24 在工作区里建了 Agent 自己的房间 home/：me/WHO.md（工作方式与边界）、me/JOURNAL.md（只追加的日志）、studio/IDEAS.md（6 个自选项目）、studio/pulse/pulse.py（工作区脉搏，打印 20 个项目最后提交/未提交/停滞状态）。AGENTS.md 已写入阅读顺序：WHO → JOURNAL → 账本 → projects.yaml。关键判断：账本只记事实，home…
