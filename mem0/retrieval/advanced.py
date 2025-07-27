import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, Set

from .bm25_engine import BM25SearchEngine
from .reranker import LLMReranker
from .filter import MemoryFilter
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class AdvancedRetrieval:
    """Advanced retrieval coordinator that orchestrates BM25 search, LLM reranking, and intelligent filtering."""
    
    def __init__(self, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the advanced retrieval system.
        
        Args:
            llm_config (Optional[Dict[str, Any]]): LLM configuration for reranking and filtering
        """
        self.bm25_engine = BM25SearchEngine()
        
        # Initialize LLM-based components if config is provided
        if llm_config:
            self.reranker = LLMReranker(llm_config)
            self.filter = MemoryFilter(llm_config)
        else:
            self.reranker = None
            self.filter = None
            logger.warning("No LLM config provided, LLM-based features will be disabled")
    
    def _get_memory_id(self, memory: Dict[str, Any]) -> str:
        """
        Extract a unique identifier from a memory item for deduplication.
        
        Args:
            memory (Dict[str, Any]): Memory item
            
        Returns:
            str: Unique identifier
        """
        # Try different ID fields
        for id_field in ['id', 'memory_id', 'hash']:
            if id_field in memory and memory[id_field]:
                return str(memory[id_field])
        
        # Fallback to memory content hash
        memory_text = memory.get('memory', '') or memory.get('data', '') or str(memory)
        return str(hash(memory_text))
    
    def _merge_results(self, semantic_results: List[Dict[str, Any]], bm25_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge semantic search results with BM25 results, avoiding duplicates.
        
        Args:
            semantic_results (List[Dict[str, Any]]): Results from semantic search
            bm25_results (List[Dict[str, Any]]): Results from BM25 search
            
        Returns:
            List[Dict[str, Any]]: Merged and deduplicated results
        """
        merged_results = []
        seen_ids: Set[str] = set()
        
        # Add semantic results first (they typically have better base relevance)
        for memory in semantic_results:
            memory_id = self._get_memory_id(memory)
            if memory_id not in seen_ids:
                memory_copy = memory.copy()
                memory_copy['source'] = 'semantic'
                merged_results.append(memory_copy)
                seen_ids.add(memory_id)
        
        # Add BM25 results that aren't already included
        for memory in bm25_results:
            memory_id = self._get_memory_id(memory)
            if memory_id not in seen_ids:
                memory_copy = memory.copy()
                memory_copy['source'] = 'bm25'
                merged_results.append(memory_copy)
                seen_ids.add(memory_id)
        
        logger.info(f"Merged {len(semantic_results)} semantic + {len(bm25_results)} BM25 results into {len(merged_results)} unique results")
        return merged_results
    
    async def _run_bm25_search(self, query: str, semantic_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run BM25 search asynchronously.
        
        Args:
            query (str): Search query
            semantic_results (List[Dict[str, Any]]): Semantic search results to build index from
            
        Returns:
            List[Dict[str, Any]]: BM25 search results
        """
        try:
            # Run BM25 search in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            bm25_results = await loop.run_in_executor(
                None, 
                self.bm25_engine.retrieve, 
                query, 
                semantic_results
            )
            logger.debug(f"BM25 search returned {len(bm25_results)} results")
            return bm25_results
        except Exception as e:
            logger.error(f"Error in BM25 search: {str(e)}")
            return []
    
    async def _run_reranking(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run LLM reranking asynchronously.
        
        Args:
            query (str): Search query
            results (List[Dict[str, Any]]): Results to rerank
            
        Returns:
            List[Dict[str, Any]]: Reranked results
        """
        if not self.reranker or not self.reranker.is_available():
            logger.warning("LLM reranker not available, skipping reranking")
            return results
        
        try:
            # Run reranking in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            reranked_results = await loop.run_in_executor(
                None,
                self.reranker.rerank,
                query,
                results
            )
            logger.debug(f"Reranking processed {len(results)} -> {len(reranked_results)} results")
            return reranked_results
        except Exception as e:
            logger.error(f"Error in reranking: {str(e)}")
            return results
    
    async def _run_filtering(self, query: str, results: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Run intelligent filtering asynchronously.
        
        Args:
            query (str): Search query
            results (List[Dict[str, Any]]): Results to filter
            threshold (float): Filtering threshold
            
        Returns:
            List[Dict[str, Any]]: Filtered results
        """
        if not self.filter or not self.filter.is_available():
            logger.warning("Memory filter not available, skipping filtering")
            return results
        
        try:
            # Run filtering in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            filtered_results = await loop.run_in_executor(
                None,
                self.filter.filter,
                query,
                results,
                threshold
            )
            logger.debug(f"Filtering processed {len(results)} -> {len(filtered_results)} results")
            return filtered_results
        except Exception as e:
            logger.error(f"Error in filtering: {str(e)}")
            return results
    
    @PerformanceMonitor.monitor_async_latency("AdvancedRetrieval", 500)
    async def search(
        self, 
        query: str, 
        semantic_results: List[Dict[str, Any]], 
        keyword_search: bool = False, 
        rerank: bool = False, 
        filter_memories: bool = False, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Perform advanced retrieval with optional BM25 search, reranking, and filtering.
        
        Args:
            query (str): Search query
            semantic_results (List[Dict[str, Any]]): Base semantic search results
            keyword_search (bool): Enable BM25 keyword search
            rerank (bool): Enable LLM-based reranking
            filter_memories (bool): Enable intelligent memory filtering
            **kwargs: Additional parameters (threshold, limit, etc.)
            
        Returns:
            List[Dict[str, Any]]: Enhanced search results
        """
        start_time = time.time()
        
        if not semantic_results:
            logger.warning("No semantic results provided for advanced retrieval")
            return []
        
        results = semantic_results.copy()
        
        try:
            # Phase 1: BM25 keyword search and merging
            if keyword_search:
                logger.debug("Running BM25 keyword search...")
                bm25_results = await self._run_bm25_search(query, semantic_results)
                results = self._merge_results(results, bm25_results)
            
            # Phase 2: LLM reranking
            if rerank:
                logger.debug("Running LLM reranking...")
                results = await self._run_reranking(query, results)
            
            # Phase 3: Intelligent filtering
            if filter_memories:
                threshold = kwargs.get('threshold', 0.7)
                logger.debug(f"Running intelligent filtering with threshold {threshold}...")
                results = await self._run_filtering(query, results, threshold)
            
            # Apply final limit if specified
            limit = kwargs.get('limit')
            if limit and len(results) > limit:
                results = results[:limit]
            
            # Performance monitoring
            elapsed_time = (time.time() - start_time) * 1000
            logger.info(f"Advanced retrieval completed in {elapsed_time:.2f}ms")
            logger.info(f"Final results: {len(results)} memories for query: '{query}'")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in advanced retrieval: {str(e)}")
            # Return original semantic results as fallback
            return semantic_results
    
    def is_available(self) -> Dict[str, bool]:
        """
        Check availability of all components.
        
        Returns:
            Dict[str, bool]: Availability status of each component
        """
        return {
            'bm25_search': True,  # BM25 is always available
            'reranking': self.reranker.is_available() if self.reranker else False,
            'filtering': self.filter.is_available() if self.filter else False
        }
