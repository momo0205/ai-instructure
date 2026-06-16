# Complete Skill Template

这是一个完整的 skill 模板，包含支持文件、示例和脚本，适合创建复杂的 skill。

## 目录结构

```
your-skill-name/
├── SKILL.md              # 主文件
├── references/           # 参考文档
│   ├── guide.md
│   └── api-docs.md
├── examples/             # 示例
│   ├── example1.py
│   └── example2.js
└── scripts/              # 工具脚本
    ├── setup.sh
    └── validate.sh
```

## SKILL.md 模板

```markdown
---
name: your-skill-name
description: This skill should be used when the user asks to "do something", "perform task", or discusses specific-domain. Provides comprehensive guidance for specific-purpose.
version: 1.0.0
---

# Your Skill Name

详细说明这个 skill 的用途、目标和价值。

## 概述

简要介绍 skill 的功能和适用场景。

## 核心功能

### 功能 1

功能 1 的概述和使用场景。

详细步骤见 `references/feature1-guide.md`。

### 功能 2

功能 2 的概述和使用场景。

详细步骤见 `references/feature2-guide.md`。

## 快速开始

### 前置条件

- 条件 1
- 条件 2

### 基本用法

1. 步骤 1
2. 步骤 2
3. 步骤 3

### 示例

参见 `examples/` 目录：
- `example1.py` - 基础示例
- `example2.js` - 高级示例

## 高级功能

更复杂的功能和用法。

详细信息见 `references/advanced-guide.md`。

## 支持文件

### Reference Files
详细信息请查阅：
- **`references/feature1-guide.md`** - 功能 1 详细指南
- **`references/feature2-guide.md`** - 功能 2 详细指南
- **`references/advanced-guide.md`** - 高级用法
- **`references/api-docs.md`** - API 参考文档

### Examples
示例代码位于 `examples/`：
- **`examples/example1.py`** - 基础示例
- **`examples/example2.js`** - 高级示例

### Scripts
工具脚本位于 `scripts/`：
- **`scripts/setup.sh`** - 环境设置脚本
- **`scripts/validate.sh`** - 验证脚本

## 注意事项

- 重要注意事项 1
- 重要注意事项 2

## 故障排查

常见问题和解决方案。

详细故障排查见 `references/troubleshooting.md`。

## 相关资源

- 资源链接 1
- 资源链接 2
```

## references/ 文件模板

### feature1-guide.md

```markdown
# 功能 1 详细指南

## 概述

功能 1 的详细说明。

## 详细步骤

### 步骤 1：准备工作

详细说明...

### 步骤 2：执行操作

详细说明...

### 步骤 3：验证结果

详细说明...

## 高级选项

- 选项 1
- 选项 2

## 最佳实践

- 实践 1
- 实践 2
```

### api-docs.md

```markdown
# API 参考文档

## 接口列表

### API 1

**用途**：说明

**参数**：
- `param1`: 参数说明
- `param2`: 参数说明

**返回值**：返回值说明

**示例**：
\`\`\`
示例代码
\`\`\`

### API 2

...
```

## examples/ 文件模板

### example1.py

```python
"""
基础示例：展示如何使用 skill

这个示例演示了最基本的用法。
"""

def main():
    # 步骤 1
    print("Step 1")
    
    # 步骤 2
    print("Step 2")
    
    # 步骤 3
    print("Step 3")

if __name__ == "__main__":
    main()
```

### example2.js

```javascript
/**
 * 高级示例：展示高级功能
 * 
 * 这个示例演示了更复杂的用法。
 */

async function main() {
  // 步骤 1
  console.log('Step 1');
  
  // 步骤 2
  console.log('Step 2');
  
  // 步骤 3
  console.log('Step 3');
}

main().catch(console.error);
```

## scripts/ 文件模板

### setup.sh

```bash
#!/bin/bash

# 环境设置脚本
# 用途：设置使用 skill 所需的环境

set -e

echo "Setting up environment..."

# 检查依赖
if ! command -v dependency &> /dev/null; then
    echo "Error: dependency not found"
    exit 1
fi

# 安装依赖
echo "Installing dependencies..."

# 配置环境
echo "Configuring environment..."

echo "Setup complete!"
```

### validate.sh

```bash
#!/bin/bash

# 验证脚本
# 用途：验证 skill 是否正确配置

set -e

echo "Validating skill setup..."

# 检查文件
if [ ! -f "SKILL.md" ]; then
    echo "Error: SKILL.md not found"
    exit 1
fi

# 检查格式
if ! grep -q "^---$" SKILL.md; then
    echo "Error: SKILL.md missing YAML frontmatter"
    exit 1
fi

echo "Validation passed!"
```

## 创建步骤

### 1. 创建目录结构

```bash
# 项目级
mkdir -p .kwaipilot/skills/your-skill-name/{references,examples,scripts}

# 个人级
mkdir -p ~/.kwaipilot/skills/your-skill-name/{references,examples,scripts}
```

### 2. 创建主文件

```bash
# 复制模板
cp examples/complete-skill-template.md .kwaipilot/skills/your-skill-name/SKILL.md

# 编辑内容
# 修改 name、description 和主体内容
```

### 3. 创建支持文件

```bash
# 创建参考文档
touch .kwaipilot/skills/your-skill-name/references/feature1-guide.md
touch .kwaipilot/skills/your-skill-name/references/api-docs.md

# 创建示例
touch .kwaipilot/skills/your-skill-name/examples/example1.py
touch .kwaipilot/skills/your-skill-name/examples/example2.js

# 创建脚本
touch .kwaipilot/skills/your-skill-name/scripts/setup.sh
touch .kwaipilot/skills/your-skill-name/scripts/validate.sh

# 添加执行权限
chmod +x .kwaipilot/skills/your-skill-name/scripts/*.sh
```

### 4. 填充内容

按照模板填充每个文件的内容。

### 5. 验证

```bash
# 使用验证脚本
cd .kwaipilot/skills/your-skill-name
./scripts/validate.sh
```

## 何时使用完整模板

完整模板适合：

- ✅ 功能复杂的 skill
- ✅ 需要详细说明的 skill
- ✅ 包含多个示例的 skill
- ✅ 需要工具脚本的 skill
- ✅ 团队共享的重要 skill

## 渐进式扩展

你可以：

1. 从简单模板开始
2. 根据需要添加 references/
3. 添加 examples/ 提供示例
4. 添加 scripts/ 自动化操作

不需要一开始就创建完整结构。

## 示例：完整的 API 设计 Skill

```
api-design/
├── SKILL.md                          # 概述和快速开始
├── references/
│   ├── rest-api-guide.md             # REST API 设计指南
│   ├── graphql-guide.md              # GraphQL 设计指南
│   ├── authentication.md             # 认证和授权
│   ├── versioning.md                 # API 版本管理
│   └── best-practices.md             # 最佳实践
├── examples/
│   ├── rest-api-example/
│   │   ├── user-api.yaml             # OpenAPI 规范
│   │   └── README.md
│   └── graphql-example/
│       ├── schema.graphql
│       └── README.md
└── scripts/
    ├── validate-openapi.sh           # 验证 OpenAPI 规范
    └── generate-docs.sh              # 生成 API 文档
```

## 最佳实践

### Progressive Disclosure

- **SKILL.md**：核心指导（1500-2000字）
- **references/**：详细文档（按需加载）
- **examples/**：可运行示例
- **scripts/**：自动化工具

### 文件组织

1. **清晰的分类**
   - 按功能组织 references/
   - 按场景组织 examples/
   - 按用途命名 scripts/

2. **自描述的命名**
   - 文件名应该清晰说明内容
   - 避免模糊的名称

3. **合理的粒度**
   - 每个文件专注一个主题
   - 避免单个文件过大

### 维护

1. **保持更新**
   - 定期审查文档
   - 更新过时的示例
   - 删除不再使用的文件

2. **版本管理**
   - 使用 Git 管理变更
   - 重要更新打标签
   - 维护 CHANGELOG

3. **文档质量**
   - 确保示例可运行
   - 保持文档一致性
   - 及时修复错误

## 总结

完整模板提供了创建复杂 skill 的完整框架：

- **结构完整**：包含所有类型的支持文件
- **Progressive Disclosure**：核心 + 详细的分层结构
- **示例丰富**：可运行的代码示例
- **工具完善**：自动化脚本支持

使用完整模板可以创建高质量、易维护的 skill！
