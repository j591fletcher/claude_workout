"""Module C facade: fetch + normalize + summarize Hevy data.

Full workout history is ~32 paginated calls, so results are cached in-process
for a short TTL — enough to keep the trainer from re-pulling on every question
while still picking up new sessions the same day they're logged.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, TypeVar

from app.config import get_settings
from app.contract import Exercise
from app.hevy import normalize, summaries
from app.hevy.client import HevyClient

log = logging.getLogger(__name__)

T = TypeVar("T")

_CACHE_TTL_SECONDS = 600.0
_cache: dict[str, tuple[float, object]] = {}


def clear_cache() -> None:
    _cache.clear()


def _cached(key: str, load: Callable[[], T]) -> T:
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is not None and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]  # type: ignore[return-value]
    value = load()
    _cache[key] = (now, value)
    return value


def _fetch_workouts() -> list[dict]:
    with HevyClient() as c:
        workouts = list(c.iter_workouts())
    log.info("fetched %d workouts from Hevy", len(workouts))
    return workouts


def _fetch_routines() -> list[dict]:
    with HevyClient() as c:
        return list(c.iter_routines())


def _fetch_exercise_templates() -> list[dict]:
    with HevyClient() as c:
        return list(c.iter_exercise_templates())


def _build_template_by_title() -> dict[str, dict]:
    return {(t.get("title") or "").strip().lower(): t
            for t in _cached("exercise_templates", _fetch_exercise_templates)}


def exercise_template_by_title() -> dict[str, dict]:
    """Lowercase exercise title -> Hevy exercise template (muscle group,
    equipment). The Hevy API has no exercise images — this is the closest
    available metadata for a visual stand-in in the UI."""
    return _cached("exercise_templates_by_title", _build_template_by_title)


def all_workouts() -> list[dict]:
    """Every logged workout, newest first (Hevy's order)."""
    return _cached("workouts", _fetch_workouts)


def tracked_routines() -> list[dict]:
    """The configured routines (CLAUDE.md five), in config order."""
    by_title = {(r.get("title") or "").strip().lower(): r
                for r in _cached("routines", _fetch_routines)}
    found: list[dict] = []
    for title in get_settings().hevy_routines:
        r = by_title.get(title.lower())
        if r is None:
            log.warning("configured routine %r not found in Hevy", title)
        else:
            found.append(r)
    return found


def working_weights() -> list[Exercise]:
    """Max non-warmup logged weight per exercise across the tracked routines."""
    return normalize.derive_working_weights(all_workouts())


def routine_summaries() -> list[str]:
    return [summaries.routine_summary(r) for r in tracked_routines()]


def recent_workout_summaries(limit: int = 5) -> list[str]:
    tracked = [w for w in all_workouts() if normalize.is_tracked(w)]
    return [summaries.workout_summary(w) for w in tracked[:limit]]
