import json
import time
import logging
from typing import List, Dict, Any, Optional

from mem0.utils.factory import LlmFactory
from mem0.configs.prompts import FILTER_MEMORIES_PROMPT
from .base import BaseFilter
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class MemoryFilter(BaseFilter):
    """LLM-based intelligent memory filter for improving search precision."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        """
        Initialize the memory filter.
        
        Args:
            llm_config (Dict[str, Any]): LLM configuration dictionary
        """
        self.llm_config = llm_config
        try:
            provider = llm_config.get('provider', 'openai')
            # Remove provider from config before passing to LlmFactory
            config_for_llm = {k: v for k, v in llm_config.items() if k != 'provider'}
            self.llm = LlmFactory.create(provider, config_for_llm)
            logger.info(f"Initialized MemoryFilter with provider: {provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            self.llm = None
    
    def _build_filter_prompt(self, query: str, memories: List[Dict[str, Any]], threshold: float) -> str:
        """
        Build the filtering prompt for the LLM.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memories to filter
            threshold (float): Relevance threshold for filtering
            
        Returns:
            str: Formatted prompt for the LLM
        """
        # Format memories for the prompt
        formatted_memories = []
        for i, memory in enumerate(memories):
            memory_text = memory.get('memory', '') or memory.get('data', '') or str(memory)
            formatted_memories.append(f"{i}: {memory_text}")
        
        memories_text = "\n".join(formatted_memories)
        
        return FILTER_MEMORIES_PROMPT.format(
            query=query,
            threshold=threshold,
            memories=memories_text
        )
    
    def _parse_filter_response(self, response: str, original_memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parse the LLM response and extract filtered memories.
        
        Args:
            response (str): LLM response containing filtered results
            original_memories (List[Dict[str, Any]]): Original memory list
            
        Returns:
            List[Dict[str, Any]]: Filtered memories with relevance scores
        """
        try:
            # Parse JSON response
            parsed_response = json.loads(response.strip())
            filtered_data = parsed_response.get('filtered_memories', [])
            
            filtered_memories = []
            for item in filtered_data:
                memory_obj = item.get('memory', {})
                relevance_score = item.get('relevance_score', 0.0)
                reason = item.get('reason', '')
                
                # Find the original memory by matching content or ID
                original_memory = None
                if isinstance(memory_obj, dict) and 'id' in memory_obj:
                    # Try to find by ID
                    for orig_mem in original_memories:
                        if orig_mem.get('id') == memory_obj.get('id'):
                            original_memory = orig_mem
                            break
                
                if original_memory is None:
                    # Fallback: use the memory object from response
                    original_memory = memory_obj
                
                if original_memory:
                    filtered_memory = original_memory.copy() if isinstance(original_memory, dict) else original_memory
                    if isinstance(filtered_memory, dict):
                        filtered_memory['filter_score'] = float(relevance_score)
                        filtered_memory['filter_reason'] = reason
                    filtered_memories.append(filtered_memory)
            
            return filtered_memories
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse filter response: {str(e)}")
            logger.debug(f"Raw response: {response}")
            # Return original memories with default scores as fallback
            return self._fallback_filter(original_memories, 0.7)
    
    def _fallback_filter(self, memories: List[Dict[str, Any]], threshold: float) -> List[Dict[str, Any]]:
        """
        Fallback filtering when LLM parsing fails.
        
        Args:
            memories (List[Dict[str, Any]]): Original memories
            threshold (float): Relevance threshold
            
        Returns:
            List[Dict[str, Any]]: Filtered memories with default scores
        """
        logger.warning("Using fallback filtering due to LLM parsing failure")
        fallback_memories = []
        for i, memory in enumerate(memories):
            # Simple fallback: keep memories with existing scores above threshold
            existing_score = memory.get('score', 0.8)  # Default to 0.8 if no score
            if existing_score >= threshold:
                memory_copy = memory.copy() if isinstance(memory, dict) else memory
                if isinstance(memory_copy, dict):
                    memory_copy['filter_score'] = existing_score
                    memory_copy['filter_reason'] = 'Fallback filtering based on existing score'
                fallback_memories.append(memory_copy)
        return fallback_memories
    
    @PerformanceMonitor.monitor_latency("MemoryFilter", 300)
    def filter(self, query: str, memories: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Filter memories based on relevance using LLM.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memories to filter
            threshold (float): Relevance threshold for filtering (0.0-1.0)
            
        Returns:
            List[Dict[str, Any]]: Filtered memories with relevance scores
        """
        start_time = time.time()
        
        if not memories:
            logger.warning("No memories provided for filtering")
            return []
        
        if not self.llm:
            logger.error("LLM not initialized, using fallback filtering")
            return self._fallback_filter(memories, threshold)
        
        try:
            # Limit input size for performance (max 15 memories for filtering)
            input_memories = memories[:min(len(memories), 15)]
            
            # Build filtering prompt
            prompt = self._build_filter_prompt(query, input_memories, threshold)
            
            # Call LLM for filtering
            messages = [{"role": "user", "content": prompt}]
            response = self.llm.generate_response(messages)
            
            # Parse response and get filtered memories
            filtered_memories = self._parse_filter_response(response, input_memories)
            
            # Performance monitoring
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if elapsed_time > 300:
                logger.warning(f"Memory filtering exceeded target latency: {elapsed_time:.2f}ms > 300ms")
            elif elapsed_time < 200:
                logger.info(f"Memory filtering completed faster than expected: {elapsed_time:.2f}ms")
            else:
                logger.info(f"Memory filtering completed in {elapsed_time:.2f}ms")
            
            logger.info(f"Filtered {len(filtered_memories)} memories from {len(input_memories)} for query: '{query}'")
            return filtered_memories
            
        except Exception as e:
            logger.error(f"Error during memory filtering: {str(e)}")
            return self._fallback_filter(memories, threshold)
    
    def retrieve(self, query: str, memories: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve memories using LLM filtering (implements BaseRetriever interface).
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memory items to filter
            **kwargs: Additional parameters (threshold, etc.)
            
        Returns:
            List[Dict[str, Any]]: Filtered memories
        """
        threshold = kwargs.get('threshold', 0.7)
        return self.filter(query, memories, threshold)
    
    def filter_by_score(self, memories: List[Dict[str, Any]], min_score: float = 0.7) -> List[Dict[str, Any]]:
        """
        Filter memories by minimum score threshold (convenience method).
        
        Args:
            memories (List[Dict[str, Any]]): List of memories with scores
            min_score (float): Minimum score threshold
            
        Returns:
            List[Dict[str, Any]]: Memories above the score threshold
        """
        filtered = []
        for memory in memories:
            score = memory.get('filter_score') or memory.get('score') or memory.get('relevance_score', 0.0)
            if score >= min_score:
                filtered.append(memory)
        
        logger.info(f"Score-based filtering kept {len(filtered)} out of {len(memories)} memories")
        return filtered
    
    def is_available(self) -> bool:
        """
        Check if the memory filter is available and ready.
        
        Returns:
            bool: True if LLM is initialized and ready, False otherwise
        """
        return self.llm is not None
