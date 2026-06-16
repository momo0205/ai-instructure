# Agent Skills 仓库结构设计决策

## 文档信息

| 项目 | 内容 |
|------|------|
| 撰写人 | Agent（协助周鸿轩） |
| 日期 | 2025-01-18 |
| 主题 | 仓库结构设计、Agent 使用流程 |
| 版本 | v1.0 |

## 一、目录结构设计

### 最终结构

```
agent-skills/
├── .githooks/                         # Git Hook 管理
│   └── pre-push                       # push 时自动检查
├── scripts/                           # 工具脚本
│   ├── setup.sh                       # 环境初始化脚本（检查+配置）
│   └── validate-structure.sh          # 目录结构验证
├── docs/                              # 技术设计文档
│   └── 2025-01-18-repo-structure/     # 按日期命名
├── README.md                          # 仓库说明（用户入口）
├── AGENTS.md                          # 智能体和用户指南
└── plugins/                           # 插件集合
    └── [插件名称]/                    # 例如 qa-test
        ├── README.md                  # 必填：插件说明
        └── skills/                    # 必填：技能目录
            └── [技能]/                # 例如 test-case-generate
                ├── SKILL.md           # 必填：Skill 行为规范
                ├── examples/          # 可选：示例
                └── references/        # 可选：参考文档
```

### 决策要点

1. 根目录只放管理性文件（README.md、AGENTS.md、脚本等）
2. 插件目录下必须包含：README.md + skills/ 目录
3. skills/ 目录不能为空
4. 每个 Skill 目录必须包含 SKILL.md 文件
5. 脚本统一放在 `scripts/` 目录下

## 二、命名规范

### 允许的格式

| 格式 | 示例 | 说明 |
|------|------|------|
| kebab-case | `code-review` | 全小写 + 中划线 |
| SCREAMING-KEBAB-CASE | `CODE-REVIEW` | 全大写 + 中划线 |

### 禁止的格式

- 大驼峰（PascalCase）：`CodeReview`
- 小驼峰（camelCase）：`codeReview`
- 下划线（snake_case）：`code_review`
- 中文：`代码审查`

## 三、Git Hook 机制

### 实现方式

使用 `.githooks/` 目录管理 Hook，通过 `git config core.hooksPath .githooks` 配置。

### 决策理由

- `.git/hooks/` 不受版本控制，用户 clone 后没有
- `.githooks/` 在仓库内，可被版本控制
- 用户和 Agent 都运行 `scripts/setup.sh` 进行验证和配置

### Hook 功能

- 触发时机：`git push` 时（pre-push）
- 检查内容：目录结构规范、命名规范
- 不通过则阻断 push

## 四、脚本设计

### 设计理念

用户和 Agent 都执行同一个脚本 `setup.sh`，此脚本承载两件事：

1. **检查**：验证 Git Hook 是否已配置
2. **初始化**：如果未配置，自动进行配置

### 脚本行为

| 场景 | 脚本行为 | 退出码 |
|------|---------|--------|
| 已配置 | 提示"✅ 已配置"，直接通过 | 0 |
| 未配置 | 自动配置 Git Hook，提示"✅ 配置完成" | 0 |

### Agent 执行要点

1. **贡献前先执行**：`source scripts/setup.sh`
2. **无需判断返回值**：脚本自己处理检查和初始化
3. **输出友好**：脚本执行过程有日志说明，让用户感到安全

## 五、文档整合方案

### 最初方案

- `README.md` - 仓库说明
- `AGENTS.md` - 智能体指南
- `CONTRIBUTING.md` - 贡献规范

### 最终方案

- `README.md` - 仓库说明（用户入口）
- `AGENTS.md` - 智能体和用户共用指南（整合 CONTRIBUTING.md）

### 决策理由

CONTRIBUTING.md 和 AGENTS.md 内容高度重复（目录结构、命名规范、Skill 结构），人和 AI 看同一份文档更简洁。

## 六、设计原则

1. **AI 优先**：让 AI 帮你解决 AI 的问题，用户不需要手动翻文档
2. **简单一致**：人和 AI 看同一份文档（AGENTS.md）
3. **强制但友好**：Hook 检查要强制，但脚本输出要友好
4. **可追溯**：设计决策记录在 `docs/` 目录，方便后续查阅

## 七、设计文档规范

### 文档模板

所有设计文档应包含以下固定信息：

```markdown
# 文档标题

## 文档信息

| 项目 | 内容 |
|------|------|
| 撰写人 | xxx |
| 日期 | yyyy-mm-dd |
| 主题 | xxx |
| 版本 | v1.0 |

## 一、背景

## 二、设计决策

## 三、具体方案

## 四、相关文档
```

### 目录命名规范

- 使用日期前缀：`YYYY-MM-DD-主题描述`
- 全小写英文，中划线连接
- 示例：`2025-01-18-repo-structure`

### 放置位置

- `docs/` 目录下按日期组织
- 每个日期目录下放置具体设计文档
- 不需要额外的 README.md 索引
