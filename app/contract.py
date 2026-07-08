"""Shared Data Contract (CLAUDE.md §3) — the shape every module speaks."""

from typing import Literal

from pydantic import BaseModel

Source = Literal["nippard", "hevy", "coaching"]


class Exercise(BaseModel):
    """One exercise prescription or logged entry.

    `weight` is the working weight in lb (max logged weight for Hevy data —
    never a 1RM). `reps`, `rpe`, and `rest` stay strings because programs use
    ranges like "8-10" or "2-3 min".
    """

    exercise: str
    sets: int
    reps: str
    rpe: str
    rest: str
    weight: float | None = None
    unit: Literal["lb"] = "lb"
    source: Source
    notes: str | None = None
