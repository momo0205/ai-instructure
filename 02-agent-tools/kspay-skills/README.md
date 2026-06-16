# kspay-skills

这是一个用于存放和分享自定义 CodeFlicker skills 的仓库。

## 当前内容

```text
.codeflicker/
├── agents/
│   ├── docs-writer.md
│   └── mermaid-flow-drawer.md
└── skills/
    ├── my-project-docs-guide/
    ├── spec-coding-bootstrap/
    └── spec-coding-setup/
```

## Skills 说明

### `spec-coding-setup`
- 原版初始化编排器。
- 适合已经具备 `docs-shuttle`、`my-project-docs-guide` 等外部依赖的环境。
- 强项是流程清晰、职责拆分明确。

### `spec-coding-bootstrap`
- 本仓库新增的更优版 bootstrap skill。
- 目标是把初始化所需模板和常用 agent 模板尽量收敛到仓库内。
- 优先复用仓库中的：
  - `.codeflicker/skills/my-project-docs-guide/`
  - `.codeflicker/agents/mermaid-flow-drawer.md`
  - `.codeflicker/agents/docs-writer.md`
- 相比原版，它更适合在“新项目 + 新环境”里做第一步落地。

## 推荐使用方式

### 快速入口
如果你要把这整套流程化 skill 直接发给别人安装，优先看：

- 本地文档：`docs/spec-coding-suite-install.md`
- 内部 Docs：`https://docs.corp.kuaishou.com/d/home/fcACT5rHVHQ891MbmJXG9lUzI`

### 场景 1：当前仓库内直接使用
把本仓库拉到本地后，等待 CodeFlicker 扫描项目级目录：

- `.codeflicker/skills/`
- `.codeflicker/agents/`

通常 30 秒内会自动发现新增 skill；如果没有生效，重启 VS Code 即可。

### 场景 2：分享给其他用户
最稳妥的方式是分享某个具体 skill 目录，而不是整个仓库。

例如要分享 `spec-coding-bootstrap`，**在仓库根目录**执行：

```bash
SKILL_MANAGER_SCRIPT="$HOME/.codeflicker/internal/skills/skill-manager/scripts/publish-skill.sh"
bash "$SKILL_MANAGER_SCRIPT" "$(pwd)/.codeflicker/skills/spec-coding-bootstrap"
```

执行成功后会得到一个 CDN URL。其他用户在 CodeFlicker 中输入：

```text
使用 skill manager 导入 <CDN_URL>
```

如果要分享 `spec-coding-setup`，把路径替换为：

```text
$(pwd)/.codeflicker/skills/spec-coding-setup
```

## 推荐打包策略

### 仅分享原版初始化器
适合已经有基础环境的同事：
- 打包 `.codeflicker/skills/spec-coding-setup`

### 分享更优版 bootstrap
适合要快速在新项目落地的同事：
- 首先打包 `.codeflicker/skills/spec-coding-bootstrap`
- 如对方也需要通用模板，再附带打包 `.codeflicker/skills/my-project-docs-guide`

### 分享整个仓库
适合团队共建：
- 直接把仓库地址给对方
- 对方 clone 后即可获得项目级 skills 与 agents

## 注意事项

1. 项目级 skill 会随仓库版本控制，适合团队协作。
2. 用户级 skill 优先级高于项目级 skill；如果对方本地已有同名个人 skill，实际生效版本可能不是仓库中的版本。
3. `docs-writer` 仍依赖本机可用的 `docs-shuttle`。
4. 分享命令里的 `SKILL_MANAGER_SCRIPT` 是一个环境相关路径；如果你的安装目录不同，请替换为本机 `skill-manager` 的实际脚本路径。
5. `spec-coding-bootstrap` 解决的是“尽量减少首次依赖”，不是完全脱离 CodeFlicker 能力边界的离线安装器。
