# 智能体使用指南

本文件为智能体提供仓库信息和贡献规范。

## 目录结构

```
agent-skills/
├── README.md              # 仓库说明
├── AGENTS.md              # 本文件
├── .githooks/             # Git Hook（不要修改）
├── scripts/               # 工具脚本
│   ├── setup.sh           # 环境初始化
│   └── validate-structure.sh  # 目录验证
├── docs/                  # 设计文档（不要修改）
└── plugins/               # 插件集合
    └── [插件名]/
        ├── README.md      # 插件说明
        └── skills/
            └── [技能]/
                └── SKILL.md
```

## 创建新插件

```bash
mkdir plugins/[plugin-name]
touch plugins/[plugin-name]/README.md
mkdir plugins/[plugin-name]/skills
mkdir plugins/[plugin-name]/skills/[skill-name]
touch plugins/[plugin-name]/skills/[skill-name]/SKILL.md
```

## 命名规范

- **kebab-case**：`qa-test`、`test-case-generate`
- **SCREAMING-KEBAB-CASE**：`QA-TEST`

禁止：大驼峰、小驼峰、下划线、中文。

## 必填文件

| 位置 | 文件 | 说明 |
|------|------|------|
| 插件根目录 | `README.md` | 插件说明（需包含最后更新时间） |
| Skill 目录 | `SKILL.md` | Skill 行为规范 |

## 文档更新时间规范

每次修改插件或 Skill 相关文档后，需更新 `README.md` 头部的最后更新时间。

### 格式要求

- **位置**：plugin 的 `README.md` 头部第一行
- **格式**：使用 `> 最后更新：YYYY-MM-DD HH:mm` 格式（24 小时制）
- **示例**：
  ```markdown
  # 插件名称

  > 最后更新：2026-01-18 21:27

  插件描述...
  ```

### 更新时机

- 新增 Skill
- 修改现有 Skill 功能
- 更新使用说明
- 重大文档重构

### 注意事项

- 不维护版本号，仅记录最后更新时间
- 格式统一使用 `YYYY-MM-DD HH:mm`（ISO 8601 日期+时间格式）

## 常用命令

### 环境初始化
首次使用或贡献代码前，先运行：
```bash
source scripts/setup.sh
```

### 验证目录结构
```bash
sh scripts/validate-structure.sh
```

## 智能体调用规范

调用脚本前：
1. 说明原因
2. 展示命令
3. 等待确认

示例：
```
需要运行 setup.sh 验证环境。命令：source scripts/setup.sh
是否继续？
```
