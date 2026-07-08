"""Human-verifiable summaries of Hevy data.

Two audiences: the user (to confirm the app understood their routines — the
trainer prompt's verification step) and the trainer itself (LIFT LOG format
from prompts/trainer.md: `Exercise | Sets x Reps | Weight | RPE | Notes`).
"""

from __future__ import annotations

from app.hevy.normalize import (
    routine_to_exercises,
    workout_date,
    workout_to_exercises,
)


def _weight_str(weight: float | None) -> str:
    if weight is None:
        return "bodyweight"
    return f"{weight:g} lb"


def workout_summary(workout: dict) -> str:
    """One logged session in the trainer's LIFT LOG format."""
    lines = [f"[{workout_date(workout)}] — {workout.get('title', 'Workout')}"]
    for e in workout_to_exercises(workout):
        lines.append(f"{e.exercise} | {e.sets}x{e.reps} | {_weight_str(e.weight)}"
                     f" | RPE {e.rpe} | {e.notes or '-'}")
    lines.append(f"Session notes: {workout.get('description') or '-'}")
    return "\n".join(lines)


def routine_summary(routine: dict) -> str:
    """One routine template: what the app believes the plan is."""
    lines = [f"{routine.get('title', 'Routine')}"]
    for e in routine_to_exercises(routine):
        lines.append(f"{e.exercise} | {e.sets}x{e.reps} | rest {e.rest}"
                     f"{' | ' + e.notes if e.notes else ''}")
    return "\n".join(lines)
