"""
Update Memory Service

Microservice for updating memories in Mem0 with multiple strategies.
"""

from typing import Dict, Any, Optional
from ..base.service import BaseService, BaseStrategy, ServiceResponse
from ...client.mem0_api_client import Mem0APIClient, Mem0Config
import os

class SingleUpdateStrategy(BaseStrategy):
    """Update a single memory by ID"""
    
    def __init__(self):
        super().__init__("single", "Update a single memory by ID")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute single memory update"""
        try:
            memory_id = arguments.get('memory_id')
            if not memory_id:
                return ServiceResponse(
                    status="error",
                    message="memory_id is required for single update strategy"
                )
            
            text = arguments.get('text')
            metadata = arguments.get('metadata')
            
            if not text and not metadata:
                return ServiceResponse(
                    status="error",
                    message="Either text or metadata must be provided for update"
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
                result = await client.update_memory(
                    memory_id=memory_id,
                    text=text,
                    metadata=metadata
                )
            
            return ServiceResponse(
                status="success",
                message="Memory updated successfully using single strategy",
                data=result,
                metadata={
                    "strategy": "single",
                    "memory_id": memory_id,
                    "updated_text": bool(text),
                    "updated_metadata": bool(metadata)
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Single update strategy failed: {str(e)}"
            )


class BatchUpdateStrategy(BaseStrategy):
    """Update multiple memories in batch"""
    
    def __init__(self):
        super().__init__("batch", "Update multiple memories in a single operation")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute batch memory update"""
        try:
            updates = arguments.get('updates', [])
            if not updates:
                return ServiceResponse(
                    status="error",
                    message="updates list is required for batch strategy"
                )
            
            if len(updates) > 1000:
                return ServiceResponse(
                    status="error",
                    message="Batch update limited to 1000 memories maximum"
                )
            
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            # Process batch updates
            successful_updates = []
            failed_updates = []
            
            async with Mem0APIClient(config) as client:
                for update in updates:
                    try:
                        memory_id = update.get('memory_id')
                        if not memory_id:
                            failed_updates.append({
                                "update": update,
                                "error": "memory_id is required"
                            })
                            continue
                        
                        result = await client.update_memory(
                            memory_id=memory_id,
                            text=update.get('text'),
                            metadata=update.get('metadata')
                        )
                        
                        successful_updates.append({
                            "memory_id": memory_id,
                            "result": result
                        })
                        
                    except Exception as e:
                        failed_updates.append({
                            "memory_id": update.get('memory_id'),
                            "update": update,
                            "error": str(e)
                        })
            
            status = "success" if len(failed_updates) == 0 else "partial"
            if len(successful_updates) == 0:
                status = "error"
            
            return ServiceResponse(
                status=status,
                message=f"Batch update completed: {len(successful_updates)} successful, {len(failed_updates)} failed",
                data={
                    "successful_updates": successful_updates,
                    "failed_updates": failed_updates,
                    "total_requested": len(updates),
                    "successful_count": len(successful_updates),
                    "failed_count": len(failed_updates)
                },
                metadata={
                    "strategy": "batch",
                    "batch_size": len(updates)
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Batch update strategy failed: {str(e)}"
            )


class UpdateMemoryService(BaseService):
    """Update Memory microservice with multiple update strategies"""
    
    def _initialize_strategies(self) -> None:
        """Initialize all available strategies for memory update"""
        self.register_strategy(SingleUpdateStrategy())
        self.register_strategy(BatchUpdateStrategy())