"""
Search Memories Service

Microservice for searching memories in Mem0 with multiple strategies.
"""

from typing import Dict, Any, List, Optional
from ..base.service import BaseService, BaseStrategy, ServiceResponse
from ...client.mem0_api_client import Mem0APIClient, Mem0Config
import os

def extract_memories_from_api_result(api_result: Any) -> List[Dict[str, Any]]:
    """
    Extract memories array from various API response structures.
    
    Handles:
    - Direct array responses
    - Nested results.results structure
    - Dictionary with results key
    """
    memories = []
    
    if isinstance(api_result, dict):
        # Handle nested results structure (results.results)
        if 'results' in api_result and isinstance(api_result['results'], dict):
            if 'results' in api_result['results']:
                memories = api_result['results']['results']
            elif isinstance(api_result['results'], list):
                memories = api_result['results']
        # Handle direct results array in dict
        elif 'results' in api_result and isinstance(api_result['results'], list):
            memories = api_result['results']
        # Handle dictionary response that might be memories itself
        elif isinstance(api_result, list):
            memories = api_result
    elif isinstance(api_result, list):
        memories = api_result
    
    # Ensure memories is always a list
    return memories if isinstance(memories, list) else []

class SemanticSearchStrategy(BaseStrategy):
    """Semantic search strategy using vector similarity"""
    
    def __init__(self):
        super().__init__("semantic", "Semantic search using vector similarity")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute semantic search"""
        try:
            query = arguments.get('query', '')
            filters = arguments.get('filters', {})
            top_k = arguments.get('top_k', 10)
            
            # Add user/agent/run IDs to filters if provided at top level
            if 'user_id' in arguments and arguments['user_id']:
                filters['user_id'] = arguments['user_id']
            if 'agent_id' in arguments and arguments['agent_id']:
                filters['agent_id'] = arguments['agent_id']
            if 'run_id' in arguments and arguments['run_id']:
                filters['run_id'] = arguments['run_id']
            
            # Get Mem0 API configuration
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),  # Default to local server
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            # Use real Mem0 API v2 search
            async with Mem0APIClient(config) as client:
                api_result = await client.search_memories(
                    query=query,
                    filters=filters,
                    top_k=top_k,
                    fields=arguments.get('fields'),
                    rerank=arguments.get('rerank', False),
                    keyword_search=False,  # Pure semantic search
                    filter_memories=arguments.get('filter_memories', False),
                    threshold=arguments.get('threshold', 0.3),
                    version="v2"
                )
            
            # Extract memories array from API response
            memories = extract_memories_from_api_result(api_result)
            
            return ServiceResponse(
                status="success",
                message=f"Found {len(memories)} memories using semantic search",
                data={"memories": memories, "total_count": len(memories)},
                metadata={
                    "strategy": "semantic",
                    "query": query,
                    "top_k": top_k,
                    "api_version": "v2"
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Semantic search strategy failed: {str(e)}"
            )


class GraphSearchStrategy(BaseStrategy):
    """Graph-based search with relationship traversal"""
    
    def __init__(self):
        super().__init__("graph", "Graph-based search with relationship traversal")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute graph search"""
        try:
            query = arguments.get('query', '')
            filters = arguments.get('filters', {})
            
            # Add user/agent/run IDs to filters if provided at top level
            if 'user_id' in arguments and arguments['user_id']:
                filters['user_id'] = arguments['user_id']
            if 'agent_id' in arguments and arguments['agent_id']:
                filters['agent_id'] = arguments['agent_id']
            if 'run_id' in arguments and arguments['run_id']:
                filters['run_id'] = arguments['run_id']
            
            # Add graph-specific filters
            if not filters.get('enable_graph'):
                return ServiceResponse(
                    status="error",
                    message="Graph strategy requires enable_graph=true in filters"
                )
            
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            async with Mem0APIClient(config) as client:
                api_result = await client.search_memories(
                    query=query,
                    filters=filters,
                    top_k=arguments.get('top_k', 10),
                    fields=arguments.get('fields'),
                    rerank=True,  # Enable reranking for graph search
                    keyword_search=False,
                    filter_memories=True,
                    threshold=arguments.get('threshold', 0.2),  # Lower threshold for graph
                    version="v2"
                )
            
            # Extract memories array from API response
            memories = extract_memories_from_api_result(api_result)
            
            return ServiceResponse(
                status="success",
                message=f"Found {len(memories)} memories using graph search",
                data={
                    "memories": memories,
                    "total_count": len(memories),
                    "graph_traversal": True
                },
                metadata={
                    "strategy": "graph",
                    "query": query,
                    "reranked": True,
                    "api_version": "v2"
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Graph search strategy failed: {str(e)}"
            )


class AdvancedSearchStrategy(BaseStrategy):
    """Advanced search with complex filters and criteria"""
    
    def __init__(self):
        super().__init__("advanced", "Advanced search with complex logical operators")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute advanced search with complex filters"""
        try:
            query = arguments.get('query', '')
            filters = arguments.get('filters', {})
            
            # Add user/agent/run IDs to filters if provided at top level
            if 'user_id' in arguments and arguments['user_id']:
                filters['user_id'] = arguments['user_id']
            if 'agent_id' in arguments and arguments['agent_id']:
                filters['agent_id'] = arguments['agent_id']
            if 'run_id' in arguments and arguments['run_id']:
                filters['run_id'] = arguments['run_id']
            
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            async with Mem0APIClient(config) as client:
                api_result = await client.search_memories(
                    query=query,
                    filters=filters,
                    top_k=arguments.get('top_k', 20),  # More results for advanced search
                    fields=arguments.get('fields'),
                    rerank=True,
                    keyword_search=arguments.get('keyword_search', True),
                    filter_memories=True,
                    threshold=arguments.get('threshold', 0.25),
                    version="v2"
                )
            
            # Extract memories array from API response
            memories = extract_memories_from_api_result(api_result)
            
            return ServiceResponse(
                status="success",
                message=f"Found {len(memories)} memories using advanced search",
                data={
                    "memories": memories,
                    "total_count": len(memories),
                    "filters_applied": filters,
                    "keyword_search_enabled": arguments.get('keyword_search', True)
                },
                metadata={
                    "strategy": "advanced",
                    "query": query,
                    "complex_filters": bool(filters),
                    "api_version": "v2"
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Advanced search strategy failed: {str(e)}"
            )


class HybridSearchStrategy(BaseStrategy):
    """Hybrid search combining semantic and keyword search"""
    
    def __init__(self):
        super().__init__("hybrid", "Hybrid search combining semantic and keyword approaches")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute hybrid search"""
        try:
            query = arguments.get('query', '')
            filters = arguments.get('filters', {})
            
            # Add user/agent/run IDs to filters if provided at top level
            if 'user_id' in arguments and arguments['user_id']:
                filters['user_id'] = arguments['user_id']
            if 'agent_id' in arguments and arguments['agent_id']:
                filters['agent_id'] = arguments['agent_id']
            if 'run_id' in arguments and arguments['run_id']:
                filters['run_id'] = arguments['run_id']
            
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            async with Mem0APIClient(config) as client:
                # Perform both semantic and keyword search concurrently
                semantic_task = client.search_memories(
                    query=query,
                    filters=filters,
                    top_k=arguments.get('top_k', 15),
                    keyword_search=False,
                    rerank=True,
                    threshold=0.3,
                    version="v2"
                )
                
                keyword_task = client.search_memories(
                    query=query,
                    filters=filters,
                    top_k=arguments.get('top_k', 15),
                    keyword_search=True,
                    rerank=True,
                    threshold=0.2,
                    version="v2"
                )
                
                # Execute both searches concurrently
                import asyncio
                semantic_result, keyword_result = await asyncio.gather(
                    semantic_task, keyword_task, return_exceptions=True
                )
                
                # Handle exceptions
                if isinstance(semantic_result, Exception):
                    semantic_result = []
                else:
                    semantic_result = extract_memories_from_api_result(semantic_result)
                    
                if isinstance(keyword_result, Exception):
                    keyword_result = []
                else:
                    keyword_result = extract_memories_from_api_result(keyword_result)
                
                # Combine and deduplicate results
                combined_memories = []
                seen_ids = set()
                
                # Add semantic results first (higher priority)
                for memory in semantic_result:
                    if memory.get('id') not in seen_ids:
                        memory['source'] = 'semantic'
                        combined_memories.append(memory)
                        seen_ids.add(memory.get('id'))
                
                # Add keyword results that weren't found semantically
                for memory in keyword_result:
                    if memory.get('id') not in seen_ids:
                        memory['source'] = 'keyword'
                        combined_memories.append(memory)
                        seen_ids.add(memory.get('id'))
                
                # Limit to requested top_k
                final_results = combined_memories[:arguments.get('top_k', 10)]
            
            return ServiceResponse(
                status="success",
                message=f"Found {len(final_results)} memories using hybrid search",
                data={
                    "memories": final_results,
                    "total_count": len(final_results),
                    "semantic_count": len(semantic_result),
                    "keyword_count": len(keyword_result),
                    "combined_deduplicated": True
                },
                metadata={
                    "strategy": "hybrid",
                    "query": query,
                    "search_types": ["semantic", "keyword"],
                    "api_version": "v2"
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Hybrid search strategy failed: {str(e)}"
            )


class SearchMemoriesService(BaseService):
    """Search Memories microservice with multiple search strategies"""
    
    def _initialize_strategies(self) -> None:
        """Initialize all available strategies for memory search"""
        self.register_strategy(SemanticSearchStrategy())
        self.register_strategy(GraphSearchStrategy())
        self.register_strategy(AdvancedSearchStrategy())
        self.register_strategy(HybridSearchStrategy())