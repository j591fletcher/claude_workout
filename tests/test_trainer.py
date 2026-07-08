"""Unit tests for Module A: system-prompt composition, the no-LLM-configured
fallback, and graceful handling when the LLM backend is unreachable. No live
network calls — get_llm_client and Module C are mocked/monkeypatched."""

from unittest.mock import patch

from app.contract import Exercise
from app.hevy.client import HevyError
from app.llm import LLMUnavailable
from app.trainer.service import Trainer


class FakeRetriever:
    def __init__(self, hits, all_programs=frozenset()):
        self._hits = hits
        self._all_programs = set(all_programs)
        self.last_call = None

    def retrieve(self, question, where=None, top_k=None):
        self.last_call = (question, where)
        return self._hits

    def distinct_programs(self):
        return self._all_programs


class FakeLLM:
    def __init__(self, response="ok", raises=None):
        self._response = response
        self._raises = raises
        self.last_call = None

    def complete(self, system, message):
        self.last_call = (system, message)
        if self._raises:
            raise self._raises
        return self._response


def _hit(text="Back Squat: 3 working sets x 6 reps", chunk_type="day_table"):
    return {"text": text, "metadata": {"chunk_type": chunk_type, "program": "Fundamentals"}}


def _trainer(hits=(), all_programs=frozenset()):
    return Trainer(retriever=FakeRetriever(list(hits), all_programs))


def _mock_hevy(mock_hevy, weights=(), routines=(), recent=()):
    mock_hevy.working_weights.return_value = list(weights)
    mock_hevy.routine_summaries.return_value = list(routines)
    mock_hevy.recent_workout_summaries.return_value = list(recent)


class TestNoLLMConfiguredFallback:
    def test_returns_without_calling_llm(self):
        t = _trainer(hits=[_hit()])
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=None):
            _mock_hevy(mock_hevy)
            result = t.chat("What's my squat programming?")
        assert "No LLM backend configured" in result.answer

    def test_sources_still_returned(self):
        t = _trainer(hits=[_hit()])
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=None):
            _mock_hevy(mock_hevy)
            result = t.chat("What's my squat programming?")
        assert result.sources == [{"chunk_type": "day_table", "program": "Fundamentals"}]


class TestLLMUnreachableFallback:
    def test_reports_instead_of_crashing(self):
        t = _trainer(hits=[_hit()])
        fake_llm = FakeLLM(raises=LLMUnavailable("Ollama at http://x:11434 unreachable"))
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=fake_llm):
            _mock_hevy(mock_hevy)
            result = t.chat("test")
        assert "unreachable" in result.answer
        assert "no coaching" in result.answer

    def test_hevy_error_also_reported_not_fatal(self):
        t = _trainer(hits=[])
        fake_llm = FakeLLM(response="ok")
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=fake_llm):
            mock_hevy.working_weights.side_effect = HevyError("boom", status=502)
            result = t.chat("test")
        assert result.answer == "ok"  # LLM still runs; Hevy context degrades gracefully


class TestSystemPromptComposition:
    def _call_and_capture_system(self, hits, weights, routines, recent):
        t = _trainer(hits=hits)
        fake_llm = FakeLLM(response="ok")
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=fake_llm):
            _mock_hevy(mock_hevy, weights, routines, recent)
            t.chat("test question")
        return fake_llm.last_call[0]

    def test_includes_trainer_identity(self):
        system = self._call_and_capture_system([_hit()], [], [], [])
        assert "You are a personal trainer AI" in system

    def test_includes_retrieved_program_excerpts_labeled_by_program(self):
        system = self._call_and_capture_system(
            [_hit(text="UNIQUE_SQUAT_TEXT_MARKER")], [], [], [])
        assert "UNIQUE_SQUAT_TEXT_MARKER" in system
        assert "program: Fundamentals" in system

    def test_no_hits_says_so_instead_of_inventing(self):
        system = self._call_and_capture_system([], [], [], [])
        assert "no matching program excerpts retrieved" in system

    def test_includes_hevy_working_weights_labeled_not_1rm(self):
        weights = [Exercise(exercise="Bench Press (Barbell)", sets=4, reps="6-7",
                            rpe="-", rest="-", weight=175.0, source="hevy")]
        system = self._call_and_capture_system([], weights, [], [])
        assert "Bench Press (Barbell): 175 lb" in system
        assert "NOT 1RMs" in system

    def test_hevy_unavailable_is_reported_in_context(self):
        t = _trainer(hits=[])
        fake_llm = FakeLLM(response="ok")
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=fake_llm):
            mock_hevy.working_weights.side_effect = HevyError("boom", status=502)
            t.chat("test")
        assert "Hevy data unavailable" in fake_llm.last_call[0]


class TestUngroundedProgramMentionFlag:
    """Regression coverage for the live-verify finding: qwen2.5:14b named a
    real Nippard program ("Fundamentals Hypertrophy Program") that was never
    part of the retrieved sources. See flag_ungrounded_programs in query.py."""

    def _chat(self, answer_text, hits, all_programs):
        t = _trainer(hits=hits, all_programs=all_programs)
        fake_llm = FakeLLM(response=answer_text)
        with patch("app.trainer.service.hevy") as mock_hevy, \
             patch("app.trainer.service.get_llm_client", return_value=fake_llm):
            _mock_hevy(mock_hevy)
            return t.chat("test")

    def test_flags_a_named_program_not_among_the_sources(self):
        hits = [_hit()]  # metadata program="Fundamentals"
        result = self._chat(
            "According to the Fundamentals Hypertrophy Program, do 5x5.",
            hits, all_programs={"Fundamentals", "Fundamentals Hypertrophy Program"},
        )
        assert "Grounding check" in result.answer
        assert "Fundamentals Hypertrophy Program" in result.answer

    def test_no_flag_when_only_cited_programs_are_mentioned(self):
        hits = [_hit()]  # metadata program="Fundamentals"
        result = self._chat("From your Fundamentals program, do 3x8.", hits,
                            all_programs={"Fundamentals", "Other Program"})
        assert "Grounding check" not in result.answer

    def test_no_flag_when_program_not_mentioned_at_all(self):
        hits = [_hit()]
        result = self._chat("Do 3 sets of 8.", hits,
                            all_programs={"Fundamentals", "Other Program"})
        assert "Grounding check" not in result.answer

    def test_flags_literal_nippard_mention_with_zero_sources(self):
        # The exact live-verify failure: model says "Nippard" with no retrieved
        # excerpts at all. Program names never contain "Nippard" (stripped at
        # ingest), so this mention is provably ungrounded.
        result = self._chat(
            "Regarding technique cues from your Nippard program: brace your core.",
            hits=[], all_programs={"Fundamentals Hypertrophy Program"},
        )
        assert "Grounding check" in result.answer
        assert "Nippard" in result.answer
