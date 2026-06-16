#!/usr/bin/env python3
"""
Document Organizer - Organizes and optimizes project documentation.

Usage:
    python organize_docs.py [project_path] --action ACTION [--options]

Actions:
    - merge: Merge similar documents
    - split: Split long documents
    - reorganize: Reorganize directory structure
    - cleanup: Apply cleanup suggestions
"""

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Action(Enum):
    MERGE = "merge"
    SPLIT = "split"
    REORGANIZE = "reorganize"
    CLEANUP = "cleanup"


@dataclass
class MergeCandidate:
    """Represents documents that can be merged."""
    file1: str
    file2: str
    similarity: float
    suggested_name: str


@dataclass
class SplitCandidate:
    """Represents a document that can be split."""
    file_path: str
    suggested_splits: list  # [(section_name, line_ranges), ...]


class DocumentOrganizer:
    """Organizes and optimizes documentation."""

    DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc'}
    DOC_DIRECTORIES = ['docs', 'doc', 'documentation']

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.documents: dict[str, str] = {}  # path -> content

    def load_documents(self):
        """Load all documentation files."""
        for ext in self.DOC_EXTENSIONS:
            for path in self.project_path.rglob(f'*{ext}'):
                try:
                    content = path.read_text()
                    self.documents[str(path)] = content
                except Exception:
                    pass

    def find_merge_candidates(self) -> list[MergeCandidate]:
        """Find documents that could be merged."""
        candidates = []
        paths = list(self.documents.keys())

        for i, path1 in enumerate(paths):
            for path2 in paths[i+1:]:
                similarity = self._calculate_similarity(
                    self.documents[path1],
                    self.documents[path2]
                )
                if similarity > 0.5:  # 50% similarity threshold
                    suggested_name = self._suggest_merge_name(path1, path2)
                    candidates.append(MergeCandidate(
                        file1=path1,
                        file2=path2,
                        similarity=similarity,
                        suggested_name=suggested_name
                    ))

        return sorted(candidates, key=lambda x: x.similarity, reverse=True)

    def find_split_candidates(self, max_lines: int = 500) -> list[SplitCandidate]:
        """Find documents that should be split."""
        candidates = []

        for path, content in self.documents.items():
            lines = content.splitlines()
            if len(lines) > max_lines:
                splits = self._suggest_splits(content)
                if splits:
                    candidates.append(SplitCandidate(
                        file_path=path,
                        suggested_splits=splits
                    ))

        return candidates

    def merge_documents(self, file1: str, file2: str, output_name: str) -> bool:
        """Merge two documents into one."""
        if file1 not in self.documents or file2 not in self.documents:
            return False

        content1 = self.documents[file1]
        content2 = self.documents[file2]

        # Merge strategy: combine with section headers
        merged = f"# {output_name}\n\n"
        merged += "## Document 1\n\n"
        merged += content1
        merged += "\n\n## Document 2\n\n"
        merged += content2

        output_path = Path(file1).parent / f"{output_name}.md"
        output_path.write_text(merged)

        # Optionally remove original files
        if input("Remove original files? [y/N]: ").lower() == 'y':
            Path(file1).unlink()
            Path(file2).unlink()

        return True

    def split_document(self, file_path: str, sections: list[str]) -> bool:
        """Split a document into multiple files by sections."""
        if file_path not in self.documents:
            return False

        content = self.documents[file_path]
        lines = content.splitlines()

        # Find section boundaries
        section_pattern = re.compile(r'^##+\s+(.+)$')
        current_section = "introduction"
        section_content: dict[str, list[str]] = {"introduction": []}

        for i, line in enumerate(lines):
            match = section_pattern.match(line)
            if match:
                section_name = self._sanitize_filename(match.group(1))
                if section_name not in section_content:
                    section_content[section_name] = []
                current_section = section_name
            section_content[current_section].append(line)

        # Write new files
        original_path = Path(file_path)
        for section_name, section_lines in section_content.items():
            if section_name == "introduction" and not sections:
                # Keep introduction in original file
                original_path.write_text("\n".join(section_lines))
                continue

            if section_name in sections or not sections:
                output_path = original_path.parent / f"{original_path.stem}-{section_name}.md"
                output_path.write_text("\n".join(section_lines))
                print(f"Created: {output_path}")

        return True

    def reorganize_structure(self, target_dir: str = "docs") -> bool:
        """Reorganize documentation into a cleaner structure."""
        target_path = self.project_path / target_dir
        if not target_path.exists():
            target_path.mkdir(parents=True)

        # Categorize documents by keywords
        categories = {
            "guides": [],
            "api": [],
            "architecture": [],
            "tutorials": [],
            "other": []
        }

        for path in self.documents.keys():
            path_str = str(path).lower()
            content = self.documents[path].lower()

            if any(kw in path_str or kw in content for kw in ['guide', 'how-to', 'tutorial']):
                categories["guides"].append(path)
            elif any(kw in path_str or kw in content for kw in ['api', 'interface', 'endpoint']):
                categories["api"].append(path)
            elif any(kw in path_str or kw in content for kw in ['architecture', 'design', 'overview']):
                categories["architecture"].append(path)
            elif any(kw in path_str or kw in content for kw in ['tutorial', 'getting-started']):
                categories["tutorials"].append(path)
            else:
                categories["other"].append(path)

        # Create directories and move files
        for category, files in categories.items():
            if files:
                cat_dir = target_path / category
                cat_dir.mkdir(exist_ok=True)

                for src in files:
                    dst = cat_dir / Path(src).name
                    if src != str(dst):
                        shutil.move(src, dst)
                        print(f"Moved: {src} -> {dst}")

        return True

    def _calculate_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two documents."""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)

    def _suggest_merge_name(self, path1: str, path2: str) -> str:
        """Suggest a name for merged document."""
        name1 = Path(path1).stem.lower()
        name2 = Path(path2).stem.lower()

        # Find common words
        words1 = set(re.split(r'[-_]', name1))
        words2 = set(re.split(r'[-_]', name2))
        common = words1 & words2

        if common:
            return "-".join(sorted(common))
        return f"{Path(path1).stem}-and-{Path(path2).stem}"

    def _suggest_splits(self, content: str) -> list:
        """Suggest section splits for a document."""
        sections = []
        pattern = re.compile(r'^##+\s+(.+)$')

        for i, line in enumerate(content.splitlines()):
            match = pattern.match(line)
            if match:
                sections.append((match.group(1), i))

        return sections

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use in filename."""
        return re.sub(r'[^a-zA-Z0-9\-_]', '', name.lower().replace(' ', '-'))


def main():
    parser = argparse.ArgumentParser(description="Organize project documentation")
    parser.add_argument("project_path", nargs="?", default=".",
                        help="Path to project root")
    parser.add_argument("--action", choices=[a.value for a in Action],
                        required=True, help="Action to perform")
    parser.add_argument("--files", nargs="+", help="Files for merge/split")
    parser.add_argument("--output", help="Output name for merge")
    parser.add_argument("--sections", nargs="+", help="Sections to split")
    parser.add_argument("--target", default="docs", help="Target directory for reorganize")

    args = parser.parse_args()

    organizer = DocumentOrganizer(args.project_path)
    organizer.load_documents()

    action = Action(args.action)

    if action == Action.MERGE:
        if not args.files or len(args.files) != 2:
            print("Error: Merge requires exactly 2 files")
            sys.exit(1)
        output_name = args.output or organizer._suggest_merge_name(args.files[0], args.files[1])
        if organizer.merge_documents(args.files[0], args.files[1], output_name):
            print(f"Merged documents into: {output_name}.md")

    elif action == Action.SPLIT:
        if not args.files:
            print("Error: Split requires at least 1 file")
            sys.exit(1)
        sections = args.sections or []
        for file_path in args.files:
            organizer.split_document(file_path, sections)

    elif action == Action.REORGANIZE:
        organizer.reorganize_structure(args.target)

    elif action == Action.CLEANUP:
        print("Available cleanup operations:")
        print("1. Find merge candidates")
        print("2. Find split candidates")
        print("3. Reorganize structure")

        choice = input("Select operation [1-3]: ")
        if choice == "1":
            candidates = organizer.find_merge_candidates()
            for c in candidates:
                print(f"  {c.file1} <-> {c.file2} ({int(c.similarity*100)}%)")
        elif choice == "2":
            candidates = organizer.find_split_candidates()
            for c in candidates:
                print(f"  {c.file_path}: {len(c.suggested_splits)} sections")
        elif choice == "3":
            organizer.reorganize_structure(args.target)


if __name__ == "__main__":
    main()
