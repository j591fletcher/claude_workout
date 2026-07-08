import datetime

from app.retriever.chunk import Chunk, chunk_program, row_to_record
from app.retriever.extract import ProgramRow, unrange


def _row(**over) -> ProgramRow:
    base = dict(
        program="Intermediate-Advanced", block="Foundation", week=1,
        day="Upper (Strength Focus)", exercise="45° Incline Barbell Press",
        working_sets=2, reps="6-8", rpe_early="~6-7", rpe_last="~7-8",
        rest="3-5 min", intensity=None, warmup_sets="2-3",
        substitutions=["45° Incline DB Press"], notes="1 second pause",
    )
    base.update(over)
    return ProgramRow(**base)


def test_unrange_reverses_excel_date_coercion():
    assert unrange(datetime.datetime(2025, 8, 10)) == "8-10"
    assert unrange(datetime.datetime(2025, 12, 15)) == "12-15"
    assert unrange("15-20") == "15-20"
    assert unrange(3) == "3"
    assert unrange(None) is None
    assert unrange("  ") is None


def test_row_to_record_matches_contract():
    rec = row_to_record(_row())
    assert rec.source == "nippard"
    assert rec.unit == "lb"
    assert rec.weight is None
    assert rec.sets == 2
    assert rec.reps == "6-8"
    assert "warm-up sets: 2-3" in rec.notes
    assert "subs: 45° Incline DB Press" in rec.notes
    assert "1 second pause" in rec.notes


def test_chunk_ids_are_deterministic_and_unique():
    rows = [_row(), _row(exercise="Pec Deck"), _row(week=2)]
    a, b = chunk_program(rows), chunk_program(rows)
    assert [c.id for c in a] == [c.id for c in b]  # idempotent re-ingestion
    assert len({c.id for c in a}) == len(a)  # no collisions


def test_day_table_groups_all_exercises_of_a_day():
    rows = [_row(), _row(exercise="Pec Deck")]
    tables = [c for c in chunk_program(rows) if c.metadata["chunk_type"] == "day_table"]
    assert len(tables) == 1
    assert "45° Incline Barbell Press" in tables[0].text
    assert "Pec Deck" in tables[0].text


def test_chunk_metadata_is_scalar_only():
    for chunk in chunk_program([_row()]):
        assert isinstance(chunk, Chunk)
        for v in chunk.metadata.values():
            assert isinstance(v, (str, int, float, bool))
