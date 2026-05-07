"""Memory.search criteria-based scoring integration.

Verifies that:
- ``Memory.search`` runs the criteria scorer after the rerank step when criteria
  are configured (auto-enabled).
- ``use_criteria=False`` opts out for a single call even when criteria are
  configured.
- Per-call ``criteria=[...]`` builds a transient scorer.
- ``use_criteria=True`` with nothing configured raises.
- ``AsyncMemory.search`` mirrors the sync wiring.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from mem0 import AsyncMemory, Memory
from mem0.configs.criteria import CriterionConfig


def _build_memory(criteria=None) -> Memory:
    """Build a Memory instance with mocked heavy deps + a fake LLM."""
    with patch.object(Memory, "__init__", return_value=None):
        m = Memory()

    fake_llm = MagicMock()
    m.llm = fake_llm
    m.vector_store = MagicMock()
    m.api_version = "v1.1"
    m.reranker = None
    m.criteria_scorer = None
    cfg = MagicMock()
    cfg.retrieval_criteria = criteria
    m.config = cfg

    if criteria:
        from mem0.memory.criteria_scorer import CriteriaScorer

        m.criteria_scorer = CriteriaScorer(fake_llm, criteria)

    # Bypass vector-store retrieval — return a fixed candidate list for all tests.
    m._search_vector_store = MagicMock(
        return_value=[
            {"id": "calm", "memory": "rainy day, feeling heavy", "score": 0.6},
            {"id": "joy", "memory": "feeling great today", "score": 0.5},
        ]
    )
    m._has_advanced_operators = MagicMock(return_value=False)
    return m


def _build_async_memory(criteria=None) -> AsyncMemory:
    with patch.object(AsyncMemory, "__init__", return_value=None):
        m = AsyncMemory()

    fake_llm = MagicMock()
    m.llm = fake_llm
    m.vector_store = MagicMock()
    m.api_version = "v1.1"
    m.reranker = None
    m.criteria_scorer = None
    cfg = MagicMock()
    cfg.retrieval_criteria = criteria
    m.config = cfg

    if criteria:
        from mem0.memory.criteria_scorer import CriteriaScorer

        m.criteria_scorer = CriteriaScorer(fake_llm, criteria)

    async def _search_vector_store(query, filters, limit, threshold):
        return [
            {"id": "calm", "memory": "rainy day, feeling heavy", "score": 0.6},
            {"id": "joy", "memory": "feeling great today", "score": 0.5},
        ]

    m._search_vector_store = _search_vector_store
    m._has_advanced_operators = MagicMock(return_value=False)
    return m


class TestSearchCriteriaWiring:
    def test_criteria_runs_when_configured(self):
        criteria = [CriterionConfig(name="joy", description="positive emotion", weight=3)]
        m = _build_memory(criteria=criteria)
        m.llm.generate_response.side_effect = [
            '{"joy": 0.1}',  # rainy day → low joy
            '{"joy": 0.9}',  # feeling great → high joy
        ]
        result = m.search("happy?", filters={"user_id": "alice"})
        # Re-sorted by criteria_score descending
        assert [r["id"] for r in result["results"]] == ["joy", "calm"]
        assert result["results"][0]["criteria_score"] == pytest.approx(0.9)

    def test_use_criteria_false_skips_scorer(self):
        criteria = [CriterionConfig(name="joy", description="positive", weight=3)]
        m = _build_memory(criteria=criteria)
        m.llm.generate_response.side_effect = ['{"joy": 0.9}']
        result = m.search("happy?", filters={"user_id": "alice"}, use_criteria=False)
        # Original vector-store order preserved; no LLM calls
        assert [r["id"] for r in result["results"]] == ["calm", "joy"]
        m.llm.generate_response.assert_not_called()
        # No criteria_score field added
        assert "criteria_score" not in result["results"][0]

    def test_per_call_criteria_overrides_config(self):
        # Project-level criteria say "joy", per-call override flips to "negativity"
        configured = [CriterionConfig(name="joy", description="positive", weight=1)]
        m = _build_memory(criteria=configured)
        m.llm.generate_response.side_effect = [
            '{"negativity": 0.9}',  # rainy day → high negativity
            '{"negativity": 0.1}',  # feeling great → low negativity
        ]
        result = m.search(
            "anything?",
            filters={"user_id": "alice"},
            criteria=[{"name": "negativity", "description": "negative tone", "weight": 1}],
        )
        # Per-call criteria scorer used: rainy day wins
        assert [r["id"] for r in result["results"]] == ["calm", "joy"]
        assert "negativity" in result["results"][0]["criteria_breakdown"]

    def test_no_criteria_no_scorer(self):
        m = _build_memory(criteria=None)
        result = m.search("q", filters={"user_id": "alice"})
        # Original order; no LLM calls
        assert [r["id"] for r in result["results"]] == ["calm", "joy"]
        m.llm.generate_response.assert_not_called()

    def test_use_criteria_true_without_config_raises(self):
        m = _build_memory(criteria=None)
        with pytest.raises(ValueError, match="no criteria"):
            m.search("q", filters={"user_id": "alice"}, use_criteria=True)

    def test_scorer_failure_falls_back_to_prior_order(self):
        """When the scorer itself blows up at a high level, search returns prior-step results."""
        criteria = [CriterionConfig(name="joy", description="positive")]
        m = _build_memory(criteria=criteria)
        # Patch the scorer.score to raise, simulating a catastrophic error past the
        # per-doc try/except (e.g. corrupted scorer state).
        m.criteria_scorer.score = MagicMock(side_effect=RuntimeError("scorer dead"))
        result = m.search("q", filters={"user_id": "alice"})
        # Falls back to original ordering, no exception bubbles up
        assert [r["id"] for r in result["results"]] == ["calm", "joy"]


class TestAsyncSearchCriteriaWiring:
    def test_async_criteria_runs_when_configured(self):
        criteria = [CriterionConfig(name="joy", description="positive", weight=1)]
        m = _build_async_memory(criteria=criteria)
        m.llm.generate_response.side_effect = ['{"joy": 0.1}', '{"joy": 0.9}']
        result = asyncio.run(m.search("happy?", filters={"user_id": "alice"}))
        assert [r["id"] for r in result["results"]] == ["joy", "calm"]

    def test_async_use_criteria_false_skips(self):
        criteria = [CriterionConfig(name="joy", description="positive", weight=1)]
        m = _build_async_memory(criteria=criteria)
        m.llm.generate_response.side_effect = ['{"joy": 0.9}']
        result = asyncio.run(
            m.search("q", filters={"user_id": "alice"}, use_criteria=False)
        )
        assert [r["id"] for r in result["results"]] == ["calm", "joy"]
        m.llm.generate_response.assert_not_called()
