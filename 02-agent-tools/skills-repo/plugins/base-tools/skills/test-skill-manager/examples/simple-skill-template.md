# Simple Skill Template

这是一个简单的 skill 模板，适合创建基础的 skill。

## 模板内容

```markdown
---
name: your-skill-name
description: This skill should be used when the user asks to "do something", "perform task", or discusses specific-domain. Provides guidance for specific-purpose.
version: 1.0.0
---

# Your Skill Name

简要说明这个 skill 的用途和目标。

## 核心功能

### 功能 1

功能 1 的说明

**使用场景**：
- 场景 1
- 场景 2

**操作步骤**：

1. 步骤 1
2. 步骤 2
3. 步骤 3

### 功能 2

功能 2 的说明

**使用场景**：
- 场景 1
- 场景 2

**操作步骤**：

1. 步骤 1
2. 步骤 2
3. 步骤 3

## 注意事项

- 注意事项 1
- 注意事项 2

## 相关资源

- 资源链接 1
- 资源链接 2
```

## 使用说明

### 1. 复制模板

```bash
# 项目级 skill
mkdir -p .kwaipilot/skills/your-skill-name
cp examples/simple-skill-template.md .kwaipilot/skills/your-skill-name/SKILL.md

# 个人级 skill
mkdir -p ~/.kwaipilot/skills/your-skill-name
cp examples/simple-skill-template.md ~/.kwaipilot/skills/your-skill-name/SKILL.md
```

### 2. 修改内容

编辑 `SKILL.md` 文件，替换以下内容：

- `your-skill-name` → 你的 skill 名称（kebab-case）
- `description` → 详细的触发场景和用途描述
- 主体内容 → 你的 skill 的具体指导

### 3. 验证格式

确保：
- ✅ YAML frontmatter 格式正确（三个连字符包裹）
- ✅ `name` 和 `description` 字段存在
- ✅ Description 使用第三人称
- ✅ Description 包含具体的触发短语

### 4. 测试 Skill

创建完成后，可以：
1. 查看 skill 列表，确认 skill 已被发现
2. 手动触发：`/your-skill-name`
3. 自动触发：说出 description 中的触发短语

## 何时使用简单模板

简单模板适合：

- ✅ 单一功能的 skill
- ✅ 不需要复杂说明的 skill
- ✅ 快速创建原型
- ✅ 学习和实验

如果你的 skill 需要：
- ❌ 详细的参考文档
- ❌ 多个示例代码
- ❌ 工具脚本

请使用 `complete-skill-template.md`。

## 示例：简单的代码审查 Skill

```markdown
---
name: code-review-checklist
description: This skill should be used when the user asks to "review code", "check code quality", or discusses code review checklist. Provides a systematic checklist for code review.
version: 1.0.0
---

# Code Review Checklist

系统化的代码审查检查清单。

## 功能性检查

### 逻辑正确性

**检查要点**：
- 代码逻辑是否正确
- 边界条件处理
- 错误处理是否完善

**操作步骤**：

1. 阅读代码，理解业务逻辑
2. 检查每个条件分支
3. 验证边界情况处理
4. 确认错误处理合理

### 性能考虑

**检查要点**：
- 是否有明显的性能问题
- 算法复杂度是否合理
- 是否有不必要的资源消耗

**操作步骤**：

1. 识别关键路径
2. 评估算法复杂度
3. 检查资源使用（内存、IO）
4. 提出优化建议

## 代码质量检查

### 可读性

**检查要点**：
- 命名是否清晰
- 注释是否充分
- 代码结构是否清晰

### 可维护性

**检查要点**：
- 代码是否易于修改
- 是否遵循项目规范
- 是否有技术债务

## 注意事项

- 保持建设性的反馈
- 关注代码而不是人
- 优先指出关键问题
```

## 总结

简单模板提供了创建基础 skill 的快速方式：

- **结构简洁**：仅包含 SKILL.md
- **易于上手**：清晰的模板结构
- **快速创建**：几分钟即可完成
- **灵活扩展**：后续可以添加支持文件

使用简单模板开始，根据需要逐步扩展！
