"""Retrieve → grounded prompt → Claude → answer with sources.

Grounding rules (CLAUDE.md §2) are enforced in the prompt: program specifics
must come from retrieved chunks and be labeled with that chunk's own program
name (pdfs/ holds more than one program — not everything is Nippard's);
anything else is labeled "general coaching"; missing details are admitted,
not invented. Chunks too dissimilar from the question (cosine distance above
retrieval_max_distance) are dropped before they ever reach the model, so
irrelevant excerpts can't be misread as grounding for a made-up answer.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from app.config import get_settings
from app.contract import Exercise
from app.llm import LLMUnavailable, get_llm_client
from app.retriever.embed import Embedder, get_embedder
from app.retriever.store import Store

log = logging.getLogger(__name__)

GROUNDING_PROMPT = """\
You answer questions about the user's training programs using ONLY the
retrieved excerpts below as the source of program facts.

Rules:
- Program specifics (exercises, sets, reps, RPE, rest, weeks, days, technique
  cues) MUST come directly from the excerpts. Label that content using the
  excerpt's own program name shown in brackets, e.g. "from your <Program>
  program".
- The user's own wording is not a source. If the user says "my Nippard
  program" but no excerpt's bracketed program name matches, do NOT say
  "Nippard" in your answer — use the excerpt's actual program name, or say
  the detail isn't in their program materials if no excerpt supports it.
- An excerpt being retrieved does not make it relevant. If the excerpts don't
  literally state the specific detail asked (a number, a cue, a rule), say so
  plainly — never invent specifics and attribute them to any program.
- You may add established coaching knowledge beyond the excerpts, but label
  it "general coaching" — never attribute it to a program.

Retrieved excerpts (each tagged with its program):
{context}
"""


def _format_context(hits: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[{i + 1}] (program: {h['metadata'].get('program', 'unknown')}, "
        f"{h['metadata'].get('chunk_type')}) {h['text']}"
        for i, h in enumerate(hits)
    )


def flag_ungrounded_programs(answer: str, hits: list[dict], all_programs: set[str]) -> str:
    """Post-answer safety net: local models sometimes name a real program from
    their own training data rather than from what was actually retrieved (seen
    live in Phase 4 testing — see HANDOFF.md)."""
    cited = {h["metadata"].get("program") for h in hits if h["metadata"].get("program")}
    warnings = []

    mentioned = sorted(p for p in all_programs - cited if p and p.lower() in answer.lower())
    if mentioned:
        warnings.append(f'mentions {", ".join(mentioned)}, but none of the retrieved '
                        "sources are from that program")

    # program_name_from_filename() always strips the author's name, so "Nippard"
    # never legitimately appears in a cited excerpt's program field — any mention
    # of it in the answer is provably not sourced from an excerpt.
    if "nippard" in answer.lower() and not any("nippard" in (c or "").lower() for c in cited):
        warnings.append('says "Nippard" — that name is never in the retrieved excerpt '
                        "metadata, so it wasn't sourced from one")

    if not warnings:
        return answer
    return (answer + "\n\n⚠️ Grounding check: this answer " + "; and it also ".join(warnings)
            + ". Treat any specifics tied to that as unverified.")


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
        hits = self._store.query(embedding, top_k or self._settings.top_k, where)
        kept = [h for h in hits if h["distance"] <= self._settings.retrieval_max_distance]
        if len(kept) < len(hits):
            log.info("filtered %d/%d retrieved chunks as too dissimilar (max_distance=%.2f)",
                      len(hits) - len(kept), len(hits), self._settings.retrieval_max_distance)
        return kept

    def distinct_programs(self) -> set[str]:
        return self._store.distinct_programs()

    def ask(self, question: str, where: dict | None = None) -> AskResult:
        hits = self.retrieve(question, where)
        if not hits:
            return AskResult(answer="Nothing relevant was retrieved for this question — "
                                     "either it hasn't been ingested, or no program excerpt "
                                     "is a close enough match to answer from.")

        context = _format_context(hits)
        llm = get_llm_client(self._settings)
        if llm is None:
            return AskResult(
                answer="No LLM backend configured — returning retrieved program "
                       "data only, no coaching.",
                sources=sources_from_hits(hits), exercises=_records(hits),
            )
        try:
            answer = llm.complete(GROUNDING_PROMPT.format(context=context), question)
        except LLMUnavailable as e:
            return AskResult(
                answer=f"{e} — returning retrieved program data only, no coaching.",
                sources=sources_from_hits(hits), exercises=_records(hits),
            )
        answer = flag_ungrounded_programs(answer, hits, self.distinct_programs())
        return AskResult(answer=answer, sources=sources_from_hits(hits), exercises=_records(hits))


def sources_from_hits(hits: list[dict]) -> list[dict]:
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
