"""Ad-hoc live check: derive real working weights and summaries from Hevy.
Not part of the app; delete or ignore after Phase 3 verification."""

import logging
import sys

from app.hevy import service

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO)


def main() -> None:
    ww = service.working_weights()
    print(f"--- WORKING WEIGHTS ({len(ww)} exercises) ---")
    for e in ww:
        weight = f"{e.weight} lb" if e.weight is not None else "bodyweight"
        print(f"{e.exercise:45s} {weight:>12s}  ({e.sets}x{e.reps}, {e.notes})")

    print()
    print("--- LATEST SESSION ---")
    latest = service.recent_workout_summaries(1)
    print(latest[0] if latest else "(none)")

    print()
    print("--- TRACKED ROUTINES ---")
    for s in service.routine_summaries():
        lines = s.splitlines()
        print(lines[0], "-", len(lines) - 1, "exercises")


if __name__ == "__main__":
    main()
