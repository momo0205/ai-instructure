---
name: commit-msg
description: 基于 staged diff 生成符合 Conventional Commits 规范的 commit message。当用户说「生成 commit」「写 commit message」「提交代码」「帮我 commit」或需要生成规范的 git 提交信息时，使用此技能。支持智能推断 type 和 scope，输出英文 subject + body。
version: 1.0.1
---

# Commit Message Generator - Conventional Commits

## 功能定位

基于 git staged diff 自动生成符合 **Conventional Commits** 规范的 commit message。

**核心价值**：

- **规范统一**：自动生成符合 Conventional Commits 的 message
- **智能推断**：自动推断 type 和 scope
- **英文输出**：subject + body，清晰说明变更原因和影响
- **全局可用**：不依赖项目结构，任何仓库都可使用

---

## 使用场景

### 何时使用

- 提交代码前需要生成规范的 commit message
- 希望自动推断变更类型和影响范围
- 需要保持团队 commit message 风格一致

### 注意事项

- **只输出 message，不执行 commit**
- **默认只看 staged 变更**（除非用户明确指定文件/路径）
- **staged 为空时**：明确告知并要求用户指定文件/路径或先暂存
- **强制要求**：每次调用必须重新执行 git diff --staged 获取最新状态，不复用对话历史中的数据

---

## 执行流程

**强制要求**：每次调用必须从 Step 1 开始完整执行，不假设任何上下文可用

**关键原则**：

- 不复用对话历史中的 git diff 结果
- 每次收到用户请求时，必须重新执行 `git diff --staged`
- 即使 staged 状态看似不变，也必须重新验证

### Step 1: 检查 Staged 状态

```bash
git diff --staged --name-status
```

- 如果有输出 → 继续 Step 2
- 如果无输出 → 进入异常处理

### Step 2: 收集变更信息

```bash
# 收集完整 diff
git diff --staged

# 收集文件列表
git diff --staged --name-status
```

### Step 3: 推断 Type 和 Scope

#### Type 推断规则

**按文件路径规则**（优先）：

- `docs/`、`*.md`（非 CHANGELOG）→ `docs`
- `test/`、`*.test.*`、`*.spec.*` → `test`
- `.github/`、`Jenkinsfile`、`.gitlab-ci.yml` → `ci`
- `Dockerfile`、`docker-compose.*` → `build`
- `package.json`、`pom.xml`、`build.gradle` → `build`

**按语义分析**（文件规则不匹配时）：

- **新增功能** → `feat`
  - 关键词：`add`, `new`, `create`, `implement`, `support`
- **修复问题** → `fix`
  - 关键词：`fix`, `bug`, `issue`, `error`, `crash`, `resolve`
- **重构代码** → `refactor`
  - 关键词：`refactor`, `restructure`, `reorganize`, `move`, `rename`
- **性能优化** → `perf`
  - 关键词：`optimize`, `performance`, `speed`, `cache`, `lazy`, `memo`
- **纯格式（不改变行为）** → `style`
  - 关键词：`format`, `indent`, `whitespace`, `semicolon`

#### Scope 推断（尽量"可解释"）

**优先级**：

1. **Monorepo 结构**（优先）
   - 若存在 `packages/<name>/...` → scope=`<name>`
   - 若存在 `apps/<name>/...` → scope=`<name>`
   - 若存在 `services/<name>/...` → scope=`<name>`

2. **顶层目录名**
   - 若变更集中在某个顶层目录（如 `src/`, `docs/`, `scripts/`, `components/`）
   - 取该目录名作为 scope

3. **跨多个顶层且难判定**
   - 省略 scope（输出 `type: ...`）

**推断逻辑**：

- 统计所有变更文件的路径前缀
- 找出最常见的顶层目录
- 如果单一目录占比 > 60%，使用该目录作为 scope
- 否则省略 scope

### Step 4: 生成 Commit Message

**格式规范**：

```
<type>(<scope>): <imperative_summary>

<body_line_1>
<body_line_2>
<body_line_3>
```

**Subject 要求**：

- 使用**祈使语气**（imperative mood）
- 首字母小写（除非是专有名词）
- 不超过 72 字符
- scope 尽量推断；推断不了可省略括号

**Body 要求**：

- 1-3 行英文
- 说明 **why/impact**（为什么改、影响是什么）
- **避免罗列文件**（文件列表在 diff 中已有）
- 每行不超过 72 字符

**示例**：

```
feat(site): add virtual card component with intersection observer

Implement VirtualCard component to optimize rendering performance
for large galleries by only rendering visible cards.
```

```
fix(assets): handle edge case in light rays animation

Fix potential null reference when animation is unmounted before
completion, preventing console errors.
```

```
docs: update design system with layout specifications

Add comprehensive layout system documentation including responsive
breakpoints and z-index management guidelines.
```

---

## 异常处理

### 情况 A: Staged 为空

**检测**：

```bash
git diff --staged --name-status
```

**处理**：

1. 明确告知用户：默认查看 staged 变更
2. 提示用户选择：
   - 先使用 `git add <files>` 暂存变更
   - 或指定文件/路径：`--paths <path1> <path2> ...`
3. 等待用户明确指示后再继续

**输出模板**：

```
No staged changes found.

By default, this skill only processes staged changes. Please either:
1. Stage your changes first:
   git add <files>
2. Or specify files/paths explicitly:
   --paths <path1> <path2> ...

Then run the skill again.
```

### 情况 B: 用户指定路径但路径无效

**检测**：

```bash
git diff -- <paths>
```

**处理**：

- 如果命令返回空或错误
- 提示用户检查路径是否正确
- 或建议先暂存变更

---

## 使用示例

### 示例 1: 正常流程（有 staged 变更）

**用户输入**：

```
生成 commit message
```

**执行**：

1. 检查 staged：`git diff --staged --name-status`
2. 收集 diff：`git diff --staged`
3. 推断 type/scope
4. 生成 message

**输出**：

```
feat(site): add virtual card component with intersection observer

Implement VirtualCard component to optimize rendering performance
for large galleries by only rendering visible cards.
```

### 示例 2: Staged 为空

**用户输入**：

```
生成 commit message
```

**执行**：

1. 检查 staged：`git diff --staged --name-status` → 无输出
2. 进入异常处理

**输出**：

```
No staged changes found.

By default, this skill only processes staged changes. Please either:
1. Stage your changes first:
   git add <files>
2. Or specify files/paths explicitly:
   --paths <path1> <path2> ...

Then run the skill again.
```

### 示例 3: 用户指定路径

**用户输入**：

```
生成 commit message --paths packages/site/src/components/VirtualCard.vue
```

**执行**：

1. 检测到 `--paths` 参数
2. 使用指定路径：`git diff -- packages/site/src/components/VirtualCard.vue`
3. 收集 diff 和推断
4. 生成 message

---

## 技术实现

### 命令执行顺序

1. **检查 staged**（必需）

   ```bash
   git diff --staged --name-status
   ```

2. **收集 diff**（必需）
   - 默认：`git diff --staged`
   - 指定路径：`git diff -- <paths>`

3. **收集文件列表**（必需）
   - 默认：`git diff --staged --name-status`
   - 指定路径：`git diff --name-status -- <paths>`

4. **收集历史**（可选，用于风格参考）

   ```bash
   git log -n 5 --pretty=format:"%s" --no-merges
   ```

### 推断算法

**Type 推断**：

1. 先按文件路径规则匹配（文档/测试/CI）
2. 如果规则不匹配，分析 diff 内容关键词
3. 统计关键词出现频率，选择最匹配的 type

**Scope 推断**：

1. 提取所有变更文件的路径
2. 按目录层级统计（优先 monorepo 结构）
3. 找出最常见的顶层目录
4. 如果单一目录占比 > 60%，使用该目录
5. 否则省略 scope

---

## 验证清单

生成 message 前确认：

- [ ] 已检查 staged 状态（或用户指定了路径）
- [ ] 已收集完整的 diff 内容
- [ ] 已收集文件变更列表
- [ ] Type 推断有明确依据（规则或语义）
- [ ] Scope 推断合理（或已省略）
- [ ] Subject 使用祈使语气
- [ ] Body 说明 why/impact，未罗列文件
- [ ] 格式符合 Conventional Commits 规范

---

## 参考

- [Conventional Commits 规范](https://www.conventionalcommits.org/)
- 常见 type：`feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `style`, `build`, `ci`, `revert`
