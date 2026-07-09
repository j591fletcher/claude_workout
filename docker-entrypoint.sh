#!/bin/sh
# pdfs/ and data/ are volumes, not baked into the image, so ingestion has to
# happen at container start, not build time. Idempotent: only runs if the
# Chroma store doesn't exist yet — re-ingesting on every restart would be slow
# and pointless. To force a re-ingest after updating pdfs/, delete data/chroma.
set -e

if [ ! -f /app/data/chroma/chroma.sqlite3 ]; then
    echo "No Chroma store found at /app/data/chroma — running ingestion..."
    python -m app.retriever.ingest /app/pdfs
else
    echo "Chroma store already exists — skipping ingestion (delete data/chroma to force a re-run)."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
