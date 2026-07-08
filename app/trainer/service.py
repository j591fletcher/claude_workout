"""Module A: the trainer persona. Wires Module B (program retrieval — pdfs/
holds more than one program, not just Nippard's) and Module C (Hevy data)
into the runtime system prompt in prompts/trainer.md and calls the LLM.
Grounding + labeling rules (CLAUDE.md §2) are enforced in the system prompt:
program facts must come from the retrieved excerpts and be labeled with that
excerpt's own program name; everything else is "general coaching". Retrieval
already drops chunks too dissimilar to the question (see Retriever.retrieve),
so a retrieved excerpt being present is a much stronger relevance signal —
but the prompt still forbids treating "retrieved" as "relevant" blindly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings
from app.hevy import service as hevy
from app.hevy.client import HevyError
from app.llm import LLMUnavailable, get_llm_client
from app.retriever.query import Retriever, flag_ungrounded_programs, sources_from_hits

CONTEXT_TEMPLATE = """\
{trainer_prompt}

-------------------------------------
RETRIEVED PROGRAM EXCERPTS
-------------------------------------
Use ONLY these excerpts for program specifics (exercises, sets, reps, RPE,
rest, technique cues). Label specifics using each excerpt's own program name
shown in brackets, e.g. "from your <Program> program".

The user's own wording is not a source. If the user says "my Nippard
program" but no excerpt's bracketed program name matches, do NOT say
"Nippard" in your answer — use the excerpt's actual program name, or say
plainly that the detail isn't in their program materials.

An excerpt being retrieved does not make it relevant. If the excerpts don't
literally state the specific detail asked (a number, a cue, a rule), say so
— never invent it and attribute it to any program.

{program_context}

-------------------------------------
HEVY DATA (source of truth for current working weights + recent log)
-------------------------------------
{hevy_context}
"""

NO_HITS = "(no matching program excerpts retrieved for this question)"


@dataclass
class ChatResult:
    answer: str
    sources: list[dict] = field(default_factory=list)


class Trainer:
    def __init__(self, retriever: Retriever | None = None) -> None:
        self._settings = get_settings()
        self._retriever = retriever or Retriever()
        self._prompt = self._settings.trainer_prompt_path.read_text(encoding="utf-8")

    def chat(self, message: str, where: dict | None = None) -> ChatResult:
        hits = self._retriever.retrieve(message, where)
        program_context = _format_hits(hits) if hits else NO_HITS
        hevy_context = _hevy_context()

        system = CONTEXT_TEMPLATE.format(
            trainer_prompt=self._prompt,
            program_context=program_context,
            hevy_context=hevy_context,
        )

        llm = get_llm_client(self._settings)
        if llm is None:
            return ChatResult(
                answer="No LLM backend configured — returning retrieved data only, "
                       f"no coaching:\n\n{program_context}\n\n{hevy_context}",
                sources=sources_from_hits(hits),
            )
        try:
            answer = llm.complete(system, message)
        except LLMUnavailable as e:
            return ChatResult(
                answer=f"{e} — returning retrieved data only, no coaching:"
                       f"\n\n{program_context}\n\n{hevy_context}",
                sources=sources_from_hits(hits),
            )
        answer = flag_ungrounded_programs(answer, hits, self._retriever.distinct_programs())
        return ChatResult(answer=answer, sources=sources_from_hits(hits))


def _format_hits(hits: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"[{i + 1}] (program: {h['metadata'].get('program', 'unknown')}, "
        f"{h['metadata'].get('chunk_type')}) {h['text']}"
        for i, h in enumerate(hits)
    )


def _hevy_context() -> str:
    try:
        weights = hevy.working_weights()
        routines = hevy.routine_summaries()
        recent = hevy.recent_workout_summaries(limit=3)
    except HevyError as e:
        return f"(Hevy data unavailable: {e})"

    lines = ["Current working weights (max logged weight per exercise — NOT 1RMs,"
              " never derive percentages from these):"]
    for e in weights:
        w = f"{e.weight:g} lb" if e.weight is not None else "bodyweight"
        lines.append(f"- {e.exercise}: {w} (last hit {e.sets}x{e.reps}, RPE {e.rpe})")

    lines.append("\nTracked routines (verify these back to the user before"
                  " programming from them):")
    lines.extend(routines)

    lines.append("\nMost recent logged sessions:")
    lines.extend(recent)

    return "\n".join(lines)
