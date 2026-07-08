"""Chroma wrapper: persisted collection, idempotent upserts, filtered queries."""

from __future__ import annotations

from pathlib import Path

import chromadb

from app.retriever.chunk import Chunk

COLLECTION = "workout"


class Store:
    def __init__(self, persist_dir: Path):
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._col = self._client.get_or_create_collection(
            COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        self._distinct_programs_cache: set[str] | None = None

    def distinct_programs(self) -> set[str]:
        """Every program name ever ingested — used to catch an LLM naming a
        real program that simply wasn't part of what was retrieved."""
        if self._distinct_programs_cache is None:
            got = self._col.get(include=["metadatas"])
            self._distinct_programs_cache = {
                m["program"] for m in got["metadatas"] if m.get("program")
            }
        return self._distinct_programs_cache

    def upsert(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        ids = [c.id for c in chunks]
        if len(set(ids)) != len(ids):
            dupes = {i for i in ids if ids.count(i) > 1}
            raise ValueError(f"chunk id collision within a single ingest batch: {dupes} "
                              "— two chunks would overwrite each other; check the "
                              "chunk id generation, not a Chroma bug")
        for i in range(0, len(chunks), 500):
            batch = chunks[i:i + 500]
            self._col.upsert(
                ids=[c.id for c in batch],
                documents=[c.text for c in batch],
                metadatas=[c.metadata for c in batch],
                embeddings=embeddings[i:i + 500],
            )

    def query(self, embedding: list[float], top_k: int,
              where: dict | None = None) -> list[dict]:
        res = self._col.query(
            query_embeddings=[embedding], n_results=top_k,
            where=where or None, include=["documents", "metadatas", "distances"],
        )
        return [
            {"text": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0],
                                       res["distances"][0])
        ]

    def count(self) -> int:
        return self._col.count()
