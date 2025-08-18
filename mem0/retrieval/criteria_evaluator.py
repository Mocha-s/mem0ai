import json
import time
import logging
from typing import List, Dict, Any, Optional

from mem0.utils.factory import LlmFactory
from mem0.configs.prompts import CRITERIA_EVALUATION_PROMPT
from .base import BaseRetriever
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class CriteriaEvaluator(BaseRetriever):
    """
    LLM-based criteria evaluator for custom memory scoring and ranking.

    This class implements the criteria retrieval functionality that allows memories to be
    evaluated and ranked based on custom criteria such as emotional tone, intent, behavioral
    signals, or other domain-specific attributes. It uses an LLM to score each memory against
    the defined criteria and applies weighted scoring to produce a final relevance score.

    The evaluator supports:
    - Custom criteria definition with name, description, and weight
    - LLM-based evaluation of memories against multiple criteria
    - Weighted scoring calculation: final_score = Σ(criterion_score × weight) / Σ(weights)
    - Fallback evaluation when LLM is unavailable
    - Performance monitoring and error handling

    Example:
        >>> llm_config = {
        ...     'provider': 'openai',
        ...     'model': 'gpt-4o-mini',
        ...     'api_key': 'your-api-key'
        ... }
        >>> evaluator = CriteriaEvaluator(llm_config)
        >>>
        >>> criteria = [
        ...     {
        ...         'name': 'joy',
        ...         'description': 'Measure positive emotions and happiness',
        ...         'weight': 3.0
        ...     },
        ...     {
        ...         'name': 'curiosity',
        ...         'description': 'Assess interest in learning or exploring',
        ...         'weight': 2.0
        ...     }
        ... ]
        >>>
        >>> memories = [
        ...     {'memory': 'I feel so happy today!', 'id': '1'},
        ...     {'memory': 'I wonder how this works?', 'id': '2'}
        ... ]
        >>>
        >>> results = evaluator.evaluate_criteria("happiness", memories, criteria)
        >>> print(f"Top result: {results[0]['memory']}")
        >>> print(f"Score: {results[0]['criteria_final_score']:.3f}")

    Attributes:
        llm_config (Dict[str, Any]): Configuration for the LLM
        llm: The initialized LLM instance for criteria evaluation
    """
    
    def __init__(self, llm_config: Dict[str, Any]) -> None:
        """
        Initialize the criteria evaluator with LLM configuration.

        Args:
            llm_config (Dict[str, Any]): LLM configuration dictionary containing:
                - provider (str): LLM provider name (e.g., 'openai', 'anthropic')
                - model (str): Model name (e.g., 'gpt-4o-mini')
                - api_key (str): API key for the LLM service
                - temperature (float, optional): Sampling temperature (default: 0.1)
                - max_tokens (int, optional): Maximum tokens in response
                - Other provider-specific configuration options

        Raises:
            Exception: If LLM initialization fails, the evaluator will still be created
                      but with llm=None, causing evaluate_criteria to use fallback mode.

        Example:
            >>> config = {
            ...     'provider': 'openai',
            ...     'model': 'gpt-4o-mini',
            ...     'api_key': 'sk-...',
            ...     'temperature': 0.1
            ... }
            >>> evaluator = CriteriaEvaluator(config)
            >>> print(evaluator.is_available())  # True if LLM initialized successfully
        """
        self.llm_config = llm_config
        try:
            # Handle both dict and config object types
            if hasattr(llm_config, 'get'):
                # It's a dictionary
                provider = llm_config.get('provider', 'openai')
                config_for_llm = {k: v for k, v in llm_config.items() if k != 'provider'}
            elif hasattr(llm_config, '__dict__'):
                # It's a config object, convert to dict
                config_dict = llm_config.__dict__.copy()
                provider = config_dict.get('provider', 'openai')
                # Filter out incompatible parameters
                allowed_params = {'model', 'api_key', 'temperature', 'max_tokens', 'top_p', 'frequency_penalty', 'presence_penalty'}
                config_for_llm = {k: v for k, v in config_dict.items() if k != 'provider' and k in allowed_params}
            else:
                # Fallback: empty config
                provider = 'openai'
                config_for_llm = {}
                
            self.llm = LlmFactory.create(provider, config_for_llm)
            logger.info(f"Initialized CriteriaEvaluator with provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            self.llm = None
    
    def _build_criteria_prompt(self, query: str, memories: List[Dict[str, Any]], criteria: List[Dict[str, Any]]) -> str:
        """
        Build the criteria evaluation prompt for the LLM.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memories to evaluate
            criteria (List[Dict[str, Any]]): List of criteria with name, description, and weight
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Format memories for the prompt
        formatted_memories = []
        for i, memory in enumerate(memories):
            memory_text = memory.get('memory', '') or memory.get('data', '') or str(memory)
            formatted_memories.append(f"{i}: {memory_text}")
        
        memories_text = "\n".join(formatted_memories)
        
        # Format criteria for the prompt
        formatted_criteria = []
        for criterion in criteria:
            name = criterion.get('name', '')
            description = criterion.get('description', '')
            weight = criterion.get('weight', 1)
            formatted_criteria.append(f"- {name} (weight: {weight}): {description}")
        
        criteria_text = "\n".join(formatted_criteria)
        
        return CRITERIA_EVALUATION_PROMPT.format(
            query=query,
            criteria=criteria_text,
            memories=memories_text
        )
    
    def _parse_criteria_response(self, response: str, original_memories: List[Dict[str, Any]], criteria: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse the LLM response and extract evaluated memories with criteria scores.
        
        Args:
            response (str): LLM response containing criteria evaluation results
            original_memories (List[Dict[str, Any]]): Original memory list
            criteria (List[Dict[str, Any]]): List of criteria used for evaluation
            
        Returns:
            List[Dict[str, Any]]: Evaluated memories with criteria scores and final weighted scores
        """
        try:
            # Parse JSON response
            parsed_response = json.loads(response.strip())
            evaluated_data = parsed_response.get('evaluated_memories', [])
            
            evaluated_memories = []
            for item in evaluated_data:
                memory_index = item.get('memory_index', 0)
                criteria_scores = item.get('criteria_scores', {})
                
                # Get the original memory
                if 0 <= memory_index < len(original_memories):
                    memory = original_memories[memory_index].copy()
                    
                    # Add criteria scores
                    memory['criteria_scores'] = criteria_scores
                    
                    # Calculate weighted final score
                    final_score = self._calculate_weighted_scores(criteria_scores, criteria)
                    memory['criteria_final_score'] = final_score
                    
                    evaluated_memories.append(memory)
            
            # Sort by final score (descending)
            evaluated_memories.sort(key=lambda x: x.get('criteria_final_score', 0.0), reverse=True)
            
            return evaluated_memories
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse criteria evaluation response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            # Return original memories with default scores as fallback
            return self._fallback_evaluation(original_memories, criteria)
    
    def _calculate_weighted_scores(self, criteria_scores: Dict[str, float], criteria: List[Dict[str, Any]]) -> float:
        """
        Calculate weighted final score based on criteria scores and weights.
        
        Args:
            criteria_scores (Dict[str, float]): Scores for each criterion
            criteria (List[Dict[str, Any]]): List of criteria with weights
            
        Returns:
            float: Weighted final score
        """
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for criterion in criteria:
            name = criterion.get('name', '')
            weight = criterion.get('weight', 1.0)
            score = criteria_scores.get(name, 0.0)
            
            total_weighted_score += score * weight
            total_weight += weight
        
        # Avoid division by zero
        if total_weight == 0:
            return 0.0
        
        return total_weighted_score / total_weight
    
    def _fallback_evaluation(self, memories: List[Dict[str, Any]], criteria: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback evaluation when LLM parsing fails.
        
        Args:
            memories (List[Dict[str, Any]]): Original memories
            criteria (List[Dict[str, Any]]): List of criteria
            
        Returns:
            List[Dict[str, Any]]: Memories with default criteria scores
        """
        logger.warning("Using fallback criteria evaluation due to LLM parsing failure")
        fallback_memories = []
        
        for i, memory in enumerate(memories):
            memory_copy = memory.copy()
            
            # Add default criteria scores
            criteria_scores = {}
            for criterion in criteria:
                name = criterion.get('name', '')
                # Default score decreases with position
                criteria_scores[name] = max(0.1, 1.0 - (i * 0.1))
            
            memory_copy['criteria_scores'] = criteria_scores
            memory_copy['criteria_final_score'] = self._calculate_weighted_scores(criteria_scores, criteria)
            
            fallback_memories.append(memory_copy)
        
        # Sort by final score (descending)
        fallback_memories.sort(key=lambda x: x.get('criteria_final_score', 0.0), reverse=True)
        
        return fallback_memories

    @PerformanceMonitor.monitor_latency("CriteriaEvaluator", 400)
    def evaluate_criteria(self, query: str, memories: List[Dict[str, Any]], criteria: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Evaluate memories against custom criteria using LLM and return ranked results.

        This is the main method for criteria-based memory evaluation. It uses the configured
        LLM to score each memory against the provided criteria, calculates weighted final scores,
        and returns memories sorted by relevance according to the criteria.

        Args:
            query (str): The search query that provides context for evaluation
            memories (List[Dict[str, Any]]): List of memory dictionaries to evaluate.
                Each memory should contain at least a 'memory' or 'data' field with the text content.
            criteria (List[Dict[str, Any]]): List of criteria dictionaries, each containing:
                - name (str): Unique identifier for the criterion
                - description (str): Detailed description for LLM interpretation
                - weight (float): Weight for final score calculation (higher = more important)

        Returns:
            List[Dict[str, Any]]: Evaluated memories sorted by criteria_final_score (descending).
                Each returned memory includes:
                - All original memory fields
                - criteria_scores (Dict[str, float]): Score (0.0-1.0) for each criterion
                - criteria_final_score (float): Weighted final score

        Raises:
            No exceptions are raised. If LLM evaluation fails, fallback evaluation is used.

        Note:
            - Maximum 15 memories are processed per call for performance reasons
            - Target processing time is <400ms (monitored by PerformanceMonitor)
            - If LLM is unavailable, fallback evaluation provides default scores

        Example:
            >>> memories = [
            ...     {'memory': 'I love sunny days!', 'id': '1'},
            ...     {'memory': 'Rainy weather makes me sad', 'id': '2'}
            ... ]
            >>> criteria = [
            ...     {'name': 'joy', 'description': 'Positive emotions', 'weight': 2.0}
            ... ]
            >>> results = evaluator.evaluate_criteria("happiness", memories, criteria)
            >>> print(f"Top result: {results[0]['memory']}")
            >>> print(f"Joy score: {results[0]['criteria_scores']['joy']}")
            >>> print(f"Final score: {results[0]['criteria_final_score']}")
        """
        start_time = time.time()

        if not memories:
            logger.warning("No memories provided for criteria evaluation")
            return []

        if not criteria:
            logger.warning("No criteria provided for evaluation")
            return memories

        if not self.llm:
            logger.error("LLM not initialized, using fallback evaluation")
            return self._fallback_evaluation(memories, criteria)

        try:
            # Limit input size for performance (max 15 memories for criteria evaluation)
            input_memories = memories[:min(len(memories), 15)]

            # Build criteria evaluation prompt
            prompt = self._build_criteria_prompt(query, input_memories, criteria)

            # Call LLM for criteria evaluation
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_response(messages)

            # Parse response and get evaluated memories
            evaluated_memories = self._parse_criteria_response(response, input_memories, criteria)

            # Performance monitoring
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds

            if elapsed_time > 400:
                logger.warning(f"Criteria evaluation exceeded target latency: {elapsed_time:.2f}ms > 400ms")
            else:
                logger.info(f"Criteria evaluation completed in {elapsed_time:.2f}ms")

            logger.info(f"Evaluated {len(evaluated_memories)} memories against {len(criteria)} criteria for query: '{query}'")
            return evaluated_memories

        except Exception as e:
            logger.error(f"Error during criteria evaluation: {str(e)}")
            return self._fallback_evaluation(memories, criteria)

    def retrieve(self, query: str, memories: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve memories using criteria evaluation (implements BaseRetriever interface).

        This method provides a standardized interface for criteria-based retrieval that
        conforms to the BaseRetriever contract. It's primarily used by AdvancedRetrieval
        and other retrieval orchestrators.

        Args:
            query (str): The search query for context
            memories (List[Dict[str, Any]]): List of memory items to evaluate
            **kwargs: Additional parameters including:
                - criteria (List[Dict[str, Any]]): Criteria for evaluation (required)
                - limit (int): Maximum number of results to return (default: 100)

        Returns:
            List[Dict[str, Any]]: Evaluated memories with criteria scores, limited to
                the specified number of results. If no criteria provided, returns
                original memories up to the limit.

        Example:
            >>> memories = [{'memory': 'Happy memory', 'id': '1'}]
            >>> criteria = [{'name': 'joy', 'description': 'Happiness', 'weight': 1.0}]
            >>> results = evaluator.retrieve("happiness", memories,
            ...                             criteria=criteria, limit=5)
        """
        criteria = kwargs.get('criteria', [])
        limit = kwargs.get('limit', 100)

        if not criteria:
            logger.warning("No criteria provided in retrieve call, returning original memories")
            return memories[:limit]

        evaluated_memories = self.evaluate_criteria(query, memories, criteria)
        return evaluated_memories[:limit]

    def is_available(self) -> bool:
        """
        Check if the criteria evaluator is available and ready for use.

        This method verifies that the LLM has been successfully initialized and is
        ready to perform criteria evaluation. If this returns False, the evaluator
        will use fallback evaluation mode.

        Returns:
            bool: True if LLM is initialized and ready for criteria evaluation,
                 False if LLM initialization failed or is unavailable.

        Example:
            >>> evaluator = CriteriaEvaluator(llm_config)
            >>> if evaluator.is_available():
            ...     print("Ready for criteria evaluation")
            ... else:
            ...     print("Will use fallback evaluation")
        """
        return self.llm is not None
