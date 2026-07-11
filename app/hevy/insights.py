"""Structured derivations over Hevy history for the web UI (Module C+).

Builds on app/hevy/service.py's cached all_workouts()/tracked_routines() and
app/hevy/normalize.py's contract-shaping helpers — no new caching here, and
the semantics (working sets only, weight_kg:0 == bodyweight, working weights
are max logged weight not a 1RM) all defer to normalize.py.

Scope: workout_feed/exercise_history cover ALL logged workouts (the app
visualizes everything imported, including pre-tracked-routine history).
recent_prs/streak reuse working-weight semantics — tracked routines only,
matching normalize.derive_working_weights.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel

from app.contract import Exercise
from app.hevy import service
from app.hevy.normalize import (
    is_tracked,
    kg_to_lb,
    routine_to_exercises,
    workout_date,
    workout_to_exercises,
    working_sets,
)

_PR_WINDOW_DAYS = 30


class ExerciseWithMeta(Exercise):
    """Exercise plus Hevy exercise-template metadata. The Hevy API has no
    exercise images — muscle_group/equipment is the closest available visual
    stand-in (rendered as a badge in the UI). None when a template lookup
    misses (e.g. a custom/renamed exercise)."""
    muscle_group: str | None = None
    equipment: str | None = None


class WorkoutFeedItem(BaseModel):
    date: str
    title: str
    tracked: bool
    description: str | None
    exercises: list[ExerciseWithMeta]


class CalendarDay(BaseModel):
    date: str
    title: str
    tracked: bool


class ExerciseSummary(BaseModel):
    name: str
    sessions: int
    last_done: str


class ExerciseHistoryPoint(BaseModel):
    date: str
    workout_title: str
    top_weight_lb: float | None
    sets: int
    reps: str
    rpe: str
    volume_lb: float | None


class LastWorkout(BaseModel):
    date: str
    title: str


class DashboardStats(BaseModel):
    total_workouts: int
    this_week: int
    last_workout: LastWorkout | None
    streak_weeks: int
    recent_prs: list[Exercise]


class RoutineFull(BaseModel):
    title: str
    exercises: list[ExerciseWithMeta]
    last_performed: str | None
    sessions_last_30d: int


def _parse_date(date_str: str) -> datetime.date:
    return datetime.date.fromisoformat(date_str)


def _week_start(d: datetime.date) -> datetime.date:
    return d - datetime.timedelta(days=d.weekday())  # Monday of that week


def _with_muscle_meta(exercises: list[Exercise]) -> list[ExerciseWithMeta]:
    templates = service.exercise_template_by_title()
    out: list[ExerciseWithMeta] = []
    for e in exercises:
        t = templates.get(e.exercise.strip().lower())
        out.append(ExerciseWithMeta(
            **e.model_dump(),
            muscle_group=t.get("primary_muscle_group") if t else None,
            equipment=t.get("equipment") if t else None,
        ))
    return out


def workout_feed(limit: int = 10, offset: int = 0) -> list[WorkoutFeedItem]:
    """Newest-first page of every logged workout (Hevy's own order)."""
    workouts = service.all_workouts()[offset:offset + limit]
    return [
        WorkoutFeedItem(
            date=workout_date(w),
            title=w.get("title") or "Workout",
            tracked=is_tracked(w),
            description=w.get("description") or None,
            exercises=_with_muscle_meta(workout_to_exercises(w)),
        )
        for w in workouts
    ]


def calendar_days() -> list[CalendarDay]:
    """One lightweight entry per logged workout across ALL history (no
    exercises) — powers the Home calendar view."""
    return [
        CalendarDay(date=workout_date(w), title=w.get("title") or "Workout", tracked=is_tracked(w))
        for w in service.all_workouts()
    ]


def workouts_on(date: str) -> list[WorkoutFeedItem] | None:
    """All workouts logged on an exact date (usually one, occasionally more
    on a double-session day). None if nothing was logged that day (caller
    maps that to a 404)."""
    matches = [w for w in service.all_workouts() if workout_date(w) == date]
    if not matches:
        return None
    return [
        WorkoutFeedItem(
            date=workout_date(w),
            title=w.get("title") or "Workout",
            tracked=is_tracked(w),
            description=w.get("description") or None,
            exercises=_with_muscle_meta(workout_to_exercises(w)),
        )
        for w in matches
    ]


def exercise_names() -> list[ExerciseSummary]:
    """Every exercise ever logged, most-trained first. Case-insensitive key,
    display uses the most recently logged casing (workouts arrive newest-first)."""
    agg: dict[str, dict] = {}
    for w in service.all_workouts():  # newest-first
        date = workout_date(w)
        seen_this_workout: set[str] = set()
        for ex in w.get("exercises", []):
            title = (ex.get("title") or "").strip()
            if not title:
                continue
            key = title.lower()
            if key in seen_this_workout:
                continue  # count each exercise once per workout
            seen_this_workout.add(key)
            entry = agg.get(key)
            if entry is None:
                agg[key] = {"name": title, "sessions": 1, "last_done": date}
            else:
                entry["sessions"] += 1
    return sorted((ExerciseSummary(**v) for v in agg.values()),
                  key=lambda e: e.sessions, reverse=True)


def exercise_history(name: str) -> list[ExerciseHistoryPoint] | None:
    """Per-session series for one exercise, oldest -> newest. None if the
    exercise name was never logged (caller maps that to a 404)."""
    key = name.strip().lower()
    points: list[ExerciseHistoryPoint] = []
    found = False
    for w in service.all_workouts():  # newest-first; reversed before return
        date = workout_date(w)
        for ex in w.get("exercises", []):
            if (ex.get("title") or "").strip().lower() != key:
                continue
            found = True
            sets = working_sets(ex)
            if not sets:
                continue
            # reuse workout_to_exercises' span/weight logic exactly, scoped
            # to just this one exercise entry
            (entry,) = workout_to_exercises({**w, "exercises": [ex]})
            weighted = [(s["weight_kg"], s["reps"]) for s in sets
                        if s.get("weight_kg") and s.get("reps") is not None]
            volume = (sum(kg_to_lb(wk) * reps for wk, reps in weighted)
                      if weighted else None)
            points.append(ExerciseHistoryPoint(
                date=date, workout_title=w.get("title") or "Workout",
                top_weight_lb=entry.weight, sets=entry.sets, reps=entry.reps,
                rpe=entry.rpe, volume_lb=volume,
            ))
    if not found:
        return None
    points.reverse()
    return points


def _streak_weeks(workouts: list[dict], today: datetime.date) -> int:
    weeks_with_workouts = {_week_start(_parse_date(workout_date(w)))
                            for w in workouts if workout_date(w)}
    cursor = _week_start(today)
    if cursor not in weeks_with_workouts:
        cursor -= datetime.timedelta(weeks=1)  # current week empty: doesn't break the streak yet
    streak = 0
    while cursor in weeks_with_workouts:
        streak += 1
        cursor -= datetime.timedelta(weeks=1)
    return streak


def _recent_prs(tracked_workouts: list[dict], today: datetime.date) -> list[Exercise]:
    """Same max-per-exercise loop as normalize.derive_working_weights (ties go
    to the more recent session since workouts arrive newest-first), filtered
    to maxes hit within the last _PR_WINDOW_DAYS days. Date is tracked as
    real data, never parsed back out of the notes string."""
    best: dict[str, tuple[float, Exercise, datetime.date]] = {}
    for w in tracked_workouts:  # newest-first
        date = _parse_date(workout_date(w))
        for entry in workout_to_exercises(w):
            if entry.weight is None:
                continue
            key = entry.exercise.lower()
            prev = best.get(key)
            if prev is None or entry.weight > prev[0]:
                best[key] = (entry.weight, entry, date)
    cutoff = today - datetime.timedelta(days=_PR_WINDOW_DAYS)
    recent = [e for _, e, d in best.values() if d >= cutoff]
    return sorted(recent, key=lambda e: e.exercise.lower())


def dashboard_stats() -> DashboardStats:
    workouts = service.all_workouts()  # newest-first
    tracked_workouts = [w for w in workouts if is_tracked(w)]
    today = datetime.date.today()
    week_start = _week_start(today)

    this_week = sum(1 for w in workouts
                     if workout_date(w) and _parse_date(workout_date(w)) >= week_start)

    last_workout = None
    if workouts:
        w0 = workouts[0]
        last_workout = LastWorkout(date=workout_date(w0), title=w0.get("title") or "Workout")

    return DashboardStats(
        total_workouts=len(workouts),
        this_week=this_week,
        last_workout=last_workout,
        streak_weeks=_streak_weeks(workouts, today),
        recent_prs=_recent_prs(tracked_workouts, today),
    )


def routines_full() -> list[RoutineFull]:
    """The five tracked routines, sorted most-recently-performed first (never
    performed sinks to the bottom), each with a 30-day session count and
    muscle-group/equipment metadata per exercise."""
    workouts = service.all_workouts()  # newest-first
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=_PR_WINDOW_DAYS)

    out: list[RoutineFull] = []
    for r in service.tracked_routines():
        title = r.get("title") or "Routine"
        key = title.strip().lower()
        matching = [w for w in workouts if (w.get("title") or "").strip().lower() == key]
        last_performed = workout_date(matching[0]) if matching else None
        sessions_last_30d = sum(
            1 for w in matching
            if workout_date(w) and _parse_date(workout_date(w)) >= cutoff
        )
        out.append(RoutineFull(
            title=title,
            exercises=_with_muscle_meta(routine_to_exercises(r)),
            last_performed=last_performed,
            sessions_last_30d=sessions_last_30d,
        ))
    out.sort(key=lambda r: r.last_performed or "", reverse=True)
    return out
