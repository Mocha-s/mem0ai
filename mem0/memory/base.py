from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from mem0.configs.criteria import coerce_criteria
from mem0.memory.criteria_scorer import CriteriaScorer


class MemoryBase(ABC):
    @abstractmethod
    def get(self, memory_id):
        """
        Retrieve a memory by ID.

        Args:
            memory_id (str): ID of the memory to retrieve.

        Returns:
            dict: Retrieved memory.
        """
        pass

    @abstractmethod
    def get_all(self):
        """
        List all memories.

        Returns:
            list: List of all memories.
        """
        pass

    @abstractmethod
    def update(self, memory_id, data):
        """
        Update a memory by ID.

        Args:
            memory_id (str): ID of the memory to update.
            data (str): New content to update the memory with.

        Returns:
            dict: Success message indicating the memory was updated.
        """
        pass

    @abstractmethod
    def delete(self, memory_id):
        """
        Delete a memory by ID.

        Args:
            memory_id (str): ID of the memory to delete.
        """
        pass

    @abstractmethod
    def history(self, memory_id):
        """
        Get the history of changes for a memory by ID.

        Args:
            memory_id (str): ID of the memory to get history for.

        Returns:
            list: List of changes for the memory.
        """
        pass

    def _resolve_criteria_scorer(
        self,
        *,
        use_criteria: Optional[bool],
        criteria: Optional[List[Dict[str, Any]]],
    ) -> Optional[CriteriaScorer]:
        """Pick the active scorer for a search call.

        Activation rules:
        - ``use_criteria=False`` always disables.
        - Per-call ``criteria`` builds a transient scorer (overrides project-level).
        - Project-level ``self.config.retrieval_criteria`` triggers when ``use_criteria != False``.
        - ``use_criteria=True`` with no criteria available raises ``ValueError``.
        Returns ``None`` when scoring should be skipped.
        """
        if use_criteria is False:
            return None

        if criteria is not None:
            coerced = coerce_criteria(criteria)
            if not coerced:
                if use_criteria is True:
                    raise ValueError(
                        "use_criteria=True but no criteria provided. Pass a non-empty "
                        "criteria=[...] list or configure retrieval_criteria on MemoryConfig."
                    )
                return None
            return CriteriaScorer(self.llm, coerced)

        configured = getattr(self.config, "retrieval_criteria", None)
        if configured:
            return getattr(self, "criteria_scorer", None) or CriteriaScorer(self.llm, configured)

        if use_criteria is True:
            raise ValueError(
                "use_criteria=True but no criteria configured. Set "
                "MemoryConfig.retrieval_criteria or pass criteria=[...] on the call."
            )
        return None
