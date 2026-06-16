#!/usr/bin/env python3
"""
Doc Updater - Updates documentation based on code changes AND task context.

Usage:
    python update_docs_from_diff.py [project_path] --mode MODE [--options]

Modes:
    - diff: Analyze git diff only (existing behavior)
    - task: Analyze task context only
    - both: Analyze both diff and task context (combined)
"""

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class ChangeType(Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class CodeChange:
    """Represents a code change."""
    change_type: ChangeType
    file_path: str
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    diff_content: str = ""


@dataclass
class DocUpdate:
    """Represents a documentation update suggestion."""
    doc_file: str
    change_type: ChangeType  # added/modified/deleted
    suggestion: str
    affected_section: Optional[str] = None
    priority: str = "medium"
    reason: str = ""


# Default task context prompt
DEFAULT_TASK_PROMPT = """你是一个技术文档更新助手。根据以下任务信息和代码变更，更新相关文档。

## 任务信息
{task_context}

## 代码变更
{code_changes}

## 文档更新规则

1. **新增功能/模块:**
   - 在相关文档中添加功能概述
   - 更新 README/快速开始（如果需要）
   - 添加 API 文档（如果公开接口）
   - 更新架构文档（如果是架构变更）

2. **修改功能:**
   - 更新功能描述
   - 修改 API 签名说明
   - 更新配置项说明
   - 同步更新示例代码

3. **删除功能:**
   - 在文档中标记为已废弃或删除
   - 添加迁移指南（如需要）
   - 更新依赖说明

4. **未变更但需更新:**
   - 更新状态标记（从"进行中"到"已完成"）
   - 添加新注意事项
   - 更新限制条件

请输出需要更新的文档列表和具体更新内容:

---
{doc_updates}
---"""


class DocUpdater:
    """Updates documentation based on code changes and task context."""

    def __init__(self, project_path: str, api_key: Optional[str] = None,
                 model: str = "claude-sonnet-4-20250514"):
        self.project_path = Path(project_path)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    # Patterns for code analysis
    FUNCTION_PATTERN = re.compile(
        r'^(?:def\s+|async\s+def\s+|function\s+|const\s+|let\s+)([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
        re.MULTILINE
    )
    CLASS_PATTERN = re.compile(
        r'^(?:class\s+|interface\s+)([a-zA-Z_][a-zA-Z0-9_]*)[\s:<{]?',
        re.MULTILINE
    )
    API_PATTERN = re.compile(r'`([a-zA-Z_][a-zA-Z0-9_]*\s*\([^)]*\))`')

    def _call_ai(self, prompt: str) -> str:
        """Call AI API."""
        import anthropic

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=self.api_key)

        response = client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def get_git_diff(self, target_commit: Optional[str] = None) -> str:
        """Get git diff for analysis."""
        try:
            if target_commit:
                result = subprocess.run(
                    ['git', 'diff', target_commit, '--'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    ['git', 'diff', '--staged', '--'],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True
                )
            return result.stdout
        except Exception as e:
            return f"Error getting diff: {e}"

    def parse_diff(self, diff_content: str) -> list[CodeChange]:
        """Parse git diff and extract code changes."""
        changes = []

        file_blocks = diff_content.split('diff --git ')
        for block in file_blocks[1:]:
            path_match = re.search(r'b/([^\n]+)', block)
            if not path_match:
                continue
            file_path = path_match.group(1)

            if block.startswith('new file'):
                change_type = ChangeType.ADDED
            elif block.startswith('deleted file'):
                change_type = ChangeType.DELETED
            elif 'similarity index 100%' in block and 'rename from' in block:
                change_type = ChangeType.RENAMED
            else:
                change_type = ChangeType.MODIFIED

            # Skip non-code files
            ext = Path(file_path).suffix
            if ext not in ['.py', '.ts', '.js', '.go', '.java', '.cpp', '.c', '.h', '.pyi', '.tsx']:
                continue

            func_matches = self.FUNCTION_PATTERN.findall(block)
            function_name = func_matches[0] if func_matches else None

            class_matches = self.CLASS_PATTERN.findall(block)
            class_name = class_matches[0] if class_matches else None

            changes.append(CodeChange(
                change_type=change_type,
                file_path=file_path,
                function_name=function_name,
                class_name=class_name,
                diff_content=block[:1000]
            ))

        return changes

    def find_affected_docs(self, changes: list[CodeChange]) -> list[str]:
        """Find documentation files that might be affected."""
        affected_docs = set()

        for change in changes:
            file_name = Path(change.file_path).stem

            for ext in ['.md', '.txt', '.rst']:
                for doc_path in self.project_path.rglob(f'*{ext}'):
                    str_path = str(doc_path)
                    doc_content = Path(doc_path).read_text()

                    # Skip archive
                    if 'archive' in str_path:
                        continue

                    # Check if doc references this file
                    if (file_name.lower() in str_path.lower() or
                        file_name.lower() in doc_content.lower() or
                        f"`{file_name}`" in doc_content or
                        change.file_path in doc_content or
                        (change.function_name and f"`{change.function_name}`" in doc_content)):
                        affected_docs.add(str_path)

        return list(affected_docs)

    def generate_updates_from_diff(self, changes: list[CodeChange],
                                    affected_docs: list[str]) -> list[DocUpdate]:
        """Generate update suggestions from diff analysis."""
        suggestions = []

        for doc_path in affected_docs:
            doc_content = Path(doc_path).read_text()

            for change in changes:
                update = None

                if change.function_name:
                    if change.change_type == ChangeType.ADDED:
                        if change.function_name not in doc_content:
                            update = DocUpdate(
                                doc_file=doc_path,
                                change_type=ChangeType.ADDED,
                                suggestion=f"Add documentation for new API: `{change.function_name}`",
                                priority="high",
                                reason="New API not documented"
                            )
                    elif change.change_type == ChangeType.DELETED:
                        if f"`{change.function_name}`" in doc_content:
                            update = DocUpdate(
                                doc_file=doc_path,
                                change_type=ChangeType.DELETED,
                                suggestion=f"Remove/update documentation for deleted API: `{change.function_name}`",
                                priority="high",
                                reason="API deleted but still documented"
                            )

                if update:
                    suggestions.append(update)

        return suggestions

    def generate_updates_from_task(self, task_context: str,
                                    changes: list[CodeChange],
                                    affected_docs: list[str]) -> list[DocUpdate]:
        """Generate update suggestions using AI based on task context."""
        diff_summary = "\n".join([
            f"- {c.change_type.value}: {c.file_path}" +
            (f" ({c.function_name})" if c.function_name else "")
            for c in changes
        ]) if changes else "No code changes detected"

        prompt = f"""根据以下任务信息和代码变更，分析需要更新的文档。

## 任务信息
{task_context}

## 代码变更
{diff_summary}

## 可能需要更新的文档
{chr(10).join(f"- {d}" for d in affected_docs)}

请分析并输出需要更新的文档列表，格式如下:

### 需要更新的文档

1. **文档路径**
   - 更新类型: [新增/修改/删除/同步更新]
   - 更新内容: 具体需要做什么
   - 优先级: [高/中/低]
   - 更新理由: 为什么需要更新

2. **下一个文档**
   ...

如果无需更新，请输出: "无需更新文档"
"""

        try:
            response = self._call_ai(prompt)
            return self._parse_ai_response(response, task_context)
        except Exception as e:
            return [DocUpdate(
                doc_file="ERROR",
                change_type=ChangeType.MODIFIED,
                suggestion=f"Error calling AI: {e}",
                priority="low"
            )]

    def _parse_ai_response(self, response: str, task_context: str) -> list[DocUpdate]:
        """Parse AI response into DocUpdate objects."""
        updates = []

        if "无需更新" in response or "no changes needed" in response.lower():
            return updates

        # Simple parsing - extract document updates from response
        # The AI will provide detailed suggestions in text format
        lines = response.split('\n')

        current_doc = None
        for line in lines:
            if line.startswith('**') and '.md' in line:
                doc_path = line.strip('* ').strip()
                current_doc = doc_path
            elif current_doc and ('更新类型' in line or '更新内容' in line or '优先级' in line):
                if '更新内容' in line:
                    content = line.split(':')[-1].strip()
                    updates.append(DocUpdate(
                        doc_file=current_doc,
                        change_type=ChangeType.MODIFIED,
                        suggestion=content,
                        priority="medium",
                        reason="AI-generated from task context"
                    ))

        # Fallback: if no structured parsing, create one update with full response
        if not updates and len(response) > 50:
            updates.append(DocUpdate(
                doc_file="task-context-updates",
                change_type=ChangeType.MODIFIED,
                suggestion=response[:1000],
                priority="medium",
                reason="AI analysis of task context"
            ))

        return updates

    def update_from_diff(self, target_commit: Optional[str] = None) -> list[DocUpdate]:
        """Update docs from git diff only."""
        diff_content = self.get_git_diff(target_commit)
        if not diff_content.strip():
            print("No changes detected in git diff.")
            return []

        changes = self.parse_diff(diff_content)
        affected_docs = self.find_affected_docs(changes)
        suggestions = self.generate_updates_from_diff(changes, affected_docs)

        return suggestions

    def update_from_task(self, task_context: str) -> list[DocUpdate]:
        """Update docs from task context only."""
        # Get any staged changes for context
        diff_content = self.get_git_diff()
        changes = self.parse_diff(diff_content) if diff_content else []
        affected_docs = self.find_affected_docs(changes)

        suggestions = self.generate_updates_from_task(task_context, changes, affected_docs)
        return suggestions

    def update_from_both(self, task_context: str, target_commit: Optional[str] = None) -> list[DocUpdate]:
        """Update docs from both task context and git diff."""
        # Get diff
        diff_content = self.get_git_diff(target_commit)
        changes = self.parse_diff(diff_content) if diff_content else []

        # Get affected docs from diff
        affected_docs = self.find_affected_docs(changes)

        # Also find docs that might need updating from task context
        task_docs = self._find_docs_from_task_context(task_context)
        affected_docs.extend(task_docs)
        affected_docs = list(set(affected_docs))

        # Generate combined updates
        suggestions = self.generate_updates_from_task(task_context, changes, affected_docs)

        # Also add diff-based updates for high priority items
        diff_suggestions = self.generate_updates_from_diff(changes, affected_docs)
        for ds in diff_suggestions:
            if ds.priority == "high" and ds not in suggestions:
                suggestions.append(ds)

        return suggestions

    def _find_docs_from_task_context(self, task_context: str) -> list[str]:
        """Find docs that might be relevant to the task context."""
        docs = []
        task_lower = task_context.lower()

        keywords = {
            'readme': ['readme', '快速开始', 'quick start'],
            'api': ['api', '接口', 'endpoint'],
            'architecture': ['架构', '架构设计', 'architecture'],
            'guide': ['指南', 'guide', '使用说明'],
            'changelog': ['changelog', '更新日志', '变更'],
        }

        for keyword, patterns in keywords.items():
            if any(p in task_lower for p in patterns):
                for ext in ['.md', '.txt']:
                    for doc_path in self.project_path.rglob(f'*{ext}'):
                        if keyword in str(doc_path).lower():
                            docs.append(str(doc_path))

        # Also check docs/ directory
        for ext in ['.md', '.txt']:
            for doc_path in (self.project_path / 'docs').rglob(f'*{ext}'):
                docs.append(str(doc_path))

        return docs


def format_updates(updates: list[DocUpdate]) -> str:
    """Format updates for display."""
    if not updates:
        return "No documentation updates needed."

    output = []
    output.append("=" * 60)
    output.append("Documentation Update Suggestions")
    output.append(f"Found {len(updates)} suggestion(s)")
    output.append("=" * 60)

    for priority in ["high", "medium", "low"]:
        priority_updates = [u for u in updates if u.priority == priority]
        if not priority_updates:
            continue

        output.append(f"\n### {priority.upper()} Priority ({len(priority_updates)})\n")

        for u in priority_updates:
            output.append(f"File: {u.doc_file}")
            output.append(f"Type: {u.change_type.value}")
            output.append(f"Suggestion: {u.suggestion}")
            if u.reason:
                output.append(f"Reason: {u.reason}")
            output.append("-" * 40)

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Update documentation from code changes and task context")
    parser.add_argument("project_path", nargs="?", default=".",
                        help="Path to project")
    parser.add_argument("--mode", choices=["diff", "task", "both"],
                        default="both", help="Update mode")
    parser.add_argument("--task", "-t",
                        help="Task context (what was accomplished)")
    parser.add_argument("--task-file", "-T",
                        help="File containing task context")
    parser.add_argument("--commit", "-c",
                        help="Compare against commit (for diff mode)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-apply updates (simple pattern-based only)")

    args = parser.parse_args()

    updater = DocUpdater(args.project_path)

    # Get task context
    task_context = ""
    if args.task:
        task_context = args.task
    elif args.task_file:
        task_context = Path(args.task_file).read_text()

    # Run update based on mode
    if args.mode == "diff":
        updates = updater.update_from_diff(args.commit)
    elif args.mode == "task":
        if not task_context:
            print("Error: --task or --task-file required for task mode")
            sys.exit(1)
        updates = updater.update_from_task(task_context)
    else:  # both
        updates = updater.update_from_both(task_context, args.commit)

    if args.json:
        import json
        print(json.dumps([
            {
                "file": u.doc_file,
                "type": u.change_type.value,
                "suggestion": u.suggestion,
                "priority": u.priority,
                "reason": u.reason
            }
            for u in updates
        ], indent=2))
    else:
        print(format_updates(updates))

    # Auto-apply if requested (only simple pattern-based updates)
    if args.auto and updates:
        print("\nAuto-apply not yet implemented. Please apply updates manually.")
        print("This feature is coming soon.")


if __name__ == "__main__":
    main()
