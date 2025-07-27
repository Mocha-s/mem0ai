import time
import logging
from typing import List, Dict, Any, Optional

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    raise ImportError("rank_bm25 is not installed. Please install it using pip install rank-bm25")

from .base import BaseSearchEngine
from .performance import PerformanceMonitor

logger = logging.getLogger(__name__)


class BM25SearchEngine(BaseSearchEngine):
    """BM25-based keyword search engine for enhanced memory retrieval."""
    
    def __init__(self):
        """Initialize the BM25 search engine."""
        self.bm25 = None
        self.documents = []
        self.indexed_memories = []
        
    def build_index(self, memories: List[Dict[str, Any]]) -> None:
        """
        Build BM25 index from memories.
        
        Args:
            memories (List[Dict[str, Any]]): List of memory items to index
        """
        if not memories:
            logger.warning("No memories provided for BM25 indexing")
            return
            
        # Extract text content and tokenize
        documents = []
        self.indexed_memories = []
        
        for memory in memories:
            # Extract memory text content
            memory_text = memory.get('memory', '') or memory.get('data', '') or str(memory)
            
            # Tokenize the text (simple whitespace tokenization)
            tokens = memory_text.lower().split()
            documents.append(tokens)
            self.indexed_memories.append(memory)
        
        # Build BM25 index
        if documents:
            self.bm25 = BM25Okapi(documents)
            logger.info(f"Built BM25 index with {len(documents)} documents")
        else:
            logger.warning("No valid documents found for BM25 indexing")
    
    @PerformanceMonitor.monitor_latency("BM25Search", 10)
    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for relevant memories using BM25.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: Search results with BM25 scores
        """
        start_time = time.time()
        
        if not self.bm25 or not self.indexed_memories:
            logger.warning("BM25 index not built or empty")
            return []
        
        # Tokenize query
        tokenized_query = query.lower().split()
        
        if not tokenized_query:
            logger.warning("Empty query provided")
            return []
        
        try:
            # Get BM25 scores for all documents
            scores = self.bm25.get_scores(tokenized_query)
            
            # Create results with scores
            results = []
            for i, score in enumerate(scores):
                if i < len(self.indexed_memories):
                    memory_item = self.indexed_memories[i].copy()
                    memory_item['bm25_score'] = float(score)
                    results.append(memory_item)
            
            # Sort by BM25 score (descending)
            results.sort(key=lambda x: x.get('bm25_score', 0), reverse=True)
            
            # Apply limit
            results = results[:limit]
            
            # Performance monitoring
            elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if elapsed_time > 10:
                logger.warning(f"BM25 search exceeded target latency: {elapsed_time:.2f}ms > 10ms")
            else:
                logger.debug(f"BM25 search completed in {elapsed_time:.2f}ms")
            
            logger.info(f"BM25 search returned {len(results)} results for query: '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Error during BM25 search: {str(e)}")
            return []
    
    def retrieve(self, query: str, memories: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve memories using BM25 search (implements BaseRetriever interface).
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memory items to search
            **kwargs: Additional parameters (limit, etc.)
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        limit = kwargs.get('limit', 100)
        
        # Build index if not already built or if memories changed
        if not self.bm25 or len(memories) != len(self.indexed_memories):
            self.build_index(memories)
        
        return self.search(query, limit)
    
    def get_top_n(self, query: str, n: int = 5) -> List[Dict[str, Any]]:
        """
        Get top N results for a query (convenience method).
        
        Args:
            query (str): The search query
            n (int): Number of top results to return
            
        Returns:
            List[Dict[str, Any]]: Top N search results
        """
        return self.search(query, limit=n)
    
    def is_indexed(self) -> bool:
        """
        Check if the BM25 index is built and ready.
        
        Returns:
            bool: True if index is ready, False otherwise
        """
        return self.bm25 is not None and len(self.indexed_memories) > 0
