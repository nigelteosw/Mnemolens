"""Deterministic memory cleanup reports for the MVP."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .store import MemoryStore


SPACE_RE = re.compile(r"\s+")


def normalize_content(content: str) -> str:
    return SPACE_RE.sub(" ", content.strip().lower())


class DreamPlanner:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def run(self, *, dry_run: bool = True) -> dict[str, Any]:
        memories = self.store.list_memories(limit=500)
        duplicates = self._find_duplicates(memories)
        weak_memories = [
            memory for memory in memories
            if float(memory["confidence"]) <= 0.5
        ]

        report = self._render_report(
            duplicates=duplicates,
            weak_memories=weak_memories,
            dry_run=dry_run,
        )
        dream_run_id = self.store.create_dream_run(report=report)
        return {
            "dream_run_id": dream_run_id,
            "dry_run": dry_run,
            "report_markdown": report,
            "actions": [],
        }

    def _find_duplicates(self, memories: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for memory in memories:
            key = (memory["category"], normalize_content(memory["content"]))
            grouped[key].append(memory)
        return [items for items in grouped.values() if len(items) > 1]

    def _render_report(
        self,
        *,
        duplicates: list[list[dict[str, Any]]],
        weak_memories: list[dict[str, Any]],
        dry_run: bool,
    ) -> str:
        duplicate_items = "\n".join(
            f"- Replace {len(group)} duplicates by deleting them and creating one record: {group[0]['content']}"
            for group in duplicates
        ) or "- None found."
        weak_items = "\n".join(
            f"- Review memory: {memory['content']}"
            for memory in weak_memories[:20]
        ) or "- None found."

        return f"""## Mnemolens Dream Report

Mode: {'dry run' if dry_run else 'apply'}

### Duplicate Memories
{duplicate_items}

### Weak Memories
{weak_items}

### Notes
- Hot-path writes are immutable and usable immediately.
- Merge or replacement means delete old records, then create new records.
- MVP dream reports are cleanup plans and do not apply changes automatically.
"""
