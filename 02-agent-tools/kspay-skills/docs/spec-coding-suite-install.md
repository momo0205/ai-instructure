# Spec-Coding 流程化 Skill 安装说明

- 内部 Docs 链接：`https://docs.corp.kuaishou.com/d/home/fcACT5rHVHQ891MbmJXG9lUzI`

这是一套可直接导入到 CodeFlicker 的流程化 Skill 组合，用于在**新项目**中快速搭建 Spec-Coding 工作流。

## 推荐安装顺序

### 1. 安装 `spec-coding-bootstrap`（推荐必装）
作用：作为新环境 / 新项目的统一入口，优先复用仓库内模板与 agent 模板，减少首次配置成本。

```text
使用 skill manager 导入 https://cdnfile.corp.kuaishou.com/kc/files/a/design-ai/poify/ccbd783ca231e59ecb39eca41.0.0.zip
```

### 2. 安装 `meta-spec-skill-template`（推荐一起安装）
作用：官方 Meta Spec 通用模板，AI 基于它为当前项目生成专属的 `{repo-name}-meta-spec` skill。

```text
使用 skill manager 导入 https://cdnfile.corp.kuaishou.com/kc/files/a/design-ai/poify/ed158782af257da70b5178911.0.0.zip
```

### 3. 安装 `spec-coding-setup`（兼容原版流程，可选）
作用：保留原始的三步初始化编排能力，适合熟悉旧流程的用户。

```text
使用 skill manager 导入 https://cdnfile.corp.kuaishou.com/kc/files/a/design-ai/poify/ccbd783ca231e59ecb39eca42.0.0.zip
```

---

## 使用流程

安装完成后，分两步使用：

**第一步：初始化环境（全局一次）**
```text
初始化 spec 开发体系
```
或：
```text
在新项目里搭建 spec 工作流
```
AI 会调用 `spec-coding-bootstrap` 完成：
- 创建 `spec-sync` / `mermaid-flow-drawer` / `docs-writer` 等配套 Agent
- 建立 docs 目录规范

**第二步：生成项目专属 Meta Spec Skill**

基于 `meta-spec-skill-template`，AI 会为当前项目生成专属 skill：
```text
基于当前项目，帮我生成项目专属的 Meta Spec Skill
```

> 生成后的 skill 命名规则：`{repo-name}-meta-spec`，保存到 `~/.codeflicker/skills/`

---

## 安装后能得到什么

导入后，这套能力会帮助用户逐步完成：

1. 创建项目级 Meta Spec Skill（基于 `meta-spec-skill-template`）
2. 创建 `spec-sync` / `mermaid-flow-drawer` / `docs-writer` 等配套 Agent 能力
3. 建立 docs 目录规范
4. 形成"需求讨论 → Spec 生成 → 代码实现 → 异步文档回写"的完整闭环

---

## 注意事项

1. 以上链接当前为**内网下载链接**。
2. `docs-writer` 相关能力仍依赖本机可用的 `docs-shuttle`。
3. 如果导入后暂时看不到新 skill，等待约 30 秒或重启 VS Code。
4. 如果用户本地已有同名个人级 skill，个人级版本会优先生效。

---

## 推荐对外转发文案

你可以把下面这段直接发给其他用户：

```text
请按顺序导入这 3 个 skill：

1. spec-coding-bootstrap（入口编排器）
使用 skill manager 导入 https://cdnfile.corp.kuaishou.com/kc/files/a/design-ai/poify/ccbd783ca231e59ecb39eca41.0.0.zip

2. meta-spec-skill-template（官方 Meta Spec 模板）
使用 skill manager 导入 https://cdnfile.corp.kuaishou.com/kc/files/a/design-ai/poify/ed158782af257da70b5178911.0.0.zip

3. spec-coding-setup（可选，兼容原版流程）
使用 skill manager 导入 https://cdnfile.corp.kuaishou.com/kc/files/a/design-ai/poify/ccbd783ca231e59ecb39eca42.0.0.zip

导入完成后：
第一步：初始化 spec 开发体系（全局一次）
第二步：基于当前项目，帮我生成项目专属的 Meta Spec Skill
```
