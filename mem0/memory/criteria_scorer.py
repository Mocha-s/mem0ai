"""LLM-driven criteria-based scoring for memory search results.

After vector retrieval (and optional reranker), apply a project-defined set of weighted
criteria to re-rank candidates by domain-specific signals (joy, urgency, curiosity, ...).
For each candidate the LLM returns a JSON object mapping criterion name → score in [0, 1];
the final ``criteria_score`` is the weighted average over all criteria.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from mem0.configs.criteria import CriterionConfig
from mem0.memory.utils import remove_code_blocks

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = (
    "You are a memory-relevance scoring assistant. Given a search query, a memory "
    "document, and a list of named criteria, score the memory against EACH criterion "
    "on a scale from 0.0 to 1.0, where 0.0 means the memory does not match the criterion "
    "at all and 1.0 means it matches strongly.\n\n"
    "Respond with ONLY a single JSON object whose keys are the criterion names and whose "
    "values are floats between 0.0 and 1.0. Do not include any explanation, prose, or "
    "extra keys. Example response: {\"joy\": 0.8, \"curiosity\": 0.2}"
)

_MAX_INPUT_LEN = 4000
_MISSING_CRITERION_FALLBACK = 0.5


class CriteriaScorer:
    """Score and re-rank candidates against weighted user-defined criteria."""

    def __init__(self, llm: Any, criteria: List[CriterionConfig]):
        if not criteria:
            raise ValueError("CriteriaScorer requires at least one CriterionConfig.")
        self.llm = llm
        self.criteria = criteria
        self._weight_sum = sum(max(c.weight, 0.0) for c in criteria)

    def score(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return documents re-sorted by weighted criteria score (descending)."""
        if not documents:
            return documents

        scored: List[Dict[str, Any]] = []
        for doc in documents:
            doc_text = self._extract_doc_text(doc)
            try:
                response = self.llm.generate_response(
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": self._format_user_prompt(query, doc_text)},
                    ],
                    response_format={"type": "json_object"},
                )
                per_criterion = self._parse_response(response)
                criteria_score = self._weighted_average(per_criterion)
            except Exception as exc:
                logger.warning("Criteria scoring failed for a document, keeping original order: %s", exc)
                criteria_score = None
                per_criterion = {}

            enriched = doc.copy()
            enriched["criteria_score"] = criteria_score
            enriched["criteria_breakdown"] = per_criterion
            scored.append(enriched)

        scored.sort(key=_sort_key, reverse=True)
        return scored

    @staticmethod
    def _extract_doc_text(doc: Dict[str, Any]) -> str:
        for key in ("memory", "text", "content"):
            if key in doc and doc[key] is not None:
                return str(doc[key])
        return str(doc)

    def _format_user_prompt(self, query: str, doc_text: str) -> str:
        criteria_block = "\n".join(
            f"- {c.name}: {c.description}" for c in self.criteria
        )
        safe_query = query[:_MAX_INPUT_LEN]
        safe_doc = doc_text[:_MAX_INPUT_LEN]
        return (
            f"Criteria:\n{criteria_block}\n\n"
            f"Query: {safe_query}\n\n"
            f"Memory: {safe_doc}\n\n"
            "Return a JSON object with one float score per criterion name."
        )

    def _parse_response(self, response: str) -> Dict[str, float]:
        if not response or not response.strip():
            raise ValueError("Empty response from LLM.")
        cleaned = remove_code_blocks(response).strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError(f"Expected JSON object, got {type(data).__name__}")

        parsed: Dict[str, float] = {}
        for c in self.criteria:
            raw = data.get(c.name)
            if raw is None:
                parsed[c.name] = _MISSING_CRITERION_FALLBACK
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                parsed[c.name] = _MISSING_CRITERION_FALLBACK
                continue
            parsed[c.name] = max(0.0, min(1.0, value))
        return parsed

    def _weighted_average(self, per_criterion: Dict[str, float]) -> Optional[float]:
        if self._weight_sum <= 0:
            return None
        total = 0.0
        for c in self.criteria:
            total += per_criterion.get(c.name, _MISSING_CRITERION_FALLBACK) * max(c.weight, 0.0)
        return total / self._weight_sum


def _sort_key(doc: Dict[str, Any]) -> float:
    score = doc.get("criteria_score")
    if score is not None:
        return float(score)
    semantic = doc.get("score")
    if semantic is not None:
        try:
            return float(semantic)
        except (TypeError, ValueError):
            return 0.0
    return 0.0
