"""Hybrid vector, FTS5, and trigram retrieval."""

from __future__ import annotations

import re
from typing import Any

from .embeddings import cosine_similarity, decode_vector
from .store import MemoryStore, SearchOptions


TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")


def build_fts_query(query: str) -> str:
    tokens = [token for token in TOKEN_RE.findall(query) if token]
    if not tokens:
        return '""'
    return " OR ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in tokens[:12])


class HybridSearch:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def search(
        self,
        query: str,
        options: SearchOptions,
        *,
        include_metadata: bool = False,
    ) -> dict[str, Any]:
        limit = max(1, min(options.limit, 20))
        categories = options.categories
        matches: dict[str, dict[str, Any]] = {}

        if options.mode in {"hybrid", "vector"}:
            for result in self._vector_search(query, categories, limit * 4):
                matches.setdefault(result["id"], result).update(result)

        if options.mode in {"hybrid", "text"}:
            fts_query = build_fts_query(query)
            if fts_query != '""':
                self._merge_text_results(matches, "fts", fts_query, categories, limit * 4)
                self._merge_text_results(matches, "trigram", fts_query, categories, limit * 4)

        scored = []
        for result in matches.values():
            vector_score = result.get("vector_score", 0.0)
            fts_score = result.get("fts_score", 0.0)
            trigram_score = result.get("trigram_score", 0.0)
            confidence_boost = min(max(float(result["confidence"]), 0.0), 1.0) * 0.08
            category_boost = 0.04 if result["category"] in {"episodic", "procedural"} else 0.0
            score = (
                vector_score * 0.55
                + fts_score * 0.22
                + trigram_score * 0.15
                + confidence_boost
                + category_boost
            )
            result["score"] = round(score, 6)
            result["match_reason"] = self._match_reason(result)
            scored.append(result)

        scored.sort(key=lambda item: item["score"], reverse=True)
        top_results = scored[:limit]
        retrieval_id = self.store.create_retrieval_event(
            query=query,
            results=top_results,
        )
        response = {
            "memories": [
                self._public_result(result, include_metadata=include_metadata)
                for result in top_results
            ],
        }
        if include_metadata:
            response["retrieval_id"] = retrieval_id
            response["search_mode"] = options.mode
        return response

    def _vector_search(
        self,
        query: str,
        categories: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, Any]]:
        query_vector = self.store.embedding_provider.embed_query(query)
        results: list[dict[str, Any]] = []
        for row in self.store.vector_rows(categories=categories):
            score = cosine_similarity(query_vector, decode_vector(row["embedding_blob"]))
            if score <= 0:
                continue
            memory = self.store._row_to_memory(row)
            memory["vector_score"] = round(score, 6)
            results.append(memory)
        results.sort(key=lambda item: item["vector_score"], reverse=True)
        return results[:limit]

    def _merge_text_results(
        self,
        matches: dict[str, dict[str, Any]],
        mode: str,
        fts_query: str,
        categories: tuple[str, ...],
        limit: int,
    ) -> None:
        table = "memory_fts" if mode == "fts" else "memory_trigram"
        score_key = "fts_score" if mode == "fts" else "trigram_score"
        rows = self.store.search_fts(
            table=table,
            query=fts_query,
            categories=categories,
            limit=limit,
        )
        total = max(len(rows), 1)
        for index, row in enumerate(rows):
            score = (total - index) / total
            existing = matches.setdefault(row["id"], row)
            existing[score_key] = max(existing.get(score_key, 0.0), round(score, 6))

    def _match_reason(self, result: dict[str, Any]) -> str:
        reasons = []
        if result.get("vector_score", 0.0) > 0:
            reasons.append(f"vector={result['vector_score']}")
        if result.get("fts_score", 0.0) > 0:
            reasons.append(f"fts={result['fts_score']}")
        if result.get("trigram_score", 0.0) > 0:
            reasons.append(f"trigram={result['trigram_score']}")
        reasons.append(f"category={result['category']}")
        return ", ".join(reasons)

    def _public_result(self, result: dict[str, Any], *, include_metadata: bool) -> dict[str, Any]:
        public = {
            "id": result["id"],
            "category": result["category"],
            "content": result["content"],
        }
        if not include_metadata:
            return public
        return public | {
            "confidence": result["confidence"],
            "score": result["score"],
            "vector_score": result.get("vector_score"),
            "fts_score": result.get("fts_score"),
            "trigram_score": result.get("trigram_score"),
            "match_reason": result["match_reason"],
            "usage_status": "selected",
        }
