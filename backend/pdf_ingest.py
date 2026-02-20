"""PDF ingestion pipeline with async chunk embedding."""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Any

from backend.utils import sanitize_pdf_text


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def extract_pdf_chunks(file_path: str) -> list[dict[str, Any]]:
    try:
        import fitz
    except Exception:
        return []

    doc = fitz.open(file_path)
    out: list[dict[str, Any]] = []
    for page_idx, page in enumerate(doc, start=1):
        text = sanitize_pdf_text(page.get_text("text"))
        if not text:
            continue
        for i, chunk in enumerate(_chunk_text(text)):
            out.append({
                "chunk_id": f"{Path(file_path).name}-{page_idx}-{i}",
                "text": chunk,
                "source_page": page_idx,
                "file_name": Path(file_path).name,
            })
    return out


async def _embed_text(text: str) -> list[float]:
    if os.getenv("EMBEDDING_BACKEND", "local") == "openai":
        from openai import OpenAI

        client = OpenAI()
        emb = client.embeddings.create(model="text-embedding-3-small", input=text)
        return list(emb.data[0].embedding)

    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255.0 for b in digest[:64]]


async def ingest_pdfs(file_paths: list[str], vector_store, tracker) -> int:
    chunks = []
    for p in file_paths:
        chunks.extend(extract_pdf_chunks(p))

    async def process(chunk: dict[str, Any]) -> None:
        embedding = await _embed_text(chunk["text"])
        vector_store.add(
            chunk_id=chunk["chunk_id"],
            text=chunk["text"],
            metadata={"file_name": chunk["file_name"], "source_page": chunk["source_page"]},
            embedding=embedding,
        )
        tracker.conn.execute(
            "INSERT INTO embeddings_meta(file_name, chunk_id, text, source_page) VALUES (?, ?, ?, ?)",
            (chunk["file_name"], chunk["chunk_id"], chunk["text"][:1200], chunk["source_page"]),
        )

    await asyncio.gather(*[process(c) for c in chunks])
    tracker.conn.commit()
    return len(chunks)
