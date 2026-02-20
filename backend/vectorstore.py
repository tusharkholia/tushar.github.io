"""Vector store abstraction with Chroma primary and in-memory fallback."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    embedding: list[float]


class VectorStore:
    def __init__(self, persist_dir: str = "db/chroma") -> None:
        self.persist_dir = persist_dir
        self.backend = "memory"
        self.records: list[ChunkRecord] = []
        self.collection = None
        if os.getenv("VECTOR_BACKEND", "chroma") == "chroma":
            try:
                import chromadb

                client = chromadb.PersistentClient(path=persist_dir)
                self.collection = client.get_or_create_collection("gmat_notes")
                self.backend = "chroma"
            except Exception:
                self.backend = "memory"

    def add(self, chunk_id: str, text: str, metadata: dict[str, Any], embedding: list[float]) -> None:
        if self.backend == "chroma" and self.collection is not None:
            self.collection.add(ids=[chunk_id], documents=[text], embeddings=[embedding], metadatas=[metadata])
            return
        self.records.append(ChunkRecord(chunk_id, text, metadata, embedding))

    def query(self, embedding: list[float], top_k: int = 3) -> list[dict[str, Any]]:
        if self.backend == "chroma" and self.collection is not None:
            out = self.collection.query(query_embeddings=[embedding], n_results=top_k)
            items = []
            for idx, doc in enumerate(out.get("documents", [[]])[0]):
                items.append(
                    {
                        "text": doc,
                        "metadata": out.get("metadatas", [[]])[0][idx],
                        "score": 1.0,
                    }
                )
            return items

        scored = []
        for r in self.records:
            score = cosine_similarity(embedding, r.embedding)
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"text": r.text, "metadata": r.metadata, "score": round(score, 4)}
            for score, r in scored[:top_k]
        ]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
