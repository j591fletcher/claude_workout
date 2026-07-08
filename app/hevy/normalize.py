"""Normalize Hevy API responses into the Shared Data Contract (CLAUDE.md §3).

Field names confirmed against the live API at Checkpoint 2 (2026-07-08):
exercises carry `title` (not `name`), workouts carry `start_time` (not `date`),
set weights are `weight_kg` only. Working weights are max logged weights across
the configured routines — NOT 1RMs; never derive percentages from them.
"""

from __future__ import annotations

import logging
from typing import Iterable

from app.config import get_settings
from app.contract import Exercise

log = logging.getLogger(__name__)

KG_TO_LB = 2.2046226218


def kg_to_lb(kg: float) -> float:
    """Convert kg to lb, rounded to the nearest 0.5 lb."""
    return round(kg * KG_TO_LB * 2) / 2


def _working_sets(exercise: dict) -> list[dict]:
    """Non-warmup sets only — warmups never count toward working weights."""
    return [s for s in exercise.get("sets", []) if s.get("type") != "warmup"]


def _span(values: list[float | int]) -> str:
    """Render a list of numbers as a compact range string: [8, 10] -> "8-10"."""
    if not values:
        return "-"
    lo, hi = min(values), max(values)
    fmt = lambda v: f"{v:g}"
    return fmt(lo) if lo == hi else f"{fmt(lo)}-{fmt(hi)}"


def _fmt_rest(seconds: int | None) -> str:
    if not seconds:
        return "-"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d} min" if s else f"{m} min"


def workout_date(workout: dict) -> str:
    """YYYY-MM-DD from the workout's start_time."""
    return (workout.get("start_time") or "")[:10]


def workout_to_exercises(workout: dict) -> list[Exercise]:
    """One logged Hevy workout -> Data Contract entries (source="hevy")."""
    out: list[Exercise] = []
    for ex in workout.get("exercises", []):
        sets = _working_sets(ex)
        if not sets:
            continue
        weights = [s["weight_kg"] for s in sets if s.get("weight_kg")]  # 0kg == bodyweight, not a working weight
        out.append(Exercise(
            exercise=ex["title"],
            sets=len(sets),
            reps=_span([s["reps"] for s in sets if s.get("reps") is not None]),
            rpe=_span([s["rpe"] for s in sets if s.get("rpe") is not None]),
            rest="-",  # logged workouts don't record rest; routines do
            weight=kg_to_lb(max(weights)) if weights else None,
            source="hevy",
            notes=ex.get("notes") or None,
        ))
    return out


def routine_to_exercises(routine: dict) -> list[Exercise]:
    """One Hevy routine template -> Data Contract entries (source="hevy")."""
    out: list[Exercise] = []
    for ex in routine.get("exercises", []):
        sets = _working_sets(ex)
        if not sets:
            continue
        rep_bounds: list[int] = []
        for s in sets:
            rng = s.get("rep_range") or {}
            rep_bounds.extend(v for v in (rng.get("start"), rng.get("end")) if v is not None)
            if s.get("reps") is not None:
                rep_bounds.append(s["reps"])
        out.append(Exercise(
            exercise=ex["title"],
            sets=len(sets),
            reps=_span(rep_bounds),
            rpe="-",  # routine templates carry no RPE
            rest=_fmt_rest(ex.get("rest_seconds")),
            weight=None,
            source="hevy",
            notes=ex.get("notes") or None,
        ))
    return out


def is_tracked(workout: dict, routine_titles: Iterable[str] | None = None) -> bool:
    """Does this workout belong to one of the configured routines (by title,
    case-insensitive)? Workout titles inherit the routine title in Hevy."""
    titles = {t.lower() for t in (routine_titles or get_settings().hevy_routines)}
    return (workout.get("title") or "").strip().lower() in titles


def derive_working_weights(workouts: Iterable[dict],
                           routine_titles: Iterable[str] | None = None) -> list[Exercise]:
    """Current working weight per exercise = max non-warmup logged weight across
    the configured routines. NOT a 1RM. Each entry's sets/reps/rpe describe the
    session where the max was hit; notes say when and where.
    """
    titles = tuple(routine_titles or get_settings().hevy_routines)
    best: dict[str, tuple[float, Exercise]] = {}
    skipped = 0
    for w in workouts:
        if not is_tracked(w, titles):
            skipped += 1
            continue
        date = workout_date(w)
        for entry in workout_to_exercises(w):
            if entry.weight is None:
                continue
            key = entry.exercise.lower()
            prev = best.get(key)
            # ties go to the more recent session (workouts arrive newest-first)
            if prev is None or entry.weight > prev[0]:
                entry.notes = f"max hit {date} ({w.get('title')})"
                best[key] = (entry.weight, entry)
    log.info("derived working weights for %d exercises (%d workouts outside %s skipped)",
             len(best), skipped, titles)
    return sorted((e for _, e in best.values()), key=lambda e: e.exercise.lower())
