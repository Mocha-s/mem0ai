from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BaseRetriever(ABC):
    """Base abstract class for all retrieval components."""
    
    @abstractmethod
    def retrieve(self, query: str, memories: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieve and process memories based on the query.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memory items to process
            **kwargs: Additional parameters specific to the retriever
            
        Returns:
            List[Dict[str, Any]]: Processed list of memory items
        """
        pass


class BaseSearchEngine(BaseRetriever):
    """Base class for search engines like BM25."""
    
    @abstractmethod
    def build_index(self, memories: List[Dict[str, Any]]) -> None:
        """
        Build search index from memories.
        
        Args:
            memories (List[Dict[str, Any]]): List of memory items to index
        """
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for relevant memories.
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        pass


class BaseReranker(BaseRetriever):
    """Base class for reranking components."""
    
    @abstractmethod
    def rerank(self, query: str, memories: List[Dict[str, Any]], limit: int = 100) -> List[Dict[str, Any]]:
        """
        Rerank memories based on relevance.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memory items to rerank
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: Reranked list of memory items
        """
        pass


class BaseFilter(BaseRetriever):
    """Base class for filtering components."""
    
    @abstractmethod
    def filter(self, query: str, memories: List[Dict[str, Any]], threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Filter memories based on relevance criteria.
        
        Args:
            query (str): The search query
            memories (List[Dict[str, Any]]): List of memory items to filter
            threshold (float): Relevance threshold for filtering
            
        Returns:
            List[Dict[str, Any]]: Filtered list of memory items
        """
        pass
