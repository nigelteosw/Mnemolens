"""SQLite storage for Mnemolens."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .embeddings import EmbeddingProvider, HashEmbeddingProvider, encode_vector


VALID_CATEGORIES = {"semantic", "episodic", "procedural"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_db_path() -> Path:
    configured = os.environ.get("MNEMOLENS_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".codex" / "mnemolens" / "mnemolens.sqlite3"


@dataclass(frozen=True)
class SearchOptions:
    categories: tuple[str, ...] = ()
    limit: int = 5
    mode: str = "hybrid"


class MemoryStore:
    def __init__(
        self,
        db_path: Path | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.db_path = db_path or default_db_path()
        self.embedding_provider = embedding_provider or HashEmbeddingProvider()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self._require_search_capabilities()
        self.migrate()

    def close(self) -> None:
        with self._lock:
            self.conn.close()

    def _require_search_capabilities(self) -> None:
        with self._lock:
            try:
                self.conn.execute("CREATE VIRTUAL TABLE temp.__mnemolens_fts_check USING fts5(content)")
                self.conn.execute(
                    "CREATE VIRTUAL TABLE temp.__mnemolens_trigram_check "
                    "USING fts5(content, tokenize='trigram')"
                )
            except sqlite3.Error as exc:
                raise RuntimeError(
                    "Mnemolens requires SQLite FTS5 with trigram tokenizer support. "
                    "Install a Python build linked against SQLite 3.34+ with FTS5 enabled."
                ) from exc

    def migrate(self) -> None:
        with self._lock:
            self.conn.executescript(SCHEMA_SQL)
            self.conn.commit()

    def create_memory(
        self,
        *,
        category: str,
        content: str,
        confidence: float = 0.5,
        evidence: str | None = None,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._validate_category(category)
            now = utc_now()
            memory_id = str(uuid.uuid4())
            metadata_payload = dict(metadata or {})
            self.conn.execute(
                """
                INSERT INTO memories (
                    id, category, content, confidence, created_at,
                    tags_json, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    category,
                    content.strip(),
                    confidence,
                    now,
                    json.dumps(tags or []),
                    json.dumps(metadata_payload),
                ),
            )
            self._upsert_embedding(memory_id, content)
            if evidence:
                self._create_evidence(
                    memory_id,
                    source_type="agent_write",
                    quote=evidence,
                )
            self.conn.commit()
            memory = self.get_memory(memory_id) or {}
            return memory

    def delete_memory(self, memory_id: str) -> dict[str, bool]:
        with self._lock:
            existing = self.get_memory(memory_id)
            if not existing:
                raise KeyError(f"memory not found: {memory_id}")
            self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self.conn.commit()
            return {"ok": True}

    def _create_evidence(
        self,
        memory_id: str,
        *,
        source_type: str,
        quote: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            evidence_id = str(uuid.uuid4())
            self.conn.execute(
                """
                INSERT INTO memory_evidence (id, memory_id, source_type, quote, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (evidence_id, memory_id, source_type, quote, utc_now()),
            )
            return dict(self.conn.execute("SELECT * FROM memory_evidence WHERE id = ?", (evidence_id,)).fetchone())

    def get_memory(self, memory_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self.conn.execute("SELECT rowid, * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            return self._row_to_memory(row) if row else None

    def list_memories(
        self,
        *,
        category: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            clauses: list[str] = []
            params: list[Any] = []
            if category:
                clauses.append("category = ?")
                params.append(category)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = self.conn.execute(
                f"""
                SELECT rowid, * FROM memories
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (*params, max(1, min(limit, 500))),
            ).fetchall()
            return [self._row_to_memory(row) for row in rows]

    def active_memory_rows(
        self,
        *,
        categories: tuple[str, ...] = (),
    ) -> list[sqlite3.Row]:
        with self._lock:
            clauses: list[str] = []
            params: list[Any] = []
            if categories:
                placeholders = ", ".join("?" for _ in categories)
                clauses.append(f"category IN ({placeholders})")
                params.extend(categories)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            return self.conn.execute(
                f"SELECT rowid, * FROM memories {where_sql}",
                params,
            ).fetchall()

    def search_fts(
        self,
        *,
        table: str,
        query: str,
        categories: tuple[str, ...],
        limit: int,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if table not in {"memory_fts", "memory_trigram"}:
                raise ValueError("invalid search table")
            clauses = [
                f"{table} MATCH ?",
            ]
            params: list[Any] = [query]
            if categories:
                placeholders = ", ".join("?" for _ in categories)
                clauses.append(f"m.category IN ({placeholders})")
                params.extend(categories)
            rows = self.conn.execute(
                f"""
                SELECT m.rowid, m.*, bm25({table}) AS rank
                FROM {table}
                JOIN memories m ON m.rowid = {table}.rowid
                WHERE {' AND '.join(clauses)}
                ORDER BY rank
                LIMIT ?
                """,
                (*params, max(1, min(limit, 50))),
            ).fetchall()
            return [self._row_to_memory(row) | {"rank": row["rank"]} for row in rows]

    def vector_rows(
        self,
        *,
        categories: tuple[str, ...],
    ) -> list[sqlite3.Row]:
        with self._lock:
            clauses: list[str] = []
            params: list[Any] = []
            if categories:
                placeholders = ", ".join("?" for _ in categories)
                clauses.append(f"m.category IN ({placeholders})")
                params.extend(categories)
            where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            return self.conn.execute(
                f"""
                SELECT m.rowid, m.*, v.embedding_model, v.embedding_dim, v.embedding_blob
                FROM memory_vectors v
                JOIN memories m ON m.id = v.memory_id
                {where_sql}
                """,
                params,
            ).fetchall()

    def create_retrieval_event(
        self,
        *,
        query: str,
        results: list[dict[str, Any]],
        turn_id: str | None = None,
    ) -> str:
        with self._lock:
            retrieval_id = str(uuid.uuid4())
            self.conn.execute(
                """
                INSERT INTO retrieval_events (id, turn_id, query, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (retrieval_id, turn_id, query, utc_now()),
            )
            for rank, result in enumerate(results, start=1):
                self.conn.execute(
                    """
                    INSERT INTO retrieval_results (
                        retrieval_id, memory_id, rank, score, match_reason, usage_status
                    )
                    VALUES (?, ?, ?, ?, ?, 'selected')
                    """,
                    (retrieval_id, result["id"], rank, result["score"], result["match_reason"]),
                )
            self.conn.commit()
            return retrieval_id

    def get_trace(self, retrieval_id: str) -> dict[str, Any]:
        with self._lock:
            event = self.conn.execute(
                "SELECT * FROM retrieval_events WHERE id = ?",
                (retrieval_id,),
            ).fetchone()
            if not event:
                raise KeyError(f"retrieval not found: {retrieval_id}")
            results = self.conn.execute(
                """
                SELECT rr.*, m.category, m.content, m.confidence
                FROM retrieval_results rr
                JOIN memories m ON m.id = rr.memory_id
                WHERE rr.retrieval_id = ?
                ORDER BY rr.rank ASC
                """,
                (retrieval_id,),
            ).fetchall()
            return {"event": dict(event), "results": [dict(row) for row in results]}

    def create_dream_run(self, *, report: str, status: str = "completed") -> str:
        with self._lock:
            run_id = str(uuid.uuid4())
            now = utc_now()
            self.conn.execute(
                """
                INSERT INTO dream_runs (
                    id, started_at, finished_at, status, report_markdown
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, now, now, status, report),
            )
            self.conn.commit()
            return run_id

    def _upsert_embedding(self, memory_id: str, content: str) -> None:
        vector = self.embedding_provider.embed_query(content)
        self.conn.execute(
            """
            INSERT INTO memory_vectors (
                memory_id, embedding_model, embedding_dim, embedding_blob, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
                embedding_model = excluded.embedding_model,
                embedding_dim = excluded.embedding_dim,
                embedding_blob = excluded.embedding_blob,
                updated_at = excluded.updated_at
            """,
            (
                memory_id,
                self.embedding_provider.model_id,
                self.embedding_provider.dimensions,
                encode_vector(vector),
                utc_now(),
            ),
        )

    def _row_to_memory(self, row: sqlite3.Row) -> dict[str, Any]:
        memory = dict(row)
        memory["tags"] = json.loads(memory.pop("tags_json") or "[]")
        memory["metadata"] = json.loads(memory.pop("metadata_json") or "{}")
        return memory

    def _validate_category(self, category: str) -> None:
        if category not in VALID_CATEGORIES:
            raise ValueError(f"invalid category: {category}")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id                  TEXT PRIMARY KEY,
    category            TEXT NOT NULL,
    content             TEXT NOT NULL,
    confidence          REAL NOT NULL DEFAULT 0.5,
    created_at          TEXT NOT NULL,
    tags_json           TEXT NOT NULL DEFAULT '[]',
    metadata_json       TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_memories_category ON memories (category);

CREATE TABLE IF NOT EXISTS memory_evidence (
    id              TEXT PRIMARY KEY,
    memory_id       TEXT NOT NULL,
    source_type     TEXT NOT NULL,
    quote           TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS memory_vectors (
    memory_id       TEXT PRIMARY KEY,
    embedding_model TEXT NOT NULL,
    embedding_dim   INTEGER NOT NULL,
    embedding_blob  BLOB NOT NULL,
    updated_at      TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS retrieval_events (
    id              TEXT PRIMARY KEY,
    turn_id         TEXT,
    query           TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS retrieval_results (
    retrieval_id    TEXT NOT NULL,
    memory_id       TEXT NOT NULL,
    rank            INTEGER NOT NULL,
    score           REAL NOT NULL,
    match_reason    TEXT,
    usage_status    TEXT NOT NULL DEFAULT 'selected',
    usage_note      TEXT,
    PRIMARY KEY (retrieval_id, memory_id),
    FOREIGN KEY (retrieval_id) REFERENCES retrieval_events(id) ON DELETE CASCADE,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dream_runs (
    id              TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,
    report_markdown TEXT,
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS dream_actions (
    id              TEXT PRIMARY KEY,
    dream_run_id    TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    memory_id       TEXT,
    before_json     TEXT,
    after_json      TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (dream_run_id) REFERENCES dream_runs(id) ON DELETE CASCADE
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    content,
    category,
    content='memories',
    content_rowid='rowid',
    tokenize='unicode61'
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_trigram USING fts5(
    content,
    category,
    content='memories',
    content_rowid='rowid',
    tokenize='trigram'
);

CREATE TRIGGER IF NOT EXISTS memories_ai_index AFTER INSERT ON memories
BEGIN
    INSERT INTO memory_fts(rowid, content, category)
    VALUES (new.rowid, new.content, new.category);
    INSERT INTO memory_trigram(rowid, content, category)
    VALUES (new.rowid, new.content, new.category);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad_delete AFTER DELETE ON memories
BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, content, category)
    VALUES ('delete', old.rowid, old.content, old.category);
    INSERT INTO memory_trigram(memory_trigram, rowid, content, category)
    VALUES ('delete', old.rowid, old.content, old.category);
END;
"""
