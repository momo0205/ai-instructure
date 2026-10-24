# 🧠 AI 工作区（ai-instructure）

> 一个可持续累积的个人 AI 工程空间：手册、工具、研究、应用和记忆都放在一起，
> 换一台机器 clone 下来，按 `bootstrap.sh` 走一遍就能继续。

- 远端：`github.com/momo0205/ai-instructure`（私有，主分支 `main`）
- 项目清单：**[projects.yaml](projects.yaml)** ← 唯一事实源，新增项目先登记
- 引导脚本：**[bootstrap.sh](bootstrap.sh)**
- Agent 规约：**[AGENTS.md](AGENTS.md)**

---

## 🚀 新机器：三步恢复

```bash
git clone git@github.com:momo0205/ai-instructure.git
cd ai-instructure
./bootstrap.sh --check     # 先看缺什么（不装东西）
./bootstrap.sh --install   # 初始化子模块 + 安装各项目依赖
cp .env.example .env       # 填 DEEPSEEK_API_KEY
```

然后按 `bootstrap.sh` 末尾打印的「手动清单」补齐密钥与 SDK。

> `origin` 用了 SSH 别名 `github-momo0205`。新机器要么在 `~/.ssh/config` 里补上：
> ```
> Host github-momo0205
>     HostName github.com
>     User git
>     IdentityFile ~/.ssh/id_ed25519_momo0205
> ```
> 要么把 remote 换成 HTTPS：`git remote set-url origin https://github.com/momo0205/ai-instructure.git`

---

## 📂 目录地图

```
ai-instructure/
├── README.md / AGENTS.md / projects.yaml / bootstrap.sh / .env.example
│
├── 01-infrastructure/              部署手册（HTML，只读参考）
│   ├── vpn-relay/                  VPN 中转站
│   ├── vps-quick-access/           VPS 快速访问
│   ├── vps-rebuild/                VPS 重建 + 代理实测（含 lab 脚本）
│   └── macbook-server/             MacBook 当 AI 服务器
│
├── 02-agent-tools/                 Agent 工具
│   ├── drawio-generator/           自然语言 → draw.io（TypeScript）
│   └── skills-repo/                Skills 仓库（fun-tools / git-tools / spec-helper）
│
├── 03-research/                    研究
│   ├── claude-code-source/         [submodule] Claude Code 逆向源码
│   ├── claude-code-analysis/       Claude 自读源码分析（含 claude-reviews-claude 子模块）
│   ├── jev-decision-lab/           [submodule] JEV 决策实验室（Python）
│   ├── paper-deep-dive/            论文精读工作台（ResNet / Transformer / DDPM）
│   └── rea-investigation/          REA 逆向工具实跑记
│
├── 04-applications/                应用
│   ├── gridbot/                    加密货币网格交易机器人（Python + Docker）
│   ├── agent-evidence-lab/         [submodule] Agent 证据实验室（Java + Python）
│   └── investment-research/
│       ├── Mira/                   [submodule] 投研协议（第三方）
│       ├── a-stock-data/           [submodule] A 股数据工具包（第三方）
│       ├── a-stock-strategy/       A 股日线策略回测（uv + 工作台）
│       ├── mira-server/            Mira HTTP API
│       ├── mira-automation/        写在 Mira 里的自有脚本备份
│       └── finance-ironmao/        财务指标学习站（独立仓库）
│
├── 05-mobile/                      Mira 客户端各形态
│   ├── mira-flutter/               [submodule] Flutter App
│   ├── mira-client/                原生 Android
│   ├── mira-pwa/                   PWA / WebView
│   └── apk-project/                旧 WebView 壳（已归档）
│
├── docs/
│   ├── superpowers/specs/          设计文档
│   ├── superpowers/plans/          实施计划
│   ├── sessions/                   历史 Agent 会话记录
│   └── reports/                    一次性汇报产出
│
├── .memory/                        跨 Agent 记忆（ledger 入库，索引不入库）
└── superpowers/                    [submodule] Superpowers 技能框架
```

---

## 🗂 项目速查

完整字段（运行时 / 入口 / 启动命令 / 状态）见 [projects.yaml](projects.yaml)。

| 项目 | 类型 | 运行 | 状态 |
|---|---|---|---|
| mira-flutter | 子模块 | Flutter | 活跃 |
| a-stock-strategy | 根仓 | Python/uv | 活跃 |
| agent-evidence-lab | 子模块 | Java/Maven | 活跃 |
| jev-decision-lab | 子模块 | Python | 活跃 |
| paper-deep-dive | 根仓 | 静态站点 | 活跃 |
| finance-ironmao | 独立仓 | Next.js | 活跃 |
| mira-server | 根仓 | FastAPI | 维护 |
| Mira / a-stock-data | 子模块（第三方） | Python | 维护 |
| gridbot | 根仓 | Python/Docker | 暂停 |
| mira-client / mira-pwa | 根仓 | Android / Web | 维护 |
| apk-project | 根仓 | Android | 已归档 |
| superpowers / claude-code-* / skills-repo | 子模块/根仓 | 文档技能 | 参考 |

> **子模块现状**：`.gitmodules` 登记了 8 个路径，其中 `Mira`、`a-stock-data` 是标准子模块；
> 其余 6 个在本地是独立克隆（`.git` 是目录），父仓只记录 commit 指针。
> 新机器执行 `git submodule update --init` 会按 URL 拉取，两种形态都能工作。
> 长期方案见下方「已知债务」。

---

## 🧱 归属规则（新增东西前先看这张表）

| 内容 | 放哪里 | 理由 |
|---|---|---|
| 工作区元信息、清单、脚本 | 根仓 | 体积小、需要 review、必须随 clone 带走 |
| 自己长期维护的代码 | **独立仓库**（根仓只登记指针） | 独立 CI / issue / release，可单独分享 |
| 第三方只读代码 | 子模块，钉 commit | 需要可复现，又不想改 |
| 手册、研究、设计文档 | 根仓 `01-/03-/docs/` | 纯文本，值得进历史 |
| 构建产物、APK、依赖 | **不入库** | 可重建；发布包走 GitHub Releases |
| 密钥、签名、本机路径 | **不入库** | 只放 `.env` / `key.properties` |

---

## 🧠 记忆系统（跨 Agent / 跨机器）

记忆分两层，**账本是真相源，向量库只是索引**：

```
.memory/ledger.jsonl   ← 只追加，随 git 同步，可 diff / 可 review
        │ rebuild
        ▼
.memory/qdrant/        ← 向量索引，gitignore，可随时从账本重建
```

```bash
python3 .memory/mem.py add "【模块】做了什么。关键决策：…。踩坑：…"
python3 .memory/mem.py search "关键词"
python3 .memory/mem.py list
python3 .memory/mem.py rebuild   # 换机器后：从账本重建索引
python3 .memory/mem.py export    # 把旧索引导出进账本
```

- 需要 `DEEPSEEK_API_KEY`（`add` 抽取事实、`search` 翻译中文查询）。
- 没配 key 也能用：`add` 照样写账本，`search` 自动降级为账本关键词检索。
- 依赖（一次性）：`pip3 install mem0ai sentence-transformers qdrant-client openai`
- 索引数据放在 `.memory/.cache`，不污染 `~/.mem0`，因此在只允许写工作区的沙箱里也能运行。

---

## 🔐 新机器必须手动准备

| 项 | 用途 |
|---|---|
| `DEEPSEEK_API_KEY` | 记忆系统 |
| SSH 密钥 `id_ed25519_momo0205` | clone / push |
| `key.properties` + `*.keystore` | Android 签名（不入库） |
| `TUSHARE_TOKEN` | a-stock 数据 |
| Flutter / Android SDK / JDK 17 / Docker | 按项目需要 |

---

## 🧾 已知债务

1. **历史已重写**（2026-10-24）：用 `git filter-repo` 清除了历史里的 APK、node_modules、构建产物、keystore 与签名密码，`.git` 从 238 MB 降到 **47 MB**。代价是**所有旧的 clone 必须重新克隆**（commit SHA 全变了）。
2. **APK 不再入库**：`05-mobile/*.apk` 已从索引移除，文件仍在本地。用 `./scripts/publish-apk.sh` 发到 GitHub Releases（需 gh 已登录）。
3. **签名密钥已从历史清除**：`apk-project` 与 `mira-flutter` 的硬编码密码已移除，密钥文件也不再入库。若要公开发布，仍建议更换签名密钥（旧密钥曾在本机明文出现）。
4. **6 个项目是「独立克隆 + 子模块登记」双形态**：功能可用但语义模糊，长期建议统一为清单克隆（见 `projects.yaml`）。
5. **DSH 技能**：`AGENTS.md` 引用的 Superpowers 技能尚未注册为 DSH 原生 skill，目前需按文件路径读取。

---

## 🔑 核心原则

1. **累积而非重复**：每个项目输出可被下一个项目复用的能力
2. **基础设施先行**：VPN → VPS → 本地服务器，逐级搭建
3. **文档即代码**：部署手册放在对应项目目录下
4. **AI 可读**：结构清晰、文件名语义化，Agent 能直接理解上下文
5. **边界清晰**：代码进仓库，产物进 Releases，密钥进本机，记忆进账本
