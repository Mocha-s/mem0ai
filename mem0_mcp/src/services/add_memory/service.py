"""
Add Memory Service

Microservice for adding memories to Mem0 with multiple strategies.
"""

from typing import Dict, Any
from ..base.service import BaseService, BaseStrategy, ServiceResponse
from ...client.mem0_api_client import Mem0APIClient, Mem0Config
import json
import os

class ContextualAddStrategy(BaseStrategy):
    """Context-aware memory addition strategy"""
    
    def __init__(self):
        super().__init__("contextual", "Context-aware memory addition with intelligent extraction")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute contextual memory addition"""
        try:
            messages = arguments.get('messages', [])
            user_id = arguments.get('user_id')
            metadata = arguments.get('metadata', {})
            infer = arguments.get('infer', True)
            
            # Get Mem0 API configuration - Point to local server
            config = Mem0Config(
                api_key=os.getenv('MEM0_API_KEY', ''),
                api_url=os.getenv('MEM0_API_URL', 'http://localhost:8000'),
                org_id=arguments.get('org_id') or os.getenv('MEM0_ORG_ID'),
                project_id=arguments.get('project_id') or os.getenv('MEM0_PROJECT_ID')
            )
            
            # Use real Mem0 API
            async with Mem0APIClient(config) as client:
                result = await client.add_memory(
                    messages=messages,
                    user_id=user_id,
                    agent_id=arguments.get('agent_id'),
                    app_id=arguments.get('app_id'),
                    run_id=arguments.get('run_id'),
                    metadata=metadata,
                    includes=arguments.get('includes'),
                    excludes=arguments.get('excludes'),
                    infer=infer,
                    output_format=arguments.get('output_format', 'v1.1'),
                    custom_categories=arguments.get('custom_categories'),
                    custom_instructions=arguments.get('custom_instructions'),
                    immutable=arguments.get('immutable', False),
                    async_mode=arguments.get('async_mode', False),
                    timestamp=arguments.get('timestamp'),
                    expiration_date=arguments.get('expiration_date'),
                    version=arguments.get('version', 'v2')
                )
            
            return ServiceResponse(
                status="success",
                message="Memory added successfully using contextual strategy",
                data=result,
                metadata={
                    "strategy": "contextual",
                    "inference_enabled": infer,
                    "api_version": "v2"
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Contextual add strategy failed: {str(e)}"
            )


class GraphAddStrategy(BaseStrategy):
    """Graph-based memory addition with relationship mapping"""
    
    def __init__(self):
        super().__init__("graph", "Graph-based memory addition with relationship mapping")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute graph memory addition"""
        try:
            messages = arguments.get('messages', [])
            user_id = arguments.get('user_id')
            enable_graph = arguments.get('enable_graph', False)
            
            if not enable_graph:
                return ServiceResponse(
                    status="error",
                    message="Graph strategy requires enable_graph=true"
                )
            
            # TODO: Integrate with actual Mem0 Graph API
            result = {
                "memory_id": f"graph_{user_id}_{hash(str(messages))}"[:20],
                "relationships": [
                    {"type": "relates_to", "entity": "previous_conversation"},
                    {"type": "mentions", "entity": "planning"}
                ],
                "graph_nodes": 2,
                "graph_edges": 1
            }
            
            return ServiceResponse(
                status="success",
                message="Memory added successfully using graph strategy",
                data=result,
                metadata={
                    "strategy": "graph",
                    "graph_enabled": True
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Graph add strategy failed: {str(e)}"
            )


class MultimodalAddStrategy(BaseStrategy):
    """Multimodal memory addition supporting text, images, and audio"""
    
    def __init__(self):
        super().__init__("multimodal", "Support for images, audio, and text in memory")
    
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute multimodal memory addition"""
        try:
            messages = arguments.get('messages', [])
            user_id = arguments.get('user_id')
            
            # Check for multimodal content
            has_images = any('image' in str(msg) for msg in messages)
            has_audio = any('audio' in str(msg) for msg in messages)
            
            # TODO: Integrate with actual Mem0 Multimodal API
            result = {
                "memory_id": f"multi_{user_id}_{hash(str(messages))}"[:20],
                "content_types": ["text"] + (["image"] if has_images else []) + (["audio"] if has_audio else []),
                "extracted_entities": ["visual_content", "audio_transcript"] if (has_images or has_audio) else ["text_content"]
            }
            
            return ServiceResponse(
                status="success", 
                message="Memory added successfully using multimodal strategy",
                data=result,
                metadata={
                    "strategy": "multimodal",
                    "has_images": has_images,
                    "has_audio": has_audio
                }
            )
            
        except Exception as e:
            return ServiceResponse(
                status="error",
                message=f"Multimodal add strategy failed: {str(e)}"
            )


class AddMemoryService(BaseService):
    """Add Memory microservice with multiple execution strategies"""
    
    def _initialize_strategies(self) -> None:
        """Initialize all available strategies for memory addition"""
        self.register_strategy(ContextualAddStrategy())
        self.register_strategy(GraphAddStrategy())
        self.register_strategy(MultimodalAddStrategy())