"""Local embedding providers for Mnemolens.

The default provider is intentionally dependency-free. It gives Mnemolens a real
local vector path for the MVP while leaving room for stronger local models later.
"""

from __future__ import annotations

import hashlib
import math
import re
import struct
from typing import Protocol


class EmbeddingProvider(Protocol):
    model_id: str
    dimensions: int

    def embed_query(self, text: str) -> list[float]:
        """Embed a query string."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple memory documents."""


class HashEmbeddingProvider:
    """Small deterministic local vectorizer.

    This is not intended to compete with model embeddings. It is a zero-setup
    vector baseline that supports local vector search and can be backfilled to a
    stronger provider later.
    """

    model_id = "mnemolens-hash-v1"
    dimensions = 384

    _TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = [token.lower() for token in self._TOKEN_RE.findall(text)]
        features: list[str] = []

        for token in tokens:
            features.append(f"tok:{token}")
            if len(token) >= 3:
                for index in range(len(token) - 2):
                    features.append(f"tri:{token[index:index + 3]}")

        for left, right in zip(tokens, tokens[1:]):
            features.append(f"bi:{left} {right}")

        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "little") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def encode_vector(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def decode_vector(blob: bytes) -> list[float]:
    if len(blob) % 4 != 0:
        raise ValueError("embedding blob length is not divisible by 4")
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
