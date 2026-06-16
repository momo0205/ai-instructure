---
name: tech-doc-organizer
description: |
  Scans, analyzes, and optimizes project technical documentation.
  Detects documentation-code inconsistencies, finds merge/split opportunities, applies lint rules,
  summarizes long documents using AI, archives old content, and updates docs based on code changes
  AND task context (what was accomplished).
  When user says "整理文档" without specific action, presents options menu for user to choose:
  1. Scan (check issues), 2. Summarize (AI condense), 3. Archive (old docs), 4. Update (from diff+task), 5. Reorganize.
  Use when users want to:
  - "整理文档", "优化文档", "检查文档", "更新文档"
  - "精简文档", "精简过长文档"
  - "归档文档", "旧文档归档"
  - "根据代码变更更新文档", "根据任务更新文档", "检查 diff 更新文档"
  - Pre-commit hooks for automatic documentation checks
---
# tech-doc-organizer

Technical documentation scanner and optimizer with summarization, archiving, and diff-based updates.

## Quick Start

### Core Commands
```bash
# Scan and report issues
python3 scripts/scan_docs.py {project_path}

# Find merge/split candidates
python3 scripts/organize_docs.py . --action cleanup

# Summarize long documents
python3 scripts/summarize_docs.py . --file docs/long.md --output docs/long-summary.md

# Archive old documents
python3 scripts/archive_docs.py . --days 365 --list

# Update docs from git diff
python3 scripts/update_docs_from_diff.py . --commit HEAD~1
```

---

## Workflows

### Workflow 1: Full Documentation Audit

```
python3 scripts/scan_docs.py {project_path}
```

Reports:
- **Consistency Issues**: APIs, functions, configs not found in code
- **Organization Issues**: Long docs (>500 lines), similar docs (>70% overlap)
- **Lint Issues**: Dead links, duplicates, outdated content, long lines

### Workflow 2: Document Summarization (AI-powered)

For long documents that need streamlining using AI:

```bash
# Find documents that need summarization (>100 non-empty lines)
python3 scripts/summarize_docs.py . --action scan

# Preview summary (dry run, no changes)
python3 scripts/summarize_docs.py . --action summarize --file docs/guide.md --dry-run

# Summarize a specific file
python3 scripts/summarize_docs.py . --action summarize --file docs/guide.md --output docs/guide-summary.md

# Batch summarize multiple files
python3 scripts/summarize_docs.py . --action batch --files docs/a.md docs/b.md --output summarized/

# Summarize but preserve specific sections
python3 scripts/summarize_docs.py . --action summarize --file docs/guide.md --preserve "Architecture" "API Reference"
```

**AI Summarization Rules:**
- **Preserves:** Core descriptions, key API signatures, config explanations, architecture/flow diagrams (mermaid/ASCII), critical code snippets (<10 lines)
- **Removes:** Large code blocks (>10 lines → "see source"), detailed step-by-step, repetitive explanations, obvious statements, outdated implementation details
- **Output:** Each section ≤100 words, concise language

**Default AI Prompt:**
```python
DEFAULT_SUMMARIZE_PROMPT = """你是一个技术文档精简助手...

1. 保留: 核心功能描述, 关键 API 签名, 架构图/流程图, 关键代码片段(<10行)
2. 删除: 大段代码示例(>10行), 详细步骤, 重复解释
3. 输出: 保留标题层级, 每章节<100字
"""
```

### Workflow 3: Document Archiving

For old or stale documentation:

```bash
# List documents to archive (>365 days or stale patterns)
python3 scripts/archive_docs.py . --list

# Archive all old documents
python3 scripts/archive_docs.py . --auto

# Custom archive threshold
python3 scripts/archive_docs.py . --days 180 --auto

# Restore an archived document
python3 scripts/archive_docs.py . --restore docs/archive/2024-01/old-guide.md
```

Archive behavior:
- Creates `docs/archive/YYYY-MM/` structure
- Creates redirect file at original location
- Updates `docs/archive/INDEX.md`

### Workflow 4: Update Docs from Code Changes & Task Context

After completing a task, update docs based on **code changes** AND **task context**:

```bash
# Mode 1: Analyze git diff only
python3 scripts/update_docs_from_diff.py . --mode diff --commit staged

# Mode 2: Analyze task context only (no git changes needed)
python3 scripts/update_docs_from_diff.py . --mode task --task "完成了用户认证功能，包括登录、注册、登出"

# Mode 3: Analyze BOTH task context AND git diff (recommended)
python3 scripts/update_docs_from_diff.py . --mode both --task "完成了用户认证功能"
python3 scripts/update_docs_from_diff.py . --mode both --task-file task-context.txt

# Compare against specific commit
python3 scripts/update_docs_from_diff.py . --mode both --task "完成了..." --commit HEAD~1
```

**Task Context Examples:**
```bash
# Simple task description
--task "完成了订单模块的重构"

# Detailed task context
--task "本次完成了以下任务:
- 新增用户注册功能 (registerUser API)
- 新增短信验证码功能
- 修改了用户登录逻辑
- 更新了数据库表结构"

# From file
--task-file /path/to/task-summary.txt
```

**What it detects:**
- **From diff:** New APIs, deleted APIs, modified APIs, renamed files
- **From task context:** Which docs to update, status changes, new sections to add

**AI Analysis (--mode both):**
- Combines code changes + task goals
- Identifies docs that need updates even without direct code references
- Suggests updates to README, architecture docs, guides, etc.

---

## Scanner Output Format

### TEXT Output (Default)
```
============================================================
Documentation Scan Report
Found 8 issue(s)
============================================================

### WARNING (3)
---
[api_signature_mismatch]
File: docs/api.md
Line: 45
...
```

### JSON Output (Programmatic)
```json
[
  {
    "type": "api_signature_mismatch",
    "severity": "warning",
    "file": "docs/api.md",
    "title": "API 'createUser' may not exist",
    "line": 45
  }
]
```

---

## Check Patterns

### APIs in Documentation
Matches: `` `function_name(args)` ``
Verified against Python, TypeScript, Go, Java code.

### Config Constants
Matches: `` `CONFIG_NAME` `` (uppercase)

### File References
Matches: `` `path/to/file.py` `` → checks existence

---

## Common Tasks

### Task 1: Full Documentation Audit
```bash
python3 scripts/scan_docs.py {project_path}
```

### Task 2: Pre-commit Check
Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: doc-consistency
      name: Check documentation consistency
      entry: python3 scripts/scan_docs.py . --output JSON
      language: system
      pass_filenames: false
      always_run: true
```

### Task 3: Summarize Long Document (AI)
```bash
# Find documents that need summarization
python3 scripts/summarize_docs.py . --action scan

# Summarize with AI (preview first)
python3 scripts/summarize_docs.py . --action summarize --file docs/long.md --dry-run

# Summarize and save to new file
python3 scripts/summarize_docs.py . --action summarize --file docs/long.md --output docs/long-summary.md

# Summarize multiple files
python3 scripts/summarize_docs.py . --action batch --files docs/a.md docs/b.md

# Preserve specific sections
python3 scripts/summarize_docs.py . --action summarize --file docs/long.md --preserve "Architecture" "API"
```

### Task 4: Archive Old Documents
```bash
# List what will be archived
python3 scripts/archive_docs.py . --days 365 --list

# Archive with confirmation
python3 scripts/archive_docs.py . --days 365

# Auto-archive
python3 scripts/archive_docs.py . --days 365 --auto
```

### Task 5: Update Docs After Task
```bash
# After making changes and before commit (diff only)
python3 scripts/update_docs_from_diff.py . --mode diff --commit staged

# After commit, check what changed (diff only)
python3 scripts/update_docs_from_diff.py . --mode diff --commit HEAD~1

# With task context (combines code changes + task goals)
python3 scripts/update_docs_from_diff.py . --mode both --task "完成了用户认证模块"

# Detailed task context
python3 scripts/update_docs_from_diff.py . --mode both --task "
完成的任务:
- 新增用户注册 API (POST /api/users)
- 新增短信验证码发送
- 修改用户登录逻辑支持验证码
- 更新数据库用户表添加 phone 字段
"

# From task file
python3 scripts/update_docs_from_diff.py . --mode both --task-file completed-tasks.txt
```

### Task 6: Document Reorganization
```bash
# Find merge candidates
python3 scripts/organize_docs.py . --action cleanup

# Reorganize into docs/
python3 scripts/organize_docs.py . --action reorganize --target docs

# Merge similar docs
python3 scripts/organize_docs.py . --action merge --files old.md similar.md --output consolidated

# Split long document
python3 scripts/organize_docs.py . --action split --files long.md
```

---

## Lint Rules

See [lint-rules.md](lint-rules.md):

- **Consistency**: API/function/config mismatches, dead links
- **Organization**: Long documents, overlapping content
- **Quality**: Duplicates, outdated markers, line length

---

## Trigger Keywords

- 整理文档、优化文档、检查文档、**更新文档**
- 精简文档、精简过长文档
- 归档文档、旧文档归档
- 文档和代码不一致
- 根据代码变更更新文档、检查 diff 更新文档

---

## Default Workflow

When user says "整理文档" without specific action:

1. Present options menu:
   ```
   请选择文档操作:
   1. 扫描文档 - 检查文档问题（不一致、lint、组织问题）
   2. 精简文档 - 精简过长文档，保留核心信息
   3. 归档文档 - 归档旧文档
   4. 更新文档 - 根据代码变更和任务上下文更新文档
   5. 重组文档 - 合并/拆分/重组织目录结构
   ```

2. If user chooses "更新文档" (option 4):
   - Ask for task context: "请描述本次完成的任务或变更"
   - User can provide: task description, completed items, or just say "根据代码变更"
   - Run in `both` mode (combines diff + task context)

3. 根据用户选择执行对应脚本

---

## Best Practices

1. **Before major releases**: Run full audit
2. **After completing tasks**: Run diff-based update
3. **Quarterly**: Archive old docs, summarize long docs
4. **Pre-commit**: Use consistency check
5. **Keep docs modular**: Split by concern, merge related
