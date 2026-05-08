"""FastMCP entrypoint for Mnemolens."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastmcp import FastMCP

from .dream import DreamPlanner
from .search import HybridSearch
from .store import MemoryStore, SearchOptions


mcp = FastMCP("mnemolens")


@lru_cache(maxsize=1)
def get_store() -> MemoryStore:
    return MemoryStore()


def get_search() -> HybridSearch:
    return HybridSearch(get_store())


@mcp.tool
def mnemolens_search_memories(
    query: str,
    categories: list[str] | None = None,
    limit: int = 5,
    mode: str = "hybrid",
    include_metadata: bool = False,
) -> dict[str, Any]:
    """Retrieve usable memories, with optional trace and ranking metadata."""
    options = SearchOptions(
        categories=tuple(categories or ()),
        limit=limit,
        mode=mode,
    )
    return get_search().search(
        query,
        options,
        include_metadata=include_metadata,
    )


@mcp.tool
def mnemolens_create_memory(
    category: str,
    content: str,
    evidence: str | None = None,
) -> dict[str, Any]:
    """Create an immediately usable memory."""
    return get_store().create_memory(
        category=category,
        content=content,
        evidence=evidence,
    )

@mcp.tool
def mnemolens_list_memories(
    category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List memories by category and limit."""
    return get_store().list_memories(
        category=category,
        limit=limit,
    )


@mcp.tool
def mnemolens_get_memory(memory_id: str) -> dict[str, Any]:
    """Fetch one memory by id."""
    memory = get_store().get_memory(memory_id)
    if not memory:
        raise ValueError(f"memory not found: {memory_id}")
    return memory


@mcp.tool
def mnemolens_delete_memory(memory_id: str) -> dict[str, bool]:
    """Delete a memory by id."""
    return get_store().delete_memory(memory_id)


@mcp.tool
def mnemolens_get_trace(retrieval_id: str) -> dict[str, Any]:
    """Read a retrieval trace."""
    return get_store().get_trace(retrieval_id)


@mcp.tool
def mnemolens_dream(dry_run: bool = True) -> dict[str, Any]:
    """Run deterministic memory cleanup planning and write a dream report."""
    return DreamPlanner(get_store()).run(dry_run=dry_run)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
