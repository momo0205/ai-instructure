# Git 操作详细指南

## 概述

本文档详细说明如何对 CodeFlicker skill 进行 Git 版本管理，包括初始化、提交、推送和分享。

## 为什么需要 Git 管理

对 skill 进行 Git 管理的好处：

1. **版本控制**
   - 记录 skill 的演进历史
   - 可以回滚到任何历史版本
   - 追踪谁做了什么修改

2. **团队协作**
   - 团队成员可以共同维护
   - 通过 Pull Request 进行代码审查
   - 避免冲突和覆盖

3. **备份和分享**
   - 防止本地文件丢失
   - 方便分享给其他人
   - 可以发布到开源社区

4. **CI/CD 集成**
   - 自动验证 skill 格式
   - 自动发布和部署
   - 持续改进质量

## Git 初始化

### 单个 Skill 的 Git 初始化

#### 手动操作

```bash
# 1. 进入 skill 目录
cd .kwaipilot/skills/skill-name

# 2. 初始化 Git 仓库
git init

# 3. 添加所有文件
git add .

# 4. 创建初始提交
git commit -m "Initial commit: skill-name skill"
```

#### 使用脚本

```bash
# 使用提供的脚本
cd .kwaipilot/skills/skill-name
../../cf-skill-manager/scripts/init-git.sh
```

### 整个 Skills 目录的 Git 初始化

如果你想对整个 skills 目录进行版本控制：

```bash
# 1. 进入 skills 目录
cd .kwaipilot/skills

# 2. 初始化 Git 仓库
git init

# 3. 创建 .gitignore（如果需要）
cat > .gitignore << 'EOF'
# 临时文件
*.tmp
*.log

# 操作系统文件
.DS_Store
Thumbs.db
EOF

# 4. 添加所有 skill
git add .

# 5. 创建初始提交
git commit -m "Initial commit: all skills"
```

### 项目级 vs 个人级的 Git 策略

#### 项目级 Skill

**推荐策略**：随项目一起 Git 管理

```bash
# 项目级 skill 应该在项目根目录初始化
cd {project-root}
git add .kwaipilot/skills/
git commit -m "Add project skills"
```

**优点**：
- ✅ 与项目代码一起版本控制
- ✅ 团队成员自动同步
- ✅ 分支和合并管理统一

#### 个人级 Skill

**推荐策略**：单独 Git 仓库管理

```bash
# 个人级 skill 应该独立管理
cd ~/.kwaipilot/skills
git init
git add .
git commit -m "Initial commit: personal skills"

# 添加 remote（如 GitHub）
git remote add origin git@github.com:username/my-skills.git
git push -u origin main
```

**优点**：
- ✅ 跨项目复用
- ✅ 独立版本控制
- ✅ 方便备份和分享

## Git Commit

### 提交前的准备

1. **查看修改内容**
   ```bash
   # 查看状态
   git status
   
   # 查看具体修改
   git diff
   ```

2. **检查文件**
   ```bash
   # 确认要提交的文件
   git status --short
   ```

### 编写 Commit 消息

#### 基本格式

```
<type>: <subject>

<body>

<footer>
```

#### Type 类型

- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档变更
- `style`: 格式调整（不影响功能）
- `refactor`: 重构（不是新功能也不是 bug 修复）
- `test`: 添加测试
- `chore`: 构建或工具变更

#### 示例

**简单提交**：
```bash
git commit -m "docs: update code-review checklist"
```

**详细提交**：
```bash
git commit -m "feat: add API design guidelines

- Add REST API best practices
- Include authentication patterns
- Add versioning strategies

Closes #123"
```

### 使用 git-commit-helper

如果你安装了 `git-commit-helper` skill：

```bash
# 1. 暂存修改
git add .

# 2. 使用 AI 生成 commit 消息
# 在 CodeFlicker 中触发 git-commit-helper skill
# 或使用命令：/git-commit-helper

# 3. AI 会分析修改并生成规范的 commit 消息
# 4. 确认并提交
```

### 使用脚本

```bash
# 使用提供的提交脚本
cd .kwaipilot/skills/skill-name
../../cf-skill-manager/scripts/commit-skill.sh
```

该脚本会：
1. 显示文件变更
2. 提示输入 commit 消息
3. 执行 commit
4. 询问是否推送

## 设置 Remote

### GitHub 设置

#### 方法 1：通过 GitHub CLI

```bash
# 1. 创建 GitHub 仓库
gh repo create my-skills --public --source=. --remote=origin

# 2. 推送到 GitHub
git push -u origin main
```

#### 方法 2：手动设置

```bash
# 1. 在 GitHub 网站创建仓库
# 访问 https://github.com/new

# 2. 添加 remote
git remote add origin git@github.com:username/my-skills.git

# 3. 推送
git branch -M main
git push -u origin main
```

### GitLab 设置

```bash
# 1. 在 GitLab 创建项目
# 访问 https://gitlab.com/projects/new

# 2. 添加 remote
git remote add origin git@gitlab.com:username/my-skills.git

# 3. 推送
git branch -M main
git push -u origin main
```

### 验证 Remote

```bash
# 查看 remote 配置
git remote -v

# 应该显示：
# origin  git@github.com:username/my-skills.git (fetch)
# origin  git@github.com:username/my-skills.git (push)
```

## Git Push

### 首次推送

```bash
# 推送到 main 分支并设置 upstream
git push -u origin main
```

### 后续推送

```bash
# 简单推送
git push
```

### 强制推送（谨慎使用）

```bash
# 仅在确定需要覆盖远程历史时使用
git push --force
```

**警告**：
- ⚠️ 强制推送会覆盖远程仓库
- ⚠️ 可能导致其他人的工作丢失
- ⚠️ 仅在个人仓库或确认安全时使用

## 分支管理

### 创建功能分支

```bash
# 创建并切换到新分支
git checkout -b feature/add-new-guideline

# 进行修改...

# 提交
git add .
git commit -m "feat: add new guideline"

# 推送分支
git push -u origin feature/add-new-guideline
```

### 合并分支

```bash
# 切换到 main 分支
git checkout main

# 合并功能分支
git merge feature/add-new-guideline

# 推送
git push
```

### 删除分支

```bash
# 删除本地分支
git branch -d feature/add-new-guideline

# 删除远程分支
git push origin --delete feature/add-new-guideline
```

## 团队协作

### Fork 和 Pull Request

#### Fork 项目

1. 在 GitHub/GitLab 上 fork 原仓库
2. Clone fork 的仓库
   ```bash
   git clone git@github.com:your-username/original-repo.git
   cd original-repo
   ```

3. 添加 upstream
   ```bash
   git remote add upstream git@github.com:original-owner/original-repo.git
   ```

#### 创建 Pull Request

1. 创建功能分支
   ```bash
   git checkout -b feature/my-improvement
   ```

2. 进行修改并提交
   ```bash
   git add .
   git commit -m "feat: my improvement"
   git push -u origin feature/my-improvement
   ```

3. 在 GitHub/GitLab 上创建 Pull Request

#### 同步 Upstream

```bash
# 获取 upstream 更新
git fetch upstream

# 合并到本地 main
git checkout main
git merge upstream/main

# 推送到你的 fork
git push origin main
```

### 代码审查

在 Pull Request 中：
1. 描述清楚改动的目的
2. 引用相关的 issue
3. 响应审查者的评论
4. 根据反馈修改代码

## 版本管理

### 语义化版本号

Skill 版本号遵循语义化版本规范（Semantic Versioning）：

```
MAJOR.MINOR.PATCH
主版本.次版本.补丁版本
```

- **MAJOR**：不兼容的 API 修改
- **MINOR**：向下兼容的功能性新增
- **PATCH**：向下兼容的问题修正

### 创建版本标签

```bash
# 创建标签
git tag -a v1.0.0 -m "Release version 1.0.0"

# 推送标签
git push origin v1.0.0

# 推送所有标签
git push origin --tags
```

### 更新 SKILL.md 版本号

```yaml
---
name: skill-name
description: ...
version: 1.0.0  # 更新这里
---
```

```bash
# 提交版本号更新
git add SKILL.md
git commit -m "chore: bump version to 1.0.0"
git tag -a v1.0.0 -m "Release version 1.0.0"
git push && git push --tags
```

## 高级操作

### Cherry-pick

选择性地应用某些提交：

```bash
# 从其他分支挑选特定提交
git cherry-pick <commit-hash>
```

### Rebase

重新应用提交历史：

```bash
# Rebase 到最新的 main
git checkout feature-branch
git rebase main
```

**警告**：
- ⚠️ Rebase 会改写历史
- ⚠️ 不要 rebase 已经推送的公共分支

### Stash

临时保存未提交的修改：

```bash
# 保存当前修改
git stash

# 查看 stash 列表
git stash list

# 恢复最近的 stash
git stash pop

# 恢复特定的 stash
git stash apply stash@{0}
```

## 常见问题和解决方案

### 问题 1：忘记添加文件

```bash
# 添加忘记的文件并修正最后一次提交
git add forgotten-file.md
git commit --amend --no-edit
```

### 问题 2：提交到了错误的分支

```bash
# 1. 撤销最后一次提交，保留修改
git reset --soft HEAD^

# 2. 切换到正确的分支
git checkout correct-branch

# 3. 重新提交
git add .
git commit -m "commit message"
```

### 问题 3：需要撤销 Push

```bash
# 1. 本地撤销提交
git reset --hard HEAD^

# 2. 强制推送（谨慎！）
git push --force
```

### 问题 4：合并冲突

```bash
# 1. 查看冲突文件
git status

# 2. 手动解决冲突（编辑文件）

# 3. 标记为已解决
git add conflicted-file.md

# 4. 完成合并
git commit -m "merge: resolve conflicts"
```

### 问题 5：清理未跟踪的文件

```bash
# 查看将要删除的文件
git clean -n

# 删除未跟踪的文件
git clean -f

# 删除未跟踪的文件和目录
git clean -fd
```

## Git 钩子（Hooks）

### Pre-commit Hook

在提交前自动验证 skill 格式：

```bash
# 创建 .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash

# 验证 SKILL.md 格式
for file in $(git diff --cached --name-only | grep 'SKILL.md$'); do
  if ! grep -q "^---$" "$file"; then
    echo "Error: $file missing YAML frontmatter"
    exit 1
  fi
done

exit 0
EOF

# 添加执行权限
chmod +x .git/hooks/pre-commit
```

### Commit-msg Hook

验证 commit 消息格式：

```bash
# 创建 .git/hooks/commit-msg
cat > .git/hooks/commit-msg << 'EOF'
#!/bin/bash

# 检查 commit 消息格式
if ! grep -qE "^(feat|fix|docs|style|refactor|test|chore):" "$1"; then
  echo "Error: Commit message must start with type: (feat|fix|docs|...)"
  exit 1
fi

exit 0
EOF

# 添加执行权限
chmod +x .git/hooks/commit-msg
```

## 最佳实践

### Commit 最佳实践

1. **小而频繁的提交**
   - 每次提交只做一件事
   - 避免大而复杂的提交

2. **清晰的提交消息**
   - 使用规范的格式
   - 说明"为什么"而不仅是"是什么"

3. **提交前检查**
   - 运行测试（如果有）
   - 验证格式
   - 检查 diff

### Branch 最佳实践

1. **使用描述性的分支名**
   - `feature/add-api-guidelines`
   - `fix/typo-in-readme`
   - `docs/update-git-guide`

2. **保持 main 分支稳定**
   - 不直接在 main 上开发
   - 通过 PR 合并到 main

3. **及时删除合并的分支**
   - 保持分支列表整洁
   - 避免混淆

### 团队协作最佳实践

1. **代码审查**
   - 所有变更通过 PR
   - 至少一个人审查
   - 及时响应评论

2. **保持同步**
   - 定期拉取远程更新
   - 解决冲突要及时

3. **沟通清晰**
   - PR 描述详细
   - Commit 消息清晰
   - Issue 追踪完整

## 工具和脚本

### 提供的脚本

#### init-git.sh
```bash
# 初始化 skill 的 Git 仓库
./scripts/init-git.sh
```

#### commit-skill.sh
```bash
# 提交 skill 的修改
./scripts/commit-skill.sh
```

### 推荐的 Git 工具

1. **GitHub CLI (gh)**
   - 快速创建仓库和 PR
   - 命令行管理 issue

2. **GitKraken / SourceTree**
   - GUI 工具
   - 可视化分支和历史

3. **Git Extensions**
   - Windows 平台的 Git GUI
   - 集成 Windows Explorer

## 总结

掌握 Git 操作对于管理 skill 非常重要：

- **初始化**：为 skill 创建 Git 仓库
- **提交**：规范的 commit 消息和频繁的提交
- **推送**：备份到远程并与团队共享
- **分支**：隔离开发，保持 main 稳定
- **协作**：通过 PR 和代码审查协同工作
- **版本**：语义化版本号和标签管理

合理使用 Git 可以让 skill 管理更加高效和安全。
