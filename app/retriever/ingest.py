"""Ingestion CLI: folder of .xlsx (program workbooks) and .pdf (guidebooks)
→ chunks → embeddings → Chroma. Idempotent (deterministic chunk IDs).

Usage: python -m app.retriever.ingest [source_dir]
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from app.config import get_settings
from app.retriever import chunk as chunking
from app.retriever.embed import get_embedder
from app.retriever.extract import parse_guidebook, parse_program_workbook
from app.retriever.store import Store

log = logging.getLogger(__name__)


def ingest(source_dir: Path) -> dict[str, int]:
    settings = get_settings()
    chunks: list[chunking.Chunk] = []
    programs: list[str] = []

    for xlsx in sorted(source_dir.glob("*.xlsx")):
        try:
            rows, warmup = parse_program_workbook(xlsx)
        except Exception:
            log.exception("Skipping malformed workbook %s", xlsx.name)
            continue
        program = rows[0].program if rows else xlsx.stem
        programs.append(program)
        chunks += chunking.chunk_program(rows)
        chunks += chunking.chunk_warmup(warmup, program)
        log.info("%s: %d exercise rows", xlsx.name, len(rows))

    for pdf in sorted(source_dir.glob("*.pdf")):
        try:
            sections = parse_guidebook(pdf)
        except Exception:
            log.exception("Skipping malformed PDF %s", pdf.name)
            continue
        # The guidebook applies to the whole system; tag with a neutral program name.
        chunks += chunking.chunk_guide(sections, "Bodybuilding Transformation System", pdf.stem)
        log.info("%s: %d sections", pdf.name, len(sections))

    if not chunks:
        log.error("No chunks produced from %s", source_dir)
        return {}

    embedder = get_embedder(settings.embedding_backend, settings.embedding_model)
    embeddings = embedder.embed([c.text for c in chunks])
    store = Store(settings.chroma_dir)
    store.upsert(chunks, embeddings)

    counts: dict[str, int] = {}
    for c in chunks:
        counts[c.metadata["chunk_type"]] = counts.get(c.metadata["chunk_type"], 0) + 1
    counts["total_in_store"] = store.count()
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else get_settings().pdf_dir
    counts = ingest(source)
    log.info("ingested: %s", counts)


if __name__ == "__main__":
    main()
