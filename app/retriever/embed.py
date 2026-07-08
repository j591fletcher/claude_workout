"""Embedder protocol + implementations.

`SentenceTransformersEmbedder` is the production default. `HashingEmbedder`
is a dependency-free fallback (feature-hashed character n-grams) for
environments that can't download models; select via EMBEDDING_BACKEND=hashing.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class Embedder(Protocol):
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformersEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # lazy: heavy import

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


class HashingEmbedder:
    """Cosine-normalized TF vectors of hashed word + character n-grams."""

    def __init__(self, dim: int = 1024):
        self.dim = dim

    def _features(self, text: str) -> list[str]:
        text = " ".join(text.lower().split())
        words = text.split()
        feats = list(words)
        feats += [" ".join(p) for p in zip(words, words[1:])]
        feats += [text[i:i + 4] for i in range(len(text) - 3)]
        return feats

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for f in self._features(text):
                h = int.from_bytes(hashlib.blake2b(f.encode(), digest_size=8).digest(), "big")
                vec[h % self.dim] += -1.0 if (h >> 63) & 1 else 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out


def get_embedder(backend: str, model_name: str) -> Embedder:
    if backend == "hashing":
        return HashingEmbedder()
    return SentenceTransformersEmbedder(model_name)
