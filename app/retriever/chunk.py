"""Structure-aware chunking: program rows and guide sections → Chroma-ready chunks.

Three chunk types:
- exercise_row: one exercise on one week/day; carries the full Data Contract
  record as JSON in metadata (`record`) so answers can return structured data.
- day_table: a whole week/day session, for session-level questions.
- guide_section: methodology prose from the guidebook.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from app.contract import Exercise
from app.retriever.extract import GuideSection, ProgramRow

MAX_SECTION_CHARS = 2400


@dataclass
class Chunk:
    id: str
    text: str
    metadata: dict  # scalar values only (Chroma requirement)


def _cid(*parts: object) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:20]


def row_to_record(row: ProgramRow) -> Exercise:
    notes = []
    if row.intensity:
        notes.append(f"last-set intensity: {row.intensity}")
    if row.warmup_sets:
        notes.append(f"warm-up sets: {row.warmup_sets}")
    if row.substitutions:
        notes.append("subs: " + " / ".join(row.substitutions))
    if row.notes:
        notes.append(row.notes)
    return Exercise(
        exercise=row.exercise, sets=row.working_sets, reps=row.reps,
        rpe=f"{row.rpe_early} (last set {row.rpe_last})", rest=row.rest,
        weight=None, source="nippard", notes="; ".join(notes) or None,
    )


def _row_line(row: ProgramRow) -> str:
    parts = [f"{row.exercise}: {row.working_sets} working sets x {row.reps} reps",
             f"RPE {row.rpe_early} (last set {row.rpe_last})", f"rest {row.rest}"]
    if row.intensity:
        parts.append(f"last-set intensity: {row.intensity}")
    if row.warmup_sets:
        parts.append(f"warm-up sets: {row.warmup_sets}")
    return ", ".join(parts)


def chunk_program(rows: list[ProgramRow]) -> list[Chunk]:
    chunks: list[Chunk] = []
    by_day: dict[tuple, list[ProgramRow]] = {}
    for row in rows:
        by_day.setdefault((row.program, row.block, row.week, row.day), []).append(row)

        ctx = f"{row.program} program, {row.block} Block, Week {row.week}, {row.day}"
        text = f"{ctx} — {_row_line(row)}"
        if row.substitutions:
            text += ". Substitutions: " + " / ".join(row.substitutions)
        if row.notes:
            text += f". Notes: {row.notes}"
        chunks.append(Chunk(
            id=_cid("ex", row.program, row.week, row.day, row.exercise),
            text=text,
            metadata={
                "chunk_type": "exercise_row", "program": row.program,
                "block": row.block, "week": row.week, "day": row.day,
                "exercise": row.exercise,
                "record": row_to_record(row).model_dump_json(),
            },
        ))

    for (program, block, week, day), day_rows in by_day.items():
        lines = [f"{program} program, {block} Block, Week {week}, {day} session:"]
        lines += [f"- {_row_line(r)}" for r in day_rows]
        chunks.append(Chunk(
            id=_cid("day", program, week, day),
            text="\n".join(lines),
            metadata={
                "chunk_type": "day_table", "program": program, "block": block,
                "week": week, "day": day,
                "record": json.dumps([row_to_record(r).model_dump() for r in day_rows]),
            },
        ))
    return chunks


def chunk_guide(sections: list[GuideSection], program: str, source_name: str) -> list[Chunk]:
    chunks = []
    for sec in sections:
        for i, piece in enumerate(_split(sec.text)):
            chunks.append(Chunk(
                id=_cid("guide", source_name, sec.title, i),
                text=f"{program} guidebook — {sec.title}:\n{piece}",
                metadata={"chunk_type": "guide_section", "program": program,
                          "section": sec.title, "page": sec.first_page},
            ))
    return chunks


def chunk_warmup(text: str, program: str) -> list[Chunk]:
    if not text.strip():
        return []
    return [Chunk(
        id=_cid("warmup", program),
        text=f"{program} program — Warm-Up Protocol:\n{text}",
        metadata={"chunk_type": "guide_section", "program": program,
                  "section": "Warm-Up Protocol", "page": 0},
    )]


def _split(text: str, limit: int = MAX_SECTION_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    pieces, buf = [], ""
    for para in text.split("\n"):
        if len(buf) + len(para) > limit and buf:
            pieces.append(buf.strip())
            buf = ""
        buf += para + "\n"
    if buf.strip():
        pieces.append(buf.strip())
    return pieces
