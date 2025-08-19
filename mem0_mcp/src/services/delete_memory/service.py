"""
Delete Memory Service

Microservice for deleting memories from Mem0 with multiple strategies.
"""

from typing import Dict, Any, List
from ..base.service import BaseService, BaseStrategy, ServiceResponse
from ...client.mem0_api_client import Mem0APIClient, Mem0Config
import os

class SingleDeleteStrategy(BaseStrategy):
    """Delete a single memory by ID"""
    
    def __init__(self):
        super().__init__("single", "Delete a single memory by ID")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute single memory deletion"""
        try:
            memory_id = arguments.get('memory_id')
            if not memory_id:
                return ServiceResponse(
                    status="error",
                    message="memory_id is required for single delete strategy"
                )
            
            # Get Mem0 API configuration
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            # Use real Mem0 API
            async with Mem0APIClient(config) as client:
                result = await client.delete_memory(memory_id=memory_id)
            
            return ServiceResponse(
                status="success",
                message="Memory deleted successfully using single strategy",
                data=result,
                metadata={
                    "strategy": "single",
                    "memory_id": memory_id
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Single delete strategy failed: {str(e)}"
            )


class BatchDeleteStrategy(BaseStrategy):
    """Delete multiple memories in batch"""
    
    def __init__(self):
        super().__init__("batch", "Delete multiple memories in a single operation")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute batch memory deletion"""
        try:
            memory_ids = arguments.get('memory_ids', [])
            if not memory_ids:
                return ServiceResponse(
                    status="error",
                    message="memory_ids list is required for batch strategy"
                )
            
            if len(memory_ids) > 1000:
                return ServiceResponse(
                    status="error",
                    message="Batch delete limited to 1000 memories maximum"
                )
            
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            # Use batch delete API
            async with Mem0APIClient(config) as client:
                result = await client.batch_delete_memories(memory_ids=memory_ids)
            
            return ServiceResponse(
                status="success",
                message=f"Batch delete completed for {len(memory_ids)} memories",
                data=result,
                metadata={
                    "strategy": "batch",
                    "deleted_count": len(memory_ids),
                    "memory_ids": memory_ids
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Batch delete strategy failed: {str(e)}"
            )


class FilteredDeleteStrategy(BaseStrategy):
    """Delete memories based on filters/criteria"""
    
    def __init__(self):
        super().__init__("filtered", "Delete memories based on filters and criteria")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute filtered memory deletion"""
        try:
            filters = arguments.get('filters', {})
            if not filters:
                return ServiceResponse(
                    status="error",
                    message="filters are required for filtered delete strategy"
                )
            
            # Safety check - require confirmation for filtered deletes
            confirm_delete = arguments.get('confirm_delete', False)
            if not confirm_delete:
                return ServiceResponse(
                    status="error",
                    message="confirm_delete=true is required for filtered deletion to prevent accidental data loss"
                )
            
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            async with Mem0APIClient(config) as client:
                # First, search for memories matching the filters
                search_result = await client.search_memories(
                    query=arguments.get('query', '*'),  # Wildcard to match all
                    filters=filters,
                    top_k=arguments.get('max_delete_count', 100),  # Limit for safety
                    version="v2"
                )
                
                if not search_result:
                    return ServiceResponse(
                        status="success",
                        message="No memories found matching the filters",
                        data={"deleted_count": 0, "memories_found": 0},
                        metadata={
                            "strategy": "filtered",
                            "filters": filters
                        }
                    )
                
                # Extract memory IDs
                memory_ids = [memory.get('id') for memory in search_result if memory.get('id')]
                
                if not memory_ids:
                    return ServiceResponse(
                        status="error",
                        message="Found memories but could not extract valid IDs"
                    )
                
                # Perform batch delete
                delete_result = await client.batch_delete_memories(memory_ids=memory_ids)
                
            return ServiceResponse(
                status="success",
                message=f"Filtered delete completed: {len(memory_ids)} memories deleted",
                data={
                    "deleted_count": len(memory_ids),
                    "memories_found": len(search_result),
                    "deleted_memory_ids": memory_ids,
                    "delete_result": delete_result
                },
                metadata={
                    "strategy": "filtered",
                    "filters": filters,
                    "query_used": arguments.get('query', '*')
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Filtered delete strategy failed: {str(e)}"
            )


class DeleteMemoryService(BaseService):
    """Delete Memory microservice with multiple deletion strategies"""
    
    def _initialize_strategies(self) -> None:
        """Initialize all available strategies for memory deletion"""
        self.register_strategy(SingleDeleteStrategy())
        self.register_strategy(BatchDeleteStrategy())
        self.register_strategy(FilteredDeleteStrategy())