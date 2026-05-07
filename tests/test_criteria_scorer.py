"""Unit tests for ``mem0.memory.criteria_scorer.CriteriaScorer``.

The scorer is a pure LLM-driven re-ranker: it takes vector hits, asks the LLM
to score each one against N user-defined criteria with weights, and re-sorts
by the weighted average. These tests pin the math, the JSON-parse edge cases,
and the failure-mode behaviours.
"""

from __future__ import annotations

from typing import Any, List
from unittest.mock import MagicMock

import pytest

from mem0.configs.criteria import CriterionConfig
from mem0.memory.criteria_scorer import CriteriaScorer


def _llm_with_responses(responses: List[str]) -> Any:
    fake = MagicMock()
    fake.generate_response.side_effect = list(responses)
    return fake


def _docs(*items):
    return [{"id": str(i), "memory": text, "score": score} for i, (text, score) in enumerate(items)]


class TestWeightedAverage:
    def test_two_criteria_weighted_average(self):
        """``criteria_score = sum(score * weight) / sum(weight)``."""
        criteria = [
            CriterionConfig(name="joy", description="positive emotion", weight=3),
            CriterionConfig(name="curiosity", description="inquisitive", weight=1),
        ]
        # joy=0.8, curiosity=0.2 → (0.8*3 + 0.2*1) / 4 = 0.65
        # joy=0.1, curiosity=0.9 → (0.1*3 + 0.9*1) / 4 = 0.30
        llm = _llm_with_responses([
            '{"joy": 0.8, "curiosity": 0.2}',
            '{"joy": 0.1, "curiosity": 0.9}',
        ])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5), ("b", 0.7)))
        assert [d["id"] for d in result] == ["0", "1"]
        assert result[0]["criteria_score"] == pytest.approx(0.65)
        assert result[1]["criteria_score"] == pytest.approx(0.30)

    def test_results_are_resorted_by_criteria_score(self):
        """Even when the input is in vector-score order, output follows weighted criteria."""
        criteria = [CriterionConfig(name="urgency", description="urgent", weight=1)]
        # Doc 0 has higher vector score but lower urgency
        llm = _llm_with_responses(['{"urgency": 0.1}', '{"urgency": 0.9}'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.9), ("b", 0.2)))
        assert [d["id"] for d in result] == ["1", "0"]

    def test_equal_weights_simple_average(self):
        criteria = [
            CriterionConfig(name="joy", description="positive", weight=1),
            CriterionConfig(name="urgency", description="urgent", weight=1),
        ]
        llm = _llm_with_responses(['{"joy": 0.6, "urgency": 0.4}'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] == pytest.approx(0.5)


class TestParseEdgeCases:
    def test_codeblock_wrapped_response(self):
        criteria = [CriterionConfig(name="joy", description="positive")]
        llm = _llm_with_responses(['```json\n{"joy": 0.5}\n```'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] == pytest.approx(0.5)

    def test_json_with_surrounding_prose(self):
        """The scorer extracts the first JSON object from prose-wrapped responses."""
        criteria = [CriterionConfig(name="joy", description="positive")]
        llm = _llm_with_responses(['Sure! Here is your score: {"joy": 0.3}. Hope that helps.'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] == pytest.approx(0.3)

    def test_invalid_json_keeps_original_position(self):
        """When the LLM returns garbage, criteria_score is None and we fall back to semantic."""
        criteria = [CriterionConfig(name="joy", description="positive")]
        llm = _llm_with_responses(["not json at all"])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] is None
        # Falls back to semantic score for sort key — sole doc, just verify it's there
        assert result[0]["score"] == 0.5

    def test_missing_criterion_uses_fallback(self):
        """If the LLM drops a criterion from the JSON, fall back to 0.5 for that key."""
        criteria = [
            CriterionConfig(name="joy", description="positive", weight=3),
            CriterionConfig(name="curiosity", description="inquisitive", weight=1),
        ]
        # joy=0.9 returned, curiosity missing → 0.5 fallback. (0.9*3 + 0.5*1)/4 = 0.8
        llm = _llm_with_responses(['{"joy": 0.9}'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] == pytest.approx(0.8)

    def test_score_clamped_to_unit_interval(self):
        criteria = [CriterionConfig(name="joy", description="positive")]
        llm = _llm_with_responses(['{"joy": 1.5}'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] == 1.0

    def test_non_numeric_score_uses_fallback(self):
        criteria = [CriterionConfig(name="joy", description="positive")]
        llm = _llm_with_responses(['{"joy": "high"}'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] == pytest.approx(0.5)

    def test_llm_exception_keeps_doc_with_no_score(self):
        criteria = [CriterionConfig(name="joy", description="positive")]
        fake = MagicMock()
        fake.generate_response.side_effect = RuntimeError("LLM is on fire")
        scorer = CriteriaScorer(fake, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_score"] is None


class TestScorerLifecycle:
    def test_empty_documents_passthrough(self):
        criteria = [CriterionConfig(name="joy", description="positive")]
        llm = _llm_with_responses([])
        scorer = CriteriaScorer(llm, criteria)
        assert scorer.score("q", []) == []
        llm.generate_response.assert_not_called()

    def test_empty_criteria_rejected_at_init(self):
        with pytest.raises(ValueError, match="at least one"):
            CriteriaScorer(MagicMock(), [])

    def test_breakdown_attached_to_result(self):
        criteria = [
            CriterionConfig(name="joy", description="positive"),
            CriterionConfig(name="urgency", description="urgent"),
        ]
        llm = _llm_with_responses(['{"joy": 0.6, "urgency": 0.4}'])
        scorer = CriteriaScorer(llm, criteria)
        result = scorer.score("q", _docs(("a", 0.5)))
        assert result[0]["criteria_breakdown"] == {"joy": 0.6, "urgency": 0.4}

    def test_user_prompt_contains_criteria_descriptions(self):
        criteria = [CriterionConfig(name="joy", description="positive emotion")]
        llm = _llm_with_responses(['{"joy": 0.5}'])
        scorer = CriteriaScorer(llm, criteria)
        scorer.score("My query", _docs(("memory text", 0.5)))
        call_messages = llm.generate_response.call_args.kwargs["messages"]
        user_msg = call_messages[1]["content"]
        assert "joy: positive emotion" in user_msg
        assert "My query" in user_msg
        assert "memory text" in user_msg
