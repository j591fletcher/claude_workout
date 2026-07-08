import datetime
from pathlib import Path
from types import SimpleNamespace

from app.retriever.chunk import Chunk, chunk_guide, chunk_program, row_to_record
from app.retriever.extract import GuideSection, ProgramRow, unrange
from app.retriever.ingest import program_name_from_filename
from app.retriever.query import Retriever, _format_context


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


def test_chunk_guide_ids_unique_when_titles_repeat():
    # scanned guidebooks repeat generic headings (e.g. "Week") across many pages
    sections = [GuideSection(title="Week", text="x " * 40, first_page=i) for i in range(5)]
    chunks = chunk_guide(sections, "Some Program", "some_file")
    assert len({c.id for c in chunks}) == len(chunks) == 5


def test_format_context_labels_each_excerpt_with_its_own_program():
    hits = [{"text": "some text", "metadata": {"program": "Push", "chunk_type": "day_table"}},
            {"text": "other text", "metadata": {"program": "BTS", "chunk_type": "guide_section"}}]
    ctx = _format_context(hits)
    assert "program: Push" in ctx
    assert "program: BTS" in ctx


class _FakeStore:
    def __init__(self, hits):
        self._hits = hits

    def query(self, embedding, top_k, where):
        return self._hits


class _FakeEmbedder:
    def embed(self, texts):
        return [[0.0]] * len(texts)


def _retriever_with(hits, max_distance=0.45):
    r = Retriever.__new__(Retriever)  # bypass __init__: no real model/store needed
    r._settings = SimpleNamespace(top_k=8, retrieval_max_distance=max_distance)
    r._embedder = _FakeEmbedder()
    r._store = _FakeStore(hits)
    return r


def test_retrieve_drops_chunks_beyond_the_distance_threshold():
    hits = [{"text": "close match", "metadata": {}, "distance": 0.3},
            {"text": "garbled unrelated content", "metadata": {}, "distance": 0.6}]
    kept = _retriever_with(hits).retrieve("some question")
    assert [h["text"] for h in kept] == ["close match"]


def test_retrieve_keeps_everything_within_threshold():
    hits = [{"text": "a", "metadata": {}, "distance": 0.1},
            {"text": "b", "metadata": {}, "distance": 0.4}]
    kept = _retriever_with(hits).retrieve("some question")
    assert len(kept) == 2


def test_program_name_from_filename_strips_library_and_author_noise():
    p = Path("Fundamentals Hypertrophy Program (Jeff Nippard) (Z-Library).pdf")
    assert program_name_from_filename(p) == "Fundamentals Hypertrophy Program"


def test_program_name_from_filename_handles_underscored_compressed_names():
    p = Path("The_Bodybuilding_Transformation_System_-_Beginner_compressed.pdf")
    assert program_name_from_filename(p) == "The Bodybuilding Transformation System Beginner"


def test_program_name_from_filename_splits_camel_case():
    p = Path("JeffNippardsUpperLowerStrengthandSizeProgram.pdf")
    name = program_name_from_filename(p)
    assert "Jeff" in name and "Upper" in name and "Program" in name
    assert " " in name  # not left as one unreadable blob


def test_program_name_from_filename_differs_across_files():
    a = program_name_from_filename(Path("Fundamentals Hypertrophy Program (Jeff Nippard).pdf"))
    b = program_name_from_filename(
        Path("The_Bodybuilding_Transformation_System_-_Beginner_compressed.pdf"))
    assert a != b
