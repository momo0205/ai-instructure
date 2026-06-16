#!/usr/bin/env python3
"""
Document Scanner - Scans project for documentation issues and optimization opportunities.

Usage:
    python scan_docs.py [project_path] [--output JSON|TEXT]

This script scans project documentation and reports:
1. Documentation-code inconsistencies
2. Documents that could be merged
3. Overly long documents
4. Directory structure issues
5. Lint issues (duplicates, dead links, etc.)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class IssueType(Enum):
    # Consistency issues
    API_SIGNATURE_MISMATCH = "api_signature_mismatch"
    FUNCTION_SIGNATURE_MISMATCH = "function_signature_mismatch"
    CONFIG_MISMATCH = "config_mismatch"
    FILE_STRUCTURE_CHANGED = "file_structure_changed"

    # Organization issues
    OVERLAPPING_CONTENT = "overlapping_content"
    LONG_DOCUMENT = "long_document"
    DEAD_LINK = "dead_link"

    # Lint issues
    DUPLICATE_CONTENT = "duplicate_content"
    OUTDATED_VERSION = "outdated_version"
    LINE_LIMIT_EXCEEDED = "line_limit_exceeded"


@dataclass
class DocumentIssue:
    """Represents a documentation issue."""
    issue_type: IssueType
    file_path: str
    severity: str  # info, warning, error
    title: str
    description: str
    suggestion: str
    line_number: Optional[int] = None
    related_files: list = field(default_factory=list)


@dataclass
class Document:
    """Represents a documentation file."""
    path: str
    content: str
    title: str
    line_count: int
    sections: list = field(default_factory=list)


class DocumentScanner:
    """Scans project documentation for issues."""

    # File extensions to consider as documentation
    DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc'}

    # Documentation directories
    DOC_DIRECTORIES = {'docs', 'doc', 'documentation', '.'}

    # Default max line count before warning
    DEFAULT_MAX_LINES = 500

    # Common API/code patterns in docs
    API_PATTERN = re.compile(r'`([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)`')
    CONFIG_PATTERN = re.compile(r'`([A-Z_][A-Z0-9_]*)`')
    FILE_PATH_PATTERN = re.compile(r'`([^`\n]+\.(py|ts|js|go|java|cpp|c|h|hpp))`')

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.documents: list[Document] = []
        self.issues: list[DocumentIssue] = []
        self.code_files: dict[str, list] = {}  # file -> content lines

    def scan(self) -> list[DocumentIssue]:
        """Run full scan of project documentation."""
        self._load_code_files()
        self._load_documents()
        self._check_consistency()
        self._check_organization()
        self._check_lint()
        return self.issues

    def _load_code_files(self):
        """Load code files for comparison."""
        for ext in ['.py', '.ts', '.js', '.go', '.java']:
            for path in self.project_path.rglob(f'*{ext}'):
                try:
                    content = path.read_text()
                    self.code_files[str(path)] = content
                except Exception:
                    pass

    def _load_documents(self):
        """Load all documentation files."""
        for doc_dir in self.DOC_DIRECTORIES:
            doc_path = self.project_path / doc_dir
            if not doc_path.exists():
                continue

            for path in doc_path.rglob('*'):
                if path.suffix in self.DOC_EXTENSIONS:
                    try:
                        content = path.read_text()
                        doc = Document(
                            path=str(path),
                            content=content,
                            title=self._extract_title(content),
                            line_count=len(content.splitlines()),
                            sections=self._extract_sections(content)
                        )
                        self.documents.append(doc)
                    except Exception:
                        pass

        # Also check for docs in root or code directories
        for path in self.project_path.rglob('README*'):
            if path.suffix in self.DOC_EXTENSIONS or path.stem.upper() == 'README':
                try:
                    content = path.read_text()
                    doc = Document(
                        path=str(path),
                        content=content,
                        title=self._extract_title(content),
                        line_count=len(content.splitlines()),
                        sections=self._extract_sections(content)
                    )
                    if doc not in self.documents:
                        self.documents.append(doc)
                except Exception:
                    pass

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown document."""
        for line in content.splitlines()[:5]:
            if line.startswith('# '):
                return line[2:].strip()
        return ""

    def _extract_sections(self, content: str) -> list[str]:
        """Extract section headings from document."""
        sections = []
        for line in content.splitlines():
            if line.startswith('## '):
                sections.append(line[3:].strip())
        return sections

    def _check_consistency(self):
        """Check documentation against code for inconsistencies."""
        for doc in self.documents:
            # Check API signatures
            for match in self.API_PATTERN.finditer(doc.content):
                api_name = match.group(1)
                if not self._api_exists_in_code(api_name):
                    self.issues.append(DocumentIssue(
                        issue_type=IssueType.API_SIGNATURE_MISMATCH,
                        file_path=doc.path,
                        severity="warning",
                        title=f"API '{api_name}' may not exist",
                        description=f"Document references API '{api_name}' but it was not found in code",
                        suggestion=f"Verify '{api_name}' exists or update the documentation",
                        line_number=doc.content[:match.start()].count('\n') + 1
                    ))

            # Check config patterns
            for match in self.CONFIG_PATTERN.finditer(doc.content):
                config_name = match.group(1)
                if not self._config_exists_in_code(config_name):
                    self.issues.append(DocumentIssue(
                        issue_type=IssueType.CONFIG_MISMATCH,
                        file_path=doc.path,
                        severity="info",
                        title=f"Config '{config_name}' may not exist",
                        description=f"Document references config '{config_name}'",
                        suggestion=f"Verify '{config_name}' exists or remove from docs",
                        line_number=doc.content[:match.start()].count('\n') + 1
                    ))

            # Check file paths
            for match in self.FILE_PATH_PATTERN.finditer(doc.content):
                file_path = match.group(1)
                if not Path(self.project_path / file_path).exists():
                    self.issues.append(DocumentIssue(
                        issue_type=IssueType.DEAD_LINK,
                        file_path=doc.path,
                        severity="warning",
                        title=f"Dead link: '{file_path}'",
                        description=f"Document references file '{file_path}' which does not exist",
                        suggestion=f"Remove reference or create the file",
                        line_number=doc.content[:match.start()].count('\n') + 1
                    ))

    def _api_exists_in_code(self, api_name: str) -> bool:
        """Check if API exists in code files."""
        for content in self.code_files.values():
            # Simple pattern - look for function/class definition
            patterns = [
                rf'def\s+{api_name}\s*\(',
                rf'async\s+def\s+{api_name}\s*\(',
                rf'class\s+{api_name}\s*[\(:]',
                rf'const\s+{api_name}\s*=',
                rf'let\s+{api_name}\s*=',
                rf'{api_name}\s*=\s*\(',
            ]
            for pattern in patterns:
                if re.search(pattern, content):
                    return True
        return False

    def _config_exists_in_code(self, config_name: str) -> bool:
        """Check if config constant exists in code."""
        for content in self.code_files.values():
            if re.search(rf'^{config_name}\s*=', content, re.MULTILINE):
                return True
            if f'"{config_name}"' in content or f"'{config_name}'" in content:
                return True
        return False

    def _check_organization(self):
        """Check for organization issues."""
        # Check for long documents
        for doc in self.documents:
            if doc.line_count > self.DEFAULT_MAX_LINES:
                self.issues.append(DocumentIssue(
                    issue_type=IssueType.LONG_DOCUMENT,
                    file_path=doc.path,
                    severity="info",
                    title=f"Long document: {doc.line_count} lines",
                    description=f"Document has {doc.line_count} lines, consider splitting",
                    suggestion="Consider splitting into multiple documents by section",
                    related_files=[doc.path]
                ))

        # Check for overlapping content
        for i, doc1 in enumerate(self.documents):
            for doc2 in self.documents[i+1:]:
                similarity = self._calculate_similarity(doc1.content, doc2.content)
                if similarity > 0.7:  # 70% similarity threshold
                    self.issues.append(DocumentIssue(
                        issue_type=IssueType.OVERLAPPING_CONTENT,
                        file_path=doc1.path,
                        severity="warning",
                        title=f"Similar documents: {Path(doc1.path).name} and {Path(doc2.path).name}",
                        description=f"Documents are {int(similarity*100)}% similar",
                        suggestion="Consider merging these documents or consolidating content",
                        related_files=[doc1.path, doc2.path]
                    ))

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two documents."""
        # Simple word-based similarity
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _is_in_code_block(self, lines: list[str], line_idx: int) -> bool:
        """Check if a line is inside a code block (``` or indented)."""
        in_block = False
        for i, line in enumerate(lines):
            if line.strip().startswith('```'):
                if in_block:
                    in_block = False
                elif i < line_idx:
                    in_block = True
            # Check for indented code (4+ spaces or 1+ tab at start)
            if i < line_idx and in_block:
                return True
            if i == line_idx:
                return in_block
        return False

    def _check_lint(self):
        """Check for lint issues."""
        for doc in self.documents:
            lines = doc.content.splitlines()

            # Check for duplicate consecutive lines (skip code blocks)
            for i in range(len(lines) - 2):
                if self._is_in_code_block(lines, i):
                    continue
                if lines[i] == lines[i+1] == lines[i+2]:
                    self.issues.append(DocumentIssue(
                        issue_type=IssueType.DUPLICATE_CONTENT,
                        file_path=doc.path,
                        severity="warning",
                        title="Duplicate consecutive lines found",
                        description="Same line repeated 3+ times",
                        suggestion="Remove duplicate lines",
                        line_number=i + 1
                    ))

            # Check for outdated version markers
            outdated_patterns = [
                r'TODO:.*\d{4}[-/]\d{2}[-/]\d{2}',  # Old TODO dates
                r'v\d+\.\d+\.\d+',  # Old version numbers
                r'deprecated',  # Deprecated mentions
            ]
            for i, line in enumerate(lines):
                for pattern in outdated_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        self.issues.append(DocumentIssue(
                            issue_type=IssueType.OUTDATED_VERSION,
                            file_path=doc.path,
                            severity="info",
                            title="Potentially outdated content",
                            description=f"Found: {line.strip()[:50]}",
                            suggestion="Review and update if necessary",
                            line_number=i + 1
                        ))
                        break  # Only report once per line

            # Check line length
            for i, line in enumerate(lines):
                if len(line) > 120:
                    self.issues.append(DocumentIssue(
                        issue_type=IssueType.LINE_LIMIT_EXCEEDED,
                        file_path=doc.path,
                        severity="info",
                        title=f"Line {i+1} exceeds 120 characters",
                        description=f"Line has {len(line)} characters",
                        suggestion="Consider wrapping or restructuring",
                        line_number=i + 1
                    ))


def format_output(issues: list[DocumentIssue], output_format: str = "TEXT") -> str:
    """Format issues for output."""
    if output_format == "JSON":
        return json.dumps(
            [{"type": i.issue_type.value, "severity": i.severity,
              "file": i.file_path, "title": i.title,
              "description": i.description, "suggestion": i.suggestion,
              "line": i.line_number, "related": i.related_files}
             for i in issues],
            indent=2
        )

    # TEXT format
    if not issues:
        return "No documentation issues found."

    output = []
    output.append("=" * 60)
    output.append("Documentation Scan Report")
    output.append(f"Found {len(issues)} issue(s)")
    output.append("=" * 60)

    # Group by severity
    for severity in ["error", "warning", "info"]:
        severity_issues = [i for i in issues if i.severity == severity]
        if not severity_issues:
            continue

        output.append(f"\n### {severity.upper()} ({len(severity_issues)})")
        output.append("-" * 40)

        for issue in severity_issues:
            output.append(f"\n[{issue.issue_type.value}]")
            output.append(f"File: {issue.file_path}")
            if issue.line_number:
                output.append(f"Line: {issue.line_number}")
            output.append(f"Title: {issue.title}")
            output.append(f"Description: {issue.description}")
            output.append(f"Suggestion: {issue.suggestion}")
            if issue.related_files:
                output.append(f"Related: {', '.join(issue.related_files)}")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Scan project documentation")
    parser.add_argument("project_path", nargs="?", default=".",
                        help="Path to project root")
    parser.add_argument("--output", choices=["JSON", "TEXT"], default="TEXT",
                        help="Output format")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON (deprecated, use --output)")

    args = parser.parse_args()

    if args.json:
        args.output = "JSON"

    scanner = DocumentScanner(args.project_path)
    issues = scanner.scan()
    print(format_output(issues, args.output))

    return 0 if len(issues) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
