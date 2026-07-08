"""Unit tests for Module C: kg->lb, normalization, working-weight derivation,
and summary formatting. Fixtures mirror the live schema confirmed at Checkpoint 2."""

import pytest

from app.hevy import normalize, summaries
from app.hevy.normalize import derive_working_weights, kg_to_lb

ROUTINES = ("Push", "Pull", "New abs", "Upper Mix",
            "Legs (Quads, Hamstrings, Glutes, Calves)")


def _set(weight_kg=None, reps=None, rpe=None, set_type="normal", rep_range=None):
    return {"index": 0, "type": set_type, "weight_kg": weight_kg, "reps": reps,
            "rpe": rpe, "distance_meters": None, "duration_seconds": None,
            "custom_metric": None,
            **({"rep_range": rep_range} if rep_range is not None else {})}


def _workout(title, date, exercises):
    return {"id": "w1", "title": title, "start_time": f"{date}T17:00:00+00:00",
            "end_time": f"{date}T18:00:00+00:00", "description": "",
            "exercises": [{"index": i, "title": name, "notes": "", "sets": sets}
                          for i, (name, sets) in enumerate(exercises)]}


class TestKgToLb:
    def test_conversion_rounds_to_half_lb(self):
        assert kg_to_lb(100) == 220.5   # 220.46 -> 220.5
        assert kg_to_lb(60) == 132.5    # 132.28 -> 132.5
        assert kg_to_lb(2.5) == 5.5     # 5.51 -> 5.5

    def test_zero(self):
        assert kg_to_lb(0) == 0.0


class TestWorkoutToExercises:
    def test_maps_confirmed_field_names(self):
        w = _workout("Push", "2026-07-01",
                     [("Bench Press (Barbell)",
                       [_set(60, 8, 7.5), _set(60, 8), _set(62.5, 6)])])
        (e,) = normalize.workout_to_exercises(w)
        assert e.exercise == "Bench Press (Barbell)"
        assert e.sets == 3
        assert e.reps == "6-8"
        assert e.rpe == "7.5"
        assert e.weight == kg_to_lb(62.5)
        assert e.unit == "lb"
        assert e.source == "hevy"

    def test_warmups_excluded(self):
        w = _workout("Push", "2026-07-01",
                     [("Bench Press (Barbell)",
                       [_set(100, 5, set_type="warmup"), _set(60, 8)])])
        (e,) = normalize.workout_to_exercises(w)
        assert e.sets == 1
        assert e.weight == kg_to_lb(60)  # warmup 100kg ignored

    def test_bodyweight_exercise_has_null_weight(self):
        w = _workout("New abs", "2026-07-01", [("Ab Wheel", [_set(None, 12)])])
        (e,) = normalize.workout_to_exercises(w)
        assert e.weight is None
        assert e.reps == "12"

    def test_zero_weight_kg_treated_as_bodyweight(self):
        # some Hevy entries log weight_kg=0 instead of leaving it null
        w = _workout("New abs", "2026-07-01",
                     [("Decline Reverse Crunch", [_set(0, 12), _set(0, 12)])])
        (e,) = normalize.workout_to_exercises(w)
        assert e.weight is None


class TestRoutineToExercises:
    def test_rep_range_and_rest(self):
        routine = {"title": "Lower 2", "exercises": [{
            "index": 0, "title": "Hack Squat (Machine)", "notes": None,
            "rest_seconds": 135,
            "sets": [_set(set_type="warmup", rep_range={"start": 8, "end": 12}),
                     _set(rep_range={"start": 8, "end": 12}),
                     _set(rep_range={"start": 8, "end": 12})],
        }]}
        (e,) = normalize.routine_to_exercises(routine)
        assert e.sets == 2  # warmup set excluded
        assert e.reps == "8-12"
        assert e.rest == "2:15 min"


class TestDeriveWorkingWeights:
    def test_max_across_sessions_and_untracked_skipped(self):
        workouts = [
            _workout("Push", "2026-07-05", [("Bench Press (Barbell)", [_set(62.5, 6)])]),
            _workout("Push", "2026-06-28", [("Bench Press (Barbell)", [_set(65, 4)])]),
            # same exercise, heavier, but in an old untracked routine:
            _workout("Upper 1", "2026-05-01", [("Bench Press (Barbell)", [_set(80, 3)])]),
        ]
        (e,) = derive_working_weights(workouts, ROUTINES)
        assert e.weight == kg_to_lb(65)
        assert "2026-06-28" in (e.notes or "")

    def test_not_a_1rm_note_is_max_weight_not_estimate(self):
        # 60kg x 10 must NOT beat 65kg x 1 (no epley-style math)
        workouts = [_workout("Pull", "2026-07-01",
                             [("Barbell Row", [_set(60, 10), _set(65, 1)])])]
        (e,) = derive_working_weights(workouts, ROUTINES)
        assert e.weight == kg_to_lb(65)

    def test_routine_title_match_is_case_insensitive(self):
        workouts = [_workout("new ABS", "2026-07-01", [("Cable Crunch", [_set(40, 12)])])]
        assert len(derive_working_weights(workouts, ROUTINES)) == 1


class TestSummaries:
    def test_workout_summary_lift_log_format(self):
        w = _workout("Push", "2026-07-05",
                     [("Bench Press (Barbell)", [_set(62.5, 6, 8.0)])])
        text = summaries.workout_summary(w)
        assert text.splitlines()[0] == "[2026-07-05] — Push"
        assert "Bench Press (Barbell) | 1x6 | 138 lb | RPE 8 | -" in text
        assert text.splitlines()[-1].startswith("Session notes:")

    def test_bodyweight_rendered(self):
        w = _workout("New abs", "2026-07-05", [("Ab Wheel", [_set(None, 12)])])
        assert "Ab Wheel | 1x12 | bodyweight" in summaries.workout_summary(w)
