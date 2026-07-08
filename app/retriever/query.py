"""Retrieve → grounded prompt → Claude → answer with sources.

Grounding rules (CLAUDE.md §2) are enforced in the prompt: program facts must
come from retrieved chunks and be labeled "from your Nippard program"; anything
else is labeled "general coaching"; missing details are admitted, not invented.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

from app.config import get_settings
from app.contract import Exercise
from app.retriever.embed import Embedder, get_embedder
from app.retriever.store import Store

GROUNDING_PROMPT = """\
You answer questions about the user's Jeff Nippard training program using ONLY
the retrieved excerpts below as the source of program facts.

Rules:
- Program specifics (exercises, sets, reps, RPE, rest, weeks, days) MUST come
  from the excerpts. Label that content "from your Nippard program".
- You may add established coaching knowledge, but label it "general coaching".
- If the excerpts don't contain the detail asked about, say so plainly.
  Never invent program specifics or attribute made-up advice to Nippard.

Retrieved excerpts:
{context}
"""


@dataclass
class AskResult:
    answer: str
    sources: list[dict] = field(default_factory=list)
    exercises: list[Exercise] = field(default_factory=list)


class Retriever:
    """Holds the embedder + store; the LLM call is a thin layer on top."""

    def __init__(self) -> None:
        s = get_settings()
        self._settings = s
        self._embedder: Embedder = get_embedder(s.embedding_backend, s.embedding_model)
        self._store = Store(s.chroma_dir)

    def retrieve(self, question: str, where: dict | None = None,
                 top_k: int | None = None) -> list[dict]:
        [embedding] = self._embedder.embed([question])
        return self._store.query(embedding, top_k or self._settings.top_k, where)

    def ask(self, question: str, where: dict | None = None) -> AskResult:
        hits = self.retrieve(question, where)
        if not hits:
            return AskResult(answer="Nothing has been ingested yet — run the ingest CLI first.")

        context = "\n\n---\n\n".join(
            f"[{i + 1}] ({h['metadata'].get('chunk_type')}) {h['text']}"
            for i, h in enumerate(hits)
        )
        if not self._settings.anthropic_api_key:
            return AskResult(
                answer="ANTHROPIC_API_KEY is not configured — returning retrieved "
                       "program data only (from your Nippard program), no coaching.",
                sources=_sources(hits), exercises=_records(hits),
            )
        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
        response = client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=self._settings.max_tokens,
            system=GROUNDING_PROMPT.format(context=context),
            messages=[{"role": "user", "content": question}],
        )
        answer = "".join(b.text for b in response.content if b.type == "text")
        return AskResult(answer=answer, sources=_sources(hits), exercises=_records(hits))


def _sources(hits: list[dict]) -> list[dict]:
    out = []
    for h in hits:
        m = h["metadata"]
        out.append({k: m[k] for k in ("chunk_type", "program", "block", "week",
                                      "day", "exercise", "section", "page") if k in m})
    return out


def _records(hits: list[dict]) -> list[Exercise]:
    seen, out = set(), []
    for h in hits:
        raw = h["metadata"].get("record")
        if not raw:
            continue
        parsed = json.loads(raw)
        for item in parsed if isinstance(parsed, list) else [parsed]:
            ex = Exercise.model_validate(item)
            if (key := ex.exercise) not in seen:
                seen.add(key)
                out.append(ex)
    return out
