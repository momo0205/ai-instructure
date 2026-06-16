# Skill 类型详解：项目级 vs 个人级

## 概述

CodeFlicker 支持两种类型的 skill：项目级（Project）和个人级（Personal）。理解这两种类型的区别对于正确组织和管理 skill 非常重要。

## 项目级 Skill (Project)

### 定义

项目级 skill 是存储在当前项目目录下的 skill，通常用于团队共享的工作流程和项目特定的规范。

### 存储位置

项目级 skill 存储在项目根目录下的以下位置之一：

```
{project-root}/.kwaipilot/skills/
{project-root}/.opencode/skills/
{project-root}/.claude/skills/
```

### 特点

**优点**：
- ✅ 随项目一起版本控制
- ✅ 团队成员自动共享
- ✅ 适合项目特定的工作流程
- ✅ 新成员加入即可使用
- ✅ 确保团队规范统一

**缺点**：
- ❌ 仅在当前项目可用
- ❌ 需要在每个项目中单独维护
- ❌ 不适合跨项目通用的技能

### 适用场景

项目级 skill 适合以下场景：

1. **项目特定的代码规范**
   - 代码审查检查清单
   - 项目编码风格指南
   - 项目特定的测试规范

2. **团队协作流程**
   - 发布流程
   - 部署步骤
   - 代码合并规范

3. **项目工具链使用**
   - 构建脚本使用指南
   - CI/CD 流程说明
   - 项目特定的调试技巧

4. **项目架构和模式**
   - 项目架构说明
   - 常用设计模式
   - 项目目录结构规范

### 示例

```
项目级 skill 示例：
.kwaipilot/skills/
├── code-review-checklist/    # 代码审查检查清单
│   └── SKILL.md
├── deployment-workflow/       # 部署流程
│   └── SKILL.md
└── testing-guidelines/        # 测试规范
    └── SKILL.md
```

## 个人级 Skill (Personal)

### 定义

个人级 skill 是存储在用户主目录下的 skill，在所有项目中都可用，通常用于个人通用的技能和工作习惯。

### 存储位置

个人级 skill 存储在用户主目录下的以下位置之一：

```
~/.kwaipilot/skills/
~/.opencode/skills/
~/.claude/skills/
```

### 特点

**优点**：
- ✅ 在所有项目中自动可用
- ✅ 无需在每个项目中重复创建
- ✅ 适合跨项目通用的技能
- ✅ 统一管理个人技能库

**缺点**：
- ❌ 团队成员无法自动共享
- ❌ 需要手动分享给其他人
- ❌ 不随项目版本控制

### 适用场景

个人级 skill 适合以下场景：

1. **通用开发技能**
   - Git 工作流程
   - 代码重构技巧
   - 调试方法论

2. **个人工作习惯**
   - 个人代码风格
   - 个人快捷命令
   - 个人工具配置

3. **跨项目通用流程**
   - API 设计规范
   - 数据库设计模式
   - 通用架构模式

4. **学习和笔记**
   - 技术学习笔记
   - 常见问题解决方案
   - 最佳实践汇总

### 示例

```
个人级 skill 示例：
~/.kwaipilot/skills/
├── git-workflow/              # Git 工作流程
│   └── SKILL.md
├── api-design/                # API 设计规范
│   └── SKILL.md
└── refactoring-patterns/      # 重构模式
    └── SKILL.md
```

## 插件内置 Skill (Plugin)

除了项目级和个人级，CodeFlicker 还支持插件内置 skill。

### 定义

插件内置 skill 是打包在插件中的 skill，随插件安装而自动可用。

### 特点

- 🔒 只读，不可直接修改
- 🔄 可以复制到个人级或项目级进行定制
- 🌐 所有用户默认可用
- 📦 随插件更新而更新

### 示例

- `skill-manager` - skill 管理工具
- `cf-skill-manager` - CodeFlicker skill 管理工具

## 冲突处理

当多个来源存在同名 skill 时，按以下优先级决定最终生效的版本：

```
Personal > Project > Plugin
个人级   > 项目级   > 插件内置
```

### 示例

如果存在以下 skill：
- `~/.kwaipilot/skills/code-review/` (Personal)
- `.kwaipilot/skills/code-review/` (Project)
- 插件内置的 `code-review` (Plugin)

最终生效的是 Personal 版本。

### 覆盖策略

当你想定制插件内置或项目级 skill 时：

1. 将原 skill 复制到个人级目录
2. 在个人级目录中进行修改
3. 个人级版本会自动覆盖原版本

```bash
# 复制插件内置 skill 到个人级
cp -r {plugin-skill-path}/skill-name ~/.kwaipilot/skills/skill-name

# 复制项目级 skill 到个人级
cp -r .kwaipilot/skills/skill-name ~/.kwaipilot/skills/skill-name
```

## 如何选择 Skill 类型

### 决策流程图

```
这个 skill 是否仅适用于当前项目？
├─ 是 → 项目级 skill
└─ 否 → 这个 skill 是否需要团队共享？
    ├─ 是 → 项目级 skill
    └─ 否 → 个人级 skill
```

### 决策表

| 场景 | 推荐类型 | 理由 |
|------|---------|------|
| 项目特定的代码规范 | 项目级 | 团队需要统一遵守 |
| 项目部署流程 | 项目级 | 流程与项目强相关 |
| 通用的 Git 工作流 | 个人级 | 跨项目通用 |
| 个人代码习惯 | 个人级 | 个人偏好 |
| 团队协作规范 | 项目级 | 需要团队共享 |
| 学习笔记 | 个人级 | 个人使用 |

### 经验法则

**选择项目级的情况**：
- 需要团队成员共同遵守
- 与项目架构、工具链强相关
- 希望通过 Git 版本控制
- 新成员加入后立即可用

**选择个人级的情况**：
- 跨多个项目都能使用
- 个人工作习惯和偏好
- 通用的开发技能
- 不需要强制团队使用

## 迁移和转换

### 从个人级转为项目级

当个人级 skill 需要团队共享时：

```bash
# 1. 复制到项目级目录
cp -r ~/.kwaipilot/skills/skill-name .kwaipilot/skills/skill-name

# 2. 提交到项目 Git
cd .kwaipilot/skills/skill-name
git add .
git commit -m "Add skill-name skill for team use"

# 3. (可选) 删除个人级版本
rm -rf ~/.kwaipilot/skills/skill-name
```

### 从项目级转为个人级

当项目级 skill 想在其他项目也使用时：

```bash
# 复制到个人级目录
cp -r .kwaipilot/skills/skill-name ~/.kwaipilot/skills/skill-name

# 可能需要修改使其更通用
# 去除项目特定的引用和配置
```

## 最佳实践

### 项目级 Skill 最佳实践

1. **随项目文档一起维护**
   - 在项目 README 中说明有哪些 skill
   - 定期审查和更新 skill

2. **代码审查时检查 skill 更新**
   - skill 的修改也应该经过代码审查
   - 确保团队对 skill 变更达成共识

3. **避免过度特定化**
   - 即使是项目级，也要考虑可维护性
   - 不要硬编码太多环境特定的值

### 个人级 Skill 最佳实践

1. **定期备份**
   - 个人级 skill 不在项目 Git 中
   - 建议用 Git 管理个人 skill 目录

2. **保持更新**
   - 定期审查和优化个人 skill
   - 删除过时或不再使用的 skill

3. **考虑分享价值**
   - 如果 skill 对他人有价值，考虑开源分享
   - 可以发布到 GitHub 等平台

## 总结

选择合适的 skill 类型是 skill 管理的第一步：

- **项目级**：团队共享、项目特定、随项目版本控制
- **个人级**：个人使用、跨项目通用、全局可用
- **插件内置**：默认可用、只读、可复制定制

根据 skill 的用途和受众，选择最合适的类型，可以让 skill 管理更加高效和有序。
