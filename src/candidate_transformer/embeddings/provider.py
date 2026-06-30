from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Return deterministic vectors for input texts."""


class HashEmbeddingProvider:
    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = text.lower().split()
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 8) for value in vector]


class SentenceTransformerProvider:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [[float(value) for value in row] for row in vectors]


def create_embedding_provider() -> EmbeddingProvider:
    backend = os.getenv("CANDIDATE_TRANSFORMER_EMBEDDING_BACKEND", "hash")
    if backend == "sentence-transformer":
        model_name = os.getenv(
            "CANDIDATE_TRANSFORMER_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
        return SentenceTransformerProvider(model_name)
    return HashEmbeddingProvider()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return max(0.0, min(1.0, sum(a * b for a, b in zip(left, right, strict=True))))
