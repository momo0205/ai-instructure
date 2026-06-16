#!/usr/bin/env python3
"""
Document Summarizer using AI - Condenses documentation to core information.

Usage:
    python summarize_docs.py [project_path] --action ACTION [--options]

Actions:
    - scan: Find documents that need summarization
    - summarize: Condense a single document using AI
    - batch: Condense all documents that need summarization
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Default AI prompt for document summarization
DEFAULT_SUMMARIZE_PROMPT = """你是一个技术文档精简助手。请将以下技术文档精简到最小必要信息，保留核心内容。

## 精简规则

1. **保留:**
   - 核心功能描述（1-2句话）
   - 关键 API/函数签名（只保留最重要的，签名完整）
   - 配置项说明（只保留正在使用的）
   - 架构图、流程图（用 mermaid 或 ASCII 表示的）
   - 关键的代码片段（< 20 行，有注释说明）

2. **删除/压缩:**
   - 大段代码示例（超过 20 行的删除，用"参见源码"代替）
   - 详细的步骤说明（保留最终结果，中间步骤删除）
   - 重复的解释
   - 显而易见的说明
   - 入门级的基础概念解释
   - 过时的实现细节

3. **输出格式:**
   - 保留原有标题层级
   - 每个章节控制在 100 字以内
   - 使用简洁的语言

请直接输出精简后的文档内容，不要添加任何解释。

---文档开始---
{document_content}
---文档结束---

精简后的文档:"""


@dataclass
class SummarizeCandidate:
    """Represents a document that should be summarized."""
    file_path: str
    line_count: int
    reason: str


class DocumentSummarizer:
    """Uses AI to summarize and condense documentation."""

    DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc'}

    # Thresholds for suggesting summarization
    MIN_LINES_FOR_SUMMARIZE = 100
    RECOMMENDED_MAX_LINES = 80

    def __init__(self, project_path: str, api_key: Optional[str] = None,
                 model: str = "claude-sonnet-4-20250514"):
        self.project_path = Path(project_path)
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    def _call_ai(self, prompt: str, content: str) -> str:
        """Call AI API to summarize content."""
        import anthropic

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Set env var or pass --api-key")

        client = anthropic.Anthropic(api_key=self.api_key)

        full_prompt = prompt.format(document_content=content)

        response = client.messages.create(
            model=self.model,
            max_tokens=8192,
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.content[0].text

    def find_candidates(self) -> list[SummarizeCandidate]:
        """Find documents that need summarization."""
        candidates = []

        for ext in self.DOC_EXTENSIONS:
            for file_path in Path(self.project_path).rglob(f'*{ext}'):
                # Skip archive and certain directories
                str_path = str(file_path)
                if any(x in str_path for x in ['node_modules', '__pycache__', '.git',
                                                'archive', '.venv', 'venv']):
                    continue

                try:
                    lines = file_path.read_text().splitlines()
                    line_count = len([l for l in lines if l.strip()])  # Non-empty lines

                    if line_count >= self.MIN_LINES_FOR_SUMMARIZE:
                        candidates.append(SummarizeCandidate(
                            file_path=str_path,
                            line_count=line_count,
                            reason=f"Too long ({line_count} non-empty lines, recommend <{self.RECOMMENDED_MAX_LINES})"
                        ))
                except Exception:
                    pass

        return sorted(candidates, key=lambda x: x.line_count, reverse=True)

    def summarize(self, file_path: str, output_path: Optional[str] = None,
                  custom_prompt: Optional[str] = None,
                  dry_run: bool = False) -> str:
        """Summarize a single document using AI."""
        content = Path(file_path).read_text()
        prompt = custom_prompt or DEFAULT_SUMMARIZE_PROMPT

        print(f"Summarizing: {file_path}")
        print("-" * 40)

        try:
            summarized = self._call_ai(prompt, content)
        except Exception as e:
            print(f"Error calling AI: {e}")
            return ""

        if dry_run:
            # Just show preview (first 500 chars)
            print("Preview (first 500 chars):")
            print(summarized[:500])
            print("...")
            return summarized

        if output_path:
            Path(output_path).write_text(summarized)
            print(f"Saved to: {output_path}")
        else:
            # Overwrite original
            Path(file_path).write_text(summarized)
            print(f"Updated: {file_path}")

        return summarized

    def batch_summarize(self, file_paths: list[str],
                        custom_prompt: Optional[str] = None,
                        output_dir: Optional[str] = None,
                        dry_run: bool = False) -> dict:
        """Summarize multiple documents."""
        results = {}
        prompt = custom_prompt or DEFAULT_SUMMARIZE_PROMPT

        for file_path in file_paths:
            print(f"\n[{len(results)+1}/{len(file_paths)}] Processing: {file_path}")

            try:
                content = Path(file_path).read_text()
                summarized = self._call_ai(prompt, content)

                if output_dir:
                    output_path = Path(output_dir) / Path(file_path).name
                    Path(output_path).write_text(summarized)
                    results[file_path] = str(output_path)
                    print(f"  -> Saved: {output_path}")
                elif not dry_run:
                    Path(file_path).write_text(summarized)
                    results[file_path] = "(overwritten)"
                    print(f"  -> Updated")
                else:
                    results[file_path] = "(dry run, no changes)"
                    print(f"  -> Would update (dry run)")

            except Exception as e:
                results[file_path] = f"Error: {e}"
                print(f"  -> Error: {e}")

        return results

    def summarize_with_preserve(self, file_path: str, preserve_sections: list[str],
                                 output_path: Optional[str] = None) -> str:
        """Summarize document but preserve specific sections."""
        content = Path(file_path).read_text()

        # Build custom prompt with preserve sections
        prompt = f"""{DEFAULT_SUMMARIZE_PROMPT}

## 额外规则 - 必须保留以下章节/内容:
{chr(10).join(f"- {s}" for s in preserve_sections)}

请确保上述章节/内容被完整保留，只精简其他部分。
"""

        return self.summarize(file_path, output_path, custom_prompt=prompt)


def main():
    parser = argparse.ArgumentParser(description="AI-powered document summarizer")
    parser.add_argument("project_path", nargs="?", default=".",
                        help="Path to project")
    parser.add_argument("--action", choices=["scan", "summarize", "batch"],
                        default="scan", help="Action to perform")
    parser.add_argument("--file", "-f", help="File to summarize")
    parser.add_argument("--files", nargs="+", help="Files to batch summarize")
    parser.add_argument("--output", "-o", help="Output file/directory")
    parser.add_argument("--prompt", help="Custom AI prompt file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without saving")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="AI model to use")
    parser.add_argument("--api-key", help="Anthropic API key")
    parser.add_argument("--preserve", nargs="+",
                        help="Sections to preserve (e.g., 'Architecture Diagram')")

    args = parser.parse_args()

    summarizer = DocumentSummarizer(
        args.project_path,
        api_key=args.api_key,
        model=args.model
    )

    # Load custom prompt if provided
    custom_prompt = None
    if args.prompt:
        custom_prompt = Path(args.prompt).read_text()

    if args.action == "scan":
        candidates = summarizer.find_candidates()
        if not candidates:
            print("No documents need summarization (>100 non-empty lines).")
        else:
            print(f"Found {len(candidates)} document(s) that need summarization:\n")
            for c in candidates:
                print(f"  - {c.file_path}")
                print(f"    {c.reason}")
            print("\nTo summarize:")
            print(f"  python3 summarize_docs.py . --action summarize --file <path>")
            print(f"  python3 summarize_docs.py . --action batch --files <paths>")

    elif args.action == "summarize":
        if not args.file:
            print("Error: --file required for summarize action")
            sys.exit(1)

        if args.preserve:
            summarizer.summarize_with_preserve(
                args.file,
                args.preserve,
                args.output
            )
        else:
            summarizer.summarize(
                args.file,
                args.output,
                custom_prompt=custom_prompt,
                dry_run=args.dry_run
            )

    elif args.action == "batch":
        if not args.files:
            print("Error: --files required for batch action")
            sys.exit(1)

        results = summarizer.batch_summarize(
            args.files,
            custom_prompt=custom_prompt,
            output_dir=args.output,
            dry_run=args.dry_run
        )

        print("\n" + "=" * 40)
        print("Summary:")
        for path, result in results.items():
            print(f"  {path}: {result}")


if __name__ == "__main__":
    main()
