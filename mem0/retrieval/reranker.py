import json
import time
import logging
from typing import List, Dict, Any, Optional

from mem0.utils.factory import LlmFactory
from mem0.configs.prompts import RERANK_MEMORIES_PROMPT
from .base import BaseReranker
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class LLMReranker(BaseReranker):
    """LLM-based reranker for improving search result relevance."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        Initialize the LLM reranker.

        Args:
            llm_config (Dict[str, Any]): LLM configuration dictionary
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
            logger.info(f"Initialized LLMReranker with provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            self.llm = None
    
    def _build_rerank_prompt(self, query: str, memories: List[Dict[str, Any]]) -> str:
        """
        Build the reranking prompt for the LLM.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memories to rerank
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Format memories for the prompt
        formatted_memories = []
        for i, memory in enumerate(memories):
            memory_text = memory.get('memory', '') or memory.get('data', '') or str(memory)
            formatted_memories.append(f"{i}: {memory_text}")
        
        memories_text = "\n".join(formatted_memories)
        
        return RERANK_MEMORIES_PROMPT.format(
            query=query,
            memories=memories_text
        )
    
    def _parse_rerank_response(self, response: str, original_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse the LLM response and extract reranked memories.
        
        Args:
            response (str): LLM response containing reranked results
            original_memories (List[Dict[str, Any]]): Original memory list
            
        Returns:
            List[Dict[str, Any]]: Reranked memories with relevance scores
        """
        try:
            # Parse JSON response
            parsed_response = json.loads(response.strip())
            reranked_data = parsed_response.get('reranked_memories', [])
            
            reranked_memories = []
            for item in reranked_data:
                original_index = item.get('original_index', 0)
                relevance_score = item.get('relevance_score', 0.0)
                
                # Get the original memory
                if 0 <= original_index < len(original_memories):
                    memory = original_memories[original_index].copy()
                    memory['relevance_score'] = float(relevance_score)
                    memory['rerank_position'] = len(reranked_memories) + 1
                    reranked_memories.append(memory)
            
            return reranked_memories
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse rerank response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            # Return original memories with default scores as fallback
            return self._fallback_rerank(original_memories)
    
    def _fallback_rerank(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fallback reranking when LLM parsing fails.
        
        Args:
            memories (List[Dict[str, Any]]): Original memories
            
        Returns:
            List[Dict[str, Any]]: Memories with default relevance scores
        """
        logger.warning("Using fallback reranking due to LLM parsing failure")
        fallback_memories = []
        for i, memory in enumerate(memories):
            memory_copy = memory.copy()
            memory_copy['relevance_score'] = 1.0 - (i * 0.1)  # Decreasing scores
            memory_copy['rerank_position'] = i + 1
            fallback_memories.append(memory_copy)
        return fallback_memories
    
    @PerformanceMonitor.monitor_latency("LLMRerank", 200)
    def rerank(self, query: str, memories: List[Dict[str, Any]], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Rerank memories based on relevance using LLM.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memories to rerank
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: Reranked memories with relevance scores
        """
        start_time = time.time()
        
        if not memories:
            logger.warning("No memories provided for reranking")
            return []
        
        if not self.llm:
            logger.error("LLM not initialized, using fallback reranking")
            return self._fallback_rerank(memories[:limit])
        
        try:
            # Limit input size for performance
            input_memories = memories[:min(len(memories), 20)]  # Limit to 20 for performance
            
            # Build reranking prompt
            prompt = self._build_rerank_prompt(query, input_memories)
            
            # Call LLM for reranking
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_response(messages)
            
            # Parse response and get reranked memories
            reranked_memories = self._parse_rerank_response(response, input_memories)
            
            # Apply limit
            reranked_memories = reranked_memories[:limit]
            
            # Performance monitoring
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if elapsed_time > 200:
                logger.warning(f"LLM reranking exceeded target latency: {elapsed_time:.2f}ms > 200ms")
            elif elapsed_time < 150:
                logger.info(f"LLM reranking completed faster than expected: {elapsed_time:.2f}ms")
            else:
                logger.info(f"LLM reranking completed in {elapsed_time:.2f}ms")
            
            logger.info(f"Reranked {len(reranked_memories)} memories for query: '{query}'")
            return reranked_memories
            
        except Exception as e:
            logger.error(f"Error during LLM reranking: {str(e)}")
            return self._fallback_rerank(memories[:limit])
    
    def retrieve(self, query: str, memories: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve memories using LLM reranking (implements BaseRetriever interface).
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memory items to rerank
            **kwargs: Additional parameters (limit, etc.)
            
        Returns:
            List[Dict[str, Any]]: Reranked memories
        """
        limit = kwargs.get('limit', 100)
        return self.rerank(query, memories, limit)
    
    def is_available(self) -> bool:
        """
        Check if the LLM reranker is available and ready.
        
        Returns:
            bool: True if LLM is initialized and ready, False otherwise
        """
        return self.llm is not None
