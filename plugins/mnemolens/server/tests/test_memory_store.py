from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from mnemolens.search import HybridSearch
from mnemolens.store import MemoryStore, SearchOptions


def test_hot_path_memory_is_retrieved_immediately(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mnemolens.sqlite3")
    try:
        memory = store.create_memory(
            category="semantic",
            content="This repo uses TanStack Router, not React Router.",
            evidence="User corrected the router choice.",
        )

        search = HybridSearch(store)
        result = search.search("router changes", SearchOptions())
        assert result["memories"]
        assert result["memories"][0]["id"] == memory["id"]
        assert set(result["memories"][0]) == {"id", "category", "content"}
        assert "retrieval_id" not in result

        result_with_metadata = search.search(
            "router changes",
            SearchOptions(),
            include_metadata=True,
        )
        assert result_with_metadata["memories"][0]["confidence"] == 0.5
        assert result_with_metadata["memories"][0]["usage_status"] == "selected"
        trace = store.get_trace(result_with_metadata["retrieval_id"])
        assert trace["results"][0]["usage_status"] == "selected"
    finally:
        store.close()


def test_delete_memory_removes_it_from_search(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mnemolens.sqlite3")
    try:
        memory = store.create_memory(
            category="procedural",
            content="Use Python for local scripts.",
        )

        before = HybridSearch(store).search("Python scripts", SearchOptions())
        assert before["memories"]

        assert store.delete_memory(memory["id"]) == {"ok": True}
        after = HybridSearch(store).search("Python scripts", SearchOptions())
        assert after["memories"] == []
        assert store.get_memory(memory["id"]) is None
    finally:
        store.close()


def test_cached_store_can_search_from_worker_threads(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "mnemolens.sqlite3")
    try:
        memory = store.create_memory(
            category="semantic",
            content="Mnemolens search uses FTS5 and trigram indexes.",
            confidence=0.9,
        )

        def search_from_worker() -> str:
            result = HybridSearch(store).search("trigram indexes", SearchOptions())
            assert result["memories"]
            return result["memories"][0]["id"]

        def list_from_worker() -> str:
            result = store.list_memories()
            assert result
            return result[0]["id"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda call: call(), [search_from_worker, list_from_worker]))

        assert results == [memory["id"], memory["id"]]
    finally:
        store.close()
