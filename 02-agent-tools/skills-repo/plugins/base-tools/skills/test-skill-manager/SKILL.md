---
name: test-skill-manager
description: This skill should be used when the user asks to "create a skill", "update a skill", "delete a skill", "manage skills", "initialize skill git", "commit skill changes", "abstract a skill from conversation", "view local skills", "list available skills", "clone skill from git", "import skill from github", "import skill from gitlab", or discusses CodeFlicker skill management, skill creation workflows, skill maintenance, skill organization, or importing skills from remote git repositories. Provides comprehensive guidance for creating, updating, deleting, git-managing, cloning from remote repositories, and organizing CodeFlicker skills throughout their entire lifecycle.
version: 1.0.0
---

# CodeFlicker Skill Manager

CodeFlicker Skill Manager 是一个专门用于管理 CodeFlicker 技能的 skill。它提供了创建、更新、删除、Git 管理、会话抽象和查看技能目录等完整的 skill 生命周期管理功能。

## 核心功能

### 1. Skill 创建

帮助用户创建新的 skill，支持项目级和个人级两种类型。

**触发场景**：
- 用户说："创建一个 skill"
- 用户说："我要新建一个技能"
- 用户说:"帮我创建一个 xxx skill"

**创建流程**：

1. **询问 Skill 类型**
   - 首先询问用户："你想创建项目级 skill 还是个人级 skill？"
   - 项目级 skill：存储在当前项目的 `.kwaipilot/skills/` 目录
   - 个人级 skill：存储在用户主目录的 `~/.kwaipilot/skills/` 目录
   - 详细区别见 `references/skill-types.md`

2. **收集必要信息**
   - Skill 名称（必填）：使用 kebab-case 格式，如 `code-review`
   - Skill 描述（必填）：清晰说明 skill 的用途和触发场景
   - Skill 用途和功能点
   - 是否需要支持文件（references/examples/scripts）

2.1. **检查 Skill 名称冲突**
   - ⚠️ **重要**：在创建 skill 之前，必须检查是否已存在同名 skill
   - 使用 **agent 上下文中的 `<available_skills>` 列表**检查同名冲突（无需手动调用接口）
   - 如果发现同名 skill：
     - **禁止创建同名 skill**，即使用户要求同名也不允许
     - 自动在用户提供的名称后添加数字后缀（如 `-2`、`-3`）
     - 检查添加后缀的名称是否仍然冲突，如果冲突则继续递增后缀数字
     - **明确告知用户**："检测到已存在名为 '{original-name}' 的 skill（来源：{source}），已自动将新 skill 名称改为 '{new-name}'"
   - 示例：
     - 用户想创建 `code-review` skill，但已存在同名 skill
     - 自动改名为 `code-review-2`
     - 如果 `code-review-2` 也存在，则改为 `code-review-3`
     - 告知用户："检测到已存在名为 'code-review' 的 skill（来源：Personal），已自动将新 skill 名称改为 'code-review-2'"

3. **创建目录结构**
   
   ⚠️ **禁止使用 brace expansion 语法**：不要使用 `{references,examples,scripts}` 这种写法，因为在某些 shell 环境下会创建一个名为 `{references,examples,scripts}` 的目录，而不是三个独立目录。
   
   **正确做法**：分别创建每个目录
   ```bash
   # 项目级
   mkdir -p .kwaipilot/skills/{skill-name}
   mkdir -p .kwaipilot/skills/{skill-name}/references
   mkdir -p .kwaipilot/skills/{skill-name}/examples
   mkdir -p .kwaipilot/skills/{skill-name}/scripts
   
   # 个人级
   mkdir -p ~/.kwaipilot/skills/{skill-name}
   mkdir -p ~/.kwaipilot/skills/{skill-name}/references
   mkdir -p ~/.kwaipilot/skills/{skill-name}/examples
   mkdir -p ~/.kwaipilot/skills/{skill-name}/scripts
   ```
   
   **错误示例（禁止使用）**：
   ```bash
   # ❌ 错误 - 不要使用 brace expansion
   mkdir -p ~/.kwaipilot/skills/my-skill/{references,examples,scripts}
   ```

4. **生成 SKILL.md 文件**
   - 包含 YAML frontmatter（name、description、version）
   - 使用第三人称描述（"This skill should be used when..."）
   - 包含具体的触发短语
   - 主体内容保持精简（1500-2000字为宜）
   - 使用祈使语气/不定式（动词开头）

5. **验证 Skill 结构**
   - 检查 SKILL.md 文件是否存在
   - 验证 YAML frontmatter 格式
   - 确认必要字段（name、description）存在

6. **验证目录位置**
   - ⚠️ **重要**：创建完成后必须验证 skill 目录位置是否正确
   - 项目级 skill 验证：
     - 检查 skill 目录是否在当前项目的 `.kwaipilot/skills/` 目录下
     - 完整路径应该是：`{project-root}/.kwaipilot/skills/{skill-name}/`
   - 个人级 skill 验证：
     - 检查 skill 目录是否在用户主目录的 `.kwaipilot/skills/` 目录下
     - 完整路径应该是：`~/.kwaipilot/skills/{skill-name}/` 或 `{home}/.kwaipilot/skills/{skill-name}/`
   - 如果目录位置不正确：
     - 提示用户目录位置错误
     - 说明正确的目录位置应该在哪里
     - 询问用户是否需要重新创建或移动目录

7. **提示用户**
   - 告知 skill 创建成功
   - 说明 skill 的位置
   - ⚠️ **重要提示**：告知用户 skill 的更新需要间隔 30秒才能生效，或者重启 VS Code 立即生效
   - 提示是否需要进行 git 初始化

### 2. Skill 更新

帮助用户更新已有的 skill。

**触发场景**：
- 用户说："更新 skill"
- 用户说："修改某个技能"
- 用户说："我要改一下 xxx skill"

**更新流程**：

1. **检查当前目录**
   - 首先检查当前目录是否是一个 skill 目录（是否存在 SKILL.md）
   - 如果是，询问："是否要更新当前 skill？"

2. **选择要更新的 Skill**
   - 如果当前目录不是 skill，列出所有可用的 skill
   - 让用户选择要更新的 skill

3. **了解更新需求**
   - 询问用户想要修改什么：
     - 更新 SKILL.md 内容
     - 修改 description
     - 添加/修改支持文件
     - 添加示例或脚本

3.1. **检查名称更新时的冲突**
   - ⚠️ **重要**：如果用户想要修改 skill 的 name 字段，必须检查新名称是否已被占用
   - 使用 **agent 上下文中的 `<available_skills>` 列表**检查同名冲突（无需手动调用接口）
   - 如果新名称与其他 skill 冲突：
     - **禁止使用冲突的名称**，即使用户要求也不允许
     - 自动在用户提供的名称后添加数字后缀（如 `-2`、`-3`）
     - 检查添加后缀的名称是否仍然冲突，如果冲突则继续递增后缀数字
     - **明确告知用户**："检测到已存在名为 '{original-name}' 的 skill（来源：{source}），已自动将 skill 名称改为 '{new-name}'"
   - 注意：排除当前正在更新的 skill 自身（通过 skill 目录路径判断）

4. **执行更新**
   - 读取现有文件内容
   - 根据用户需求修改
   - 保存更新后的文件

5. **验证更新**
   - 验证 YAML frontmatter 格式
   - 确保必要字段存在

6. **提示后续操作**
   - 告知更新成功
   - ⚠️ **重要提示**：告知用户 skill 的更新需要间隔 30秒才能生效，或者重启 VS Code 立即生效
   - 如果 skill 已经 git 化，提示用户是否执行 git commit
   - 可以使用 `scripts/commit-skill.sh` 脚本

### 3. Skill 删除

帮助用户删除不需要的 skill。

**触发场景**：
- 用户说："删除 skill"
- 用户说："移除某个技能"
- 用户说："不要这个 skill 了"

**删除流程**：

1. **选择要删除的 Skill**
   - 列出所有可用的 skill（个人级和项目级分开显示）
   - 用户选择要删除的 skill

2. **二次确认**
   - ⚠️ **重要**：删除前必须二次确认
   - 提示用户："确定要删除 skill '{skill-name}' 吗？此操作不可撤销。(y/N)"
   - 只有用户明确回复 "y" 或 "yes" 才继续

3. **执行删除**
   ```bash
   # 删除整个 skill 目录
   rm -rf {skill-directory}
   ```

4. **确认删除结果**
   - 告知用户删除成功
   - 说明删除的 skill 名称和位置

### 4. Skill Git 初始化和 Commit

帮助用户对 skill 进行 git 管理。

**触发场景**：
- 用户说："初始化 skill 的 git"
- 用户说："提交 skill 修改"
- 用户说："给 skill 做版本管理"
- Skill 创建或更新后的提示引导

**Git 操作流程**：

#### 4.1 Git 初始化

1. **检查 Git 状态**
   ```bash
   cd {skill-directory}
   git rev-parse --git-dir 2>/dev/null
   ```

2. **执行初始化**（如果不是 git 仓库）
   ```bash
   git init
   git add .
   git commit -m "Initial commit: {skill-name} skill"
   ```

3. **设置 Remote**（可选）
   - 询问用户是否要设置 remote 仓库
   - 引导用户输入 GitHub/GitLab 链接
   ```bash
   git remote add origin {remote-url}
   git push -u origin main
   ```

#### 4.2 Git Commit

1. **检查文件变更**
   ```bash
   cd {skill-directory}
   git status
   git diff
   ```

2. **展示变更内容**
   - 向用户展示有哪些文件被修改
   - 显示具体的变更内容

3. **生成 Commit 消息**
   - 可以使用 `git-commit-helper` skill 生成规范的 commit 消息
   - 或者让用户自己输入 commit 消息

4. **执行 Commit**
   ```bash
   git add .
   git commit -m "{commit-message}"
   ```

5. **推送到远程**（如果有 remote）
   ```bash
   git push
   ```

**便捷脚本**：
- 可以使用 `scripts/init-git.sh` 初始化 git
- 可以使用 `scripts/commit-skill.sh` 快速提交

详细的 git 操作说明见 `references/git-operations.md`

### 5. 基于会话抽象 Skill

帮助用户从当前会话中抽象出一个可复用的 skill。

**触发场景**：
- 用户说："把这个对话抽象成 skill"
- 用户说："根据当前会话创建技能"
- 用户说："这个流程可以做成 skill 吗"

**抽象流程**：

1. **分析当前会话**
   - 检查当前会话是否包含足够的逻辑性操作
   - 识别会话中的关键步骤和模式
   - 判断是否适合抽象为 skill

2. **提取关键信息**
   - 任务的目标和目的
   - 执行步骤和流程
   - 需要的工具和命令
   - 注意事项和最佳实践

3. **询问 Skill 元信息**
   - Skill 名称
   - Skill 描述和触发场景
   - 是项目级还是个人级

4. **生成 Skill 内容**
   - 将会话中的步骤整理成结构化的指导
   - 提炼通用模式，去除特定项目的细节
   - 添加使用示例和场景说明

5. **创建 Skill**
   - 按照"Skill 创建"流程创建 skill
   - 将抽象的内容写入 SKILL.md

6. **验证和优化**
   - 检查 skill 是否足够通用
   - 确认触发场景描述清晰
   - 优化语言和格式

**注意事项**：
- 并非所有会话都适合抽象为 skill
- skill 应该是可复用的，不应包含过多的项目特定信息
- 抽象时要关注通用模式，而不是具体实现

### 6. 查看本地 Skill 目录

帮助用户查看本地有哪些可用的 skill。

**触发场景**：
- 用户说："查看本地 skill"
- 用户说："有哪些可用的技能"
- 用户说："列出所有 skill"

**查看流程**：

1. **扫描 Skill 目录**
   - 扫描项目级目录：`.kwaipilot/skills/`、`.opencode/skills/`、`.claude/skills/`
   - 扫描个人级目录：`~/.kwaipilot/skills/`、`~/.opencode/skills/`、`~/.claude/skills/`
   - 扫描插件内置目录（如果存在）

2. **解析 Skill 元信息**
   - 读取每个 skill 的 SKILL.md
   - 提取 name、description、version、source 等信息

3. **分类展示**
   ```
   ## 个人级 Skill (Personal)
   - skill-name-1 (v1.0.0): 描述...
     路径: ~/.kwaipilot/skills/skill-name-1
   
   - skill-name-2 (v1.2.0): 描述...
     路径: ~/.kwaipilot/skills/skill-name-2
   
   ## 项目级 Skill (Project)
   - project-skill-1 (v1.0.0): 描述...
     路径: .kwaipilot/skills/project-skill-1
   
   ## 插件内置 Skill (Plugin)
   - built-in-skill (v1.0.0): 描述...
     路径: .kwaipilot/internal/skills/built-in-skill
   ```

4. **处理冲突**
   - 如果发现同名 skill，标注冲突
   - 说明优先级：Personal > Project > Plugin

5. **提供操作入口**
   - 询问用户是否要查看某个 skill 的详细内容
   - 提供更新、删除等操作的入口

**Skill 目录信息**：
- 详见 `references/skill-directories.md`
- 默认扫描目录：`.kwaipilot/skills/`、`.opencode/skills/`、`.claude/skills/`
- 用户主目录：`~/.kwaipilot/skills/`、`~/.opencode/skills/`、`~/.claude/skills/`

### 7. 从 Git 仓库克隆 Skill

帮助用户从远程 Git 仓库（如 GitHub、GitLab）克隆现有的 skill 到本地。

**触发场景**：
- 用户说："从 git 克隆一个 skill"
- 用户说："导入 github 上的 skill"
- 用户说："clone 这个 skill 仓库"
- 用户提供了一个 git 链接并说要作为 skill 使用

**克隆流程**：

1. **获取 Git 仓库链接**
   - 询问用户提供 Git 仓库 URL
   - 支持的链接格式：
     - SSH 格式：`git@github.com:username/skill-repo.git`
     - SSH 格式：`git@gitlab.com:username/skill-repo.git`
     - HTTPS 格式：`https://github.com/username/skill-repo.git`
     - HTTPS 格式：`https://gitlab.com/username/skill-repo.git`
     - 企业 Git：`git@git.corp.example.com:team/skill-repo.git`

2. **询问 Skill 类型**
   - 询问用户："你想将此 skill 克隆为项目级还是个人级？"
   - 项目级 skill：克隆到当前项目的 `.kwaipilot/skills/` 目录
   - 个人级 skill：克隆到用户主目录的 `~/.kwaipilot/skills/` 目录

3. **解析仓库名称**
   - 从 Git URL 中提取仓库名称作为默认 skill 目录名
   - 示例：`git@github.com:user/my-awesome-skill.git` → `my-awesome-skill`
   - 询问用户是否要使用其他名称

4. **检查 Skill 名称冲突**
   - ⚠️ **重要**：在克隆之前，必须检查目标目录是否已存在
   - 使用 **agent 上下文中的 `<available_skills>` 列表**检查同名冲突
   - 如果发现同名 skill：
     - **禁止克隆到同名目录**
     - 自动在目录名后添加数字后缀（如 `-2`、`-3`）
     - **明确告知用户**："检测到已存在名为 '{original-name}' 的 skill（来源：{source}），已自动将目录名改为 '{new-name}'"

5. **执行克隆操作**
   ```bash
   # 项目级
   cd {project-root}/.kwaipilot/skills
   git clone {git-url} {skill-name}
   
   # 个人级
   cd ~/.kwaipilot/skills
   git clone {git-url} {skill-name}
   ```

6. **验证克隆结果**
   - 检查目录是否创建成功
   - 检查 SKILL.md 文件是否存在
   - 验证 YAML frontmatter 格式是否正确
   - 如果 SKILL.md 不存在或格式不正确：
     - 警告用户该仓库可能不是有效的 skill 仓库
     - 询问是否要手动创建 SKILL.md 或删除该目录

7. **提示用户**
   - 告知克隆成功
   - 显示 skill 的位置
   - 显示 skill 的基本信息（name、description、version）
   - ⚠️ **重要提示**：告知用户 skill 的更新需要间隔 30秒才能生效，或者重启 VS Code 立即生效

**错误处理**：

1. **Git 克隆失败**
   - 检查网络连接
   - 检查 SSH 密钥或 HTTPS 凭证
   - 检查仓库是否存在或是否有访问权限
   - 提供详细的错误信息

2. **无效的 Skill 仓库**
   - 如果克隆的仓库没有 SKILL.md 文件
   - 询问用户：
     - 是否要手动创建 SKILL.md（按照创建流程）
     - 是否要删除该目录

**使用示例**：

**用户**：帮我克隆这个 skill：git@github.com:example/code-formatter.git

**流程**：
1. 确认链接格式正确
2. 询问：项目级还是个人级？ → 用户选择"个人级"
3. 解析目录名：code-formatter
4. 检查名称冲突
5. 执行：`cd ~/.kwaipilot/skills && git clone git@github.com:example/code-formatter.git code-formatter`
6. 验证 SKILL.md 存在
7. 告知用户克隆成功

## 最佳实践

### Skill 命名规范
- 使用 kebab-case 格式（小写字母和连字符）
- 保持简洁且具有描述性
- 示例：`code-review`、`api-testing`、`git-workflow`

### Description 编写规范
- 使用第三人称："This skill should be used when..."
- 包含具体的触发短语
- 说明适用场景和解决的问题
- 避免模糊的描述

### 内容组织
- SKILL.md 保持精简（1500-2000字）
- 详细内容放在 references/ 目录
- 可执行示例放在 examples/ 目录
- 工具脚本放在 scripts/ 目录

### Progressive Disclosure
- 主文档包含核心指令
- 支持文件包含详细资料
- AI 按需加载详细内容

### 版本管理
- 使用 git 进行版本控制
- 遵循语义化版本号（Semantic Versioning）
- 重要变更记录 CHANGELOG

## 错误处理

### 常见问题

1. **Skill 名称冲突**
   - 系统会自动处理同名冲突
   - 自动在名称后添加数字后缀（如 `-2`、`-3`）
   - 明确告知用户已自动改名及改名原因

2. **YAML 格式错误**
   - 显示具体的错误信息
   - 提供正确的格式示例
   - 引导用户修复

3. **Git 操作失败**
   - 检查 git 是否安装
   - 检查当前目录权限
   - 提供详细的错误信息和解决方案

4. **找不到 Skill**
   - 列出所有可用的 skill
   - 检查拼写是否正确
   - 提示可能的 skill 名称

## 支持文件

### Reference Files
详细信息请查阅：
- **`references/skill-types.md`** - 项目级 vs 个人级 skill 详解
- **`references/skill-directories.md`** - Skill 目录结构和扫描规则
- **`references/git-operations.md`** - Git 操作详细指南

### Examples
示例模板位于 `examples/`：
- **`examples/simple-skill-template.md`** - 简单 skill 模板
- **`examples/complete-skill-template.md`** - 完整 skill 模板（包含支持文件）

### Scripts
工具脚本位于 `scripts/`：
- **`scripts/init-git.sh`** - Git 初始化脚本
- **`scripts/commit-skill.sh`** - Skill 提交脚本
- **`scripts/validate-skill.sh`** - Skill 验证脚本

## 使用示例

### 示例 1：创建项目级 Skill

**用户**：帮我创建一个代码审查的 skill

**流程**：
1. 询问：项目级还是个人级？ → 用户选择"项目级"
2. 收集信息：
   - 名称：code-review
   - 描述：用于系统化代码审查流程
3. 创建目录结构
4. 生成 SKILL.md
5. 提示是否 git 初始化

### 示例 2：更新 Skill 并提交

**用户**：我要更新 code-review skill，然后提交到 git

**流程**：
1. 检查当前目录（如果在 skill 目录）
2. 了解更新需求
3. 执行更新
4. 展示变更内容
5. 生成 commit 消息
6. 执行 git commit 和 push

### 示例 3：从会话抽象 Skill

**用户**：这个部署流程可以抽象成 skill 吗？

**流程**：
1. 分析会话中的部署步骤
2. 判断是否适合抽象
3. 提取关键步骤和模式
4. 询问 skill 元信息
5. 生成 skill 内容
6. 创建 skill

## 注意事项

1. **删除操作必须二次确认**：避免误删除
2. **Git 操作需要用户主动确认**：不自动推送到远程
3. **Skill 类型选择很重要**：
   - 项目级适合团队共享的工作流
   - 个人级适合个人通用的技能
4. **保持 SKILL.md 简洁**：详细内容放在支持文件中
5. **遵循命名规范**：使用 kebab-case，避免特殊字符
6. ⚠️ **Skill 更新生效时间**：Skill 的创建或更新需要间隔 30秒才能被系统扫描到并生效，或者重启 VS Code 立即生效
