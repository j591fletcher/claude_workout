"""Unit tests for app/hevy/insights.py — reuses the _set()/_workout() fixture
builders from test_hevy.py, which mirror the confirmed live Hevy schema."""

import datetime as dt

import pytest

from app.hevy import insights
from app.hevy.normalize import kg_to_lb
from tests.test_hevy import _set, _workout


@pytest.fixture(autouse=True)
def _no_real_hevy_template_fetch(monkeypatch):
    # _with_muscle_meta() calls service.exercise_template_by_title(), which
    # would otherwise hit the real Hevy API on first use in any test here.
    monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {})


class TestStreakWeeks:
    def test_consecutive_weeks_including_current(self):
        today = dt.date(2026, 7, 15)  # Wednesday
        workouts = [_workout("Push", "2026-07-14", []),
                    _workout("Push", "2026-07-07", []),
                    _workout("Push", "2026-06-30", [])]
        assert insights._streak_weeks(workouts, today) == 3

    def test_empty_current_week_does_not_break_streak(self):
        today = dt.date(2026, 7, 15)
        workouts = [_workout("Push", "2026-07-07", []),
                    _workout("Push", "2026-06-30", [])]
        assert insights._streak_weeks(workouts, today) == 2

    def test_gap_week_breaks_streak(self):
        today = dt.date(2026, 7, 15)
        # current week logged, last week missing, two weeks ago logged
        workouts = [_workout("Push", "2026-07-14", []),
                    _workout("Push", "2026-06-30", [])]
        assert insights._streak_weeks(workouts, today) == 1

    def test_no_workouts_is_zero_streak(self):
        assert insights._streak_weeks([], dt.date(2026, 7, 15)) == 0


class TestRecentPrs:
    def test_excludes_maxes_older_than_30_days(self):
        today = dt.date(2026, 7, 15)
        workouts = [
            _workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(60, 8)])]),
            _workout("Push", "2026-05-01", [("Squat (Barbell)", [_set(100, 5)])]),
        ]
        names = {e.exercise for e in insights._recent_prs(workouts, today)}
        assert "Bench Press (Barbell)" in names
        assert "Squat (Barbell)" not in names

    def test_ties_go_to_the_more_recent_session(self):
        # newest-first order matters: same max weight hit twice, newest wins
        today = dt.date(2026, 7, 15)
        workouts = [
            _workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(65, 4)])]),
            _workout("Push", "2026-07-01", [("Bench Press (Barbell)", [_set(65, 8)])]),
        ]
        (e,) = insights._recent_prs(workouts, today)
        assert e.reps == "4"  # the newer session's rep count, not the older tie


class TestExerciseHistory:
    def test_orders_oldest_to_newest_and_computes_volume(self, monkeypatch):
        workouts = [
            _workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(65, 5)])]),
            _workout("Push", "2026-07-03", [("Bench Press (Barbell)", [_set(60, 8)])]),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        points = insights.exercise_history("Bench Press (Barbell)")
        assert [p.date for p in points] == ["2026-07-03", "2026-07-10"]
        assert points[0].volume_lb == kg_to_lb(60) * 8
        assert points[1].top_weight_lb == kg_to_lb(65)

    def test_bodyweight_session_has_no_weight_or_volume(self, monkeypatch):
        workouts = [_workout("New abs", "2026-07-10", [("Ab Wheel", [_set(None, 12)])])]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        (point,) = insights.exercise_history("Ab Wheel")
        assert point.top_weight_lb is None
        assert point.volume_lb is None

    def test_zero_weight_kg_treated_as_bodyweight(self, monkeypatch):
        workouts = [_workout("New abs", "2026-07-10",
                             [("Decline Reverse Crunch", [_set(0, 12)])])]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        (point,) = insights.exercise_history("Decline Reverse Crunch")
        assert point.top_weight_lb is None
        assert point.volume_lb is None

    def test_unknown_name_returns_none(self, monkeypatch):
        monkeypatch.setattr(insights.service, "all_workouts", lambda: [])
        assert insights.exercise_history("Nonexistent Exercise") is None

    def test_case_insensitive_lookup(self, monkeypatch):
        workouts = [_workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(60, 5)])])]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        assert insights.exercise_history("bench press (barbell)") is not None


class TestWorkoutFeed:
    def test_tracked_flag_and_pagination(self, monkeypatch):
        workouts = [
            _workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(65, 5)])]),
            _workout("Old Untracked Routine", "2026-05-01", [("Something", [_set(50, 5)])]),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        page1 = insights.workout_feed(limit=1, offset=0)
        assert len(page1) == 1
        assert page1[0].title == "Push"
        assert page1[0].tracked is True
        page2 = insights.workout_feed(limit=1, offset=1)
        assert page2[0].title == "Old Untracked Routine"
        assert page2[0].tracked is False


class TestExerciseNames:
    def test_counts_once_per_workout_even_if_listed_twice(self, monkeypatch):
        w = {"start_time": "2026-07-10T12:00:00+00:00", "exercises": [
            {"title": "Bench Press (Barbell)", "sets": [_set(60, 5)]},
            {"title": "bench press (barbell)", "sets": [_set(65, 5)]},
        ]}
        monkeypatch.setattr(insights.service, "all_workouts", lambda: [w])
        (n,) = insights.exercise_names()
        assert n.sessions == 1

    def test_sorted_by_sessions_descending(self, monkeypatch):
        workouts = [
            _workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(60, 5)])]),
            _workout("Push", "2026-07-03", [("Bench Press (Barbell)", [_set(60, 5)]),
                                            ("Overhead Press (Barbell)", [_set(40, 5)])]),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        names = insights.exercise_names()
        assert names[0].name == "Bench Press (Barbell)"
        assert names[0].sessions == 2

    def test_last_done_is_most_recent_and_casing_matches_it(self, monkeypatch):
        workouts = [
            _workout("Push", "2026-07-10", [("bench press (barbell)", [_set(60, 5)])]),
            _workout("Push", "2026-07-03", [("Bench Press (Barbell)", [_set(55, 5)])]),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        (n,) = insights.exercise_names()
        assert n.last_done == "2026-07-10"
        assert n.name == "bench press (barbell)"  # newest-first: most recent casing wins


class TestDashboardStats:
    def test_excludes_untracked_workouts_from_prs_but_counts_them_in_total(self, monkeypatch):
        today_str = dt.date.today().isoformat()
        workouts = [
            _workout("Push", today_str, [("Bench Press (Barbell)", [_set(60, 5)])]),
            _workout("Old Untracked Routine", today_str, [("Deadlift (Barbell)", [_set(200, 1)])]),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        stats = insights.dashboard_stats()
        assert stats.total_workouts == 2
        assert stats.last_workout.title == "Push"
        names = {e.exercise for e in stats.recent_prs}
        assert "Bench Press (Barbell)" in names
        assert "Deadlift (Barbell)" not in names

    def test_no_workouts_gives_empty_stats(self, monkeypatch):
        monkeypatch.setattr(insights.service, "all_workouts", lambda: [])
        stats = insights.dashboard_stats()
        assert stats.total_workouts == 0
        assert stats.last_workout is None
        assert stats.streak_weeks == 0
        assert stats.recent_prs == []


class TestCalendarDays:
    def test_one_entry_per_workout_with_tracked_flag(self, monkeypatch):
        workouts = [
            _workout("Push", "2026-07-10", []),
            _workout("Old Untracked Routine", "2026-05-01", []),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        days = insights.calendar_days()
        assert [(d.date, d.title, d.tracked) for d in days] == [
            ("2026-07-10", "Push", True),
            ("2026-05-01", "Old Untracked Routine", False),
        ]


class TestWorkoutsOn:
    def test_returns_all_workouts_on_that_date(self, monkeypatch):
        workouts = [
            _workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(60, 5)])]),
            _workout("Abs (extra)", "2026-07-10", [("Ab Wheel", [_set(None, 12)])]),
            _workout("Pull", "2026-07-09", [("Lat Pulldown (Cable)", [_set(50, 8)])]),
        ]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        result = insights.workouts_on("2026-07-10")
        assert {w.title for w in result} == {"Push", "Abs (extra)"}

    def test_rest_day_returns_none(self, monkeypatch):
        monkeypatch.setattr(insights.service, "all_workouts", lambda: [])
        assert insights.workouts_on("2026-07-10") is None


class TestExerciseWithMeta:
    def test_attaches_muscle_group_and_equipment_when_template_matches(self, monkeypatch):
        workouts = [_workout("Push", "2026-07-10", [("Bench Press (Barbell)", [_set(60, 5)])])]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {
            "bench press (barbell)": {"primary_muscle_group": "chest", "equipment": "barbell"},
        })
        (item,) = insights.workout_feed()
        (e,) = item.exercises
        assert e.muscle_group == "chest"
        assert e.equipment == "barbell"

    def test_none_when_no_template_match(self, monkeypatch):
        workouts = [_workout("Push", "2026-07-10", [("Some Custom Move", [_set(60, 5)])])]
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {})
        (item,) = insights.workout_feed()
        (e,) = item.exercises
        assert e.muscle_group is None
        assert e.equipment is None


class TestRoutinesFull:
    def test_uses_routine_to_exercises(self, monkeypatch):
        routine = {"title": "Push", "exercises": [{
            "index": 0, "title": "Bench Press (Barbell)", "notes": None,
            "rest_seconds": 120,
            "sets": [_set(rep_range={"start": 6, "end": 8})],
        }]}
        monkeypatch.setattr(insights.service, "tracked_routines", lambda: [routine])
        monkeypatch.setattr(insights.service, "all_workouts", lambda: [])
        monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {})
        (r,) = insights.routines_full()
        assert r.title == "Push"
        assert r.exercises[0].exercise == "Bench Press (Barbell)"
        assert r.exercises[0].reps == "6-8"

    def test_last_performed_and_sessions_last_30d(self, monkeypatch):
        today_str = dt.date.today().isoformat()
        old_str = (dt.date.today() - dt.timedelta(days=45)).isoformat()
        routine = {"title": "Push", "exercises": []}
        workouts = [
            _workout("Push", today_str, []),
            _workout("Push", old_str, []),
            _workout("Pull", today_str, []),
        ]
        monkeypatch.setattr(insights.service, "tracked_routines", lambda: [routine])
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {})
        (r,) = insights.routines_full()
        assert r.last_performed == today_str
        assert r.sessions_last_30d == 1  # the 45-day-old session falls outside the window

    def test_never_performed_routine_has_none_last_performed(self, monkeypatch):
        routine = {"title": "New abs", "exercises": []}
        monkeypatch.setattr(insights.service, "tracked_routines", lambda: [routine])
        monkeypatch.setattr(insights.service, "all_workouts", lambda: [])
        monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {})
        (r,) = insights.routines_full()
        assert r.last_performed is None
        assert r.sessions_last_30d == 0

    def test_sorted_most_recently_performed_first(self, monkeypatch):
        today_str = dt.date.today().isoformat()
        old_str = (dt.date.today() - dt.timedelta(days=10)).isoformat()
        routines = [{"title": "Legs", "exercises": []}, {"title": "Push", "exercises": []}]
        workouts = [_workout("Push", today_str, []), _workout("Legs", old_str, [])]
        monkeypatch.setattr(insights.service, "tracked_routines", lambda: routines)
        monkeypatch.setattr(insights.service, "all_workouts", lambda: workouts)
        monkeypatch.setattr(insights.service, "exercise_template_by_title", lambda: {})
        result = insights.routines_full()
        assert [r.title for r in result] == ["Push", "Legs"]
