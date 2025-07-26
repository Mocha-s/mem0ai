"""
API version adapters for different Mem0 API versions
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .mem0_client import Mem0HTTPClient
from ..utils.errors import ToolExecutionError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseAdapter(ABC):
    """Base adapter for Mem0 API versions"""
    
    def __init__(self, client: Mem0HTTPClient):
        self.client = client
    
    @abstractmethod
    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Add memory from messages"""
        pass
    
    @abstractmethod
    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        """Search memories"""
        pass
    
    @abstractmethod
    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        """Get memories"""
        pass
    
    @abstractmethod
    async def get_memory_by_id(self, memory_id: str) -> Dict[str, Any]:
        """Get memory by ID"""
        pass
    
    @abstractmethod
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete memory by ID"""
        pass
    
    @abstractmethod
    async def update_memory(self, memory_id: str, data: str) -> Dict[str, Any]:
        """Update memory by ID"""
        pass
    
    @abstractmethod
    async def batch_delete_memories(self, **kwargs) -> Dict[str, Any]:
        """Batch delete memories"""
        pass


class V1Adapter(BaseAdapter):
    """Adapter for Mem0 V1 API"""
    
    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Add memory using V1 API
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Additional parameters (user_id, agent_id, run_id, metadata)
            
        Returns:
            V1 API response
        """
        try:
            payload = {
                "messages": messages,
                **kwargs
            }
            
            response = await self.client.post("memories", payload)
            logger.debug(f"V1 add_memory response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 add_memory failed: {str(e)}")
            raise ToolExecutionError(f"Failed to add memory: {str(e)}", "add_memory")
    
    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search memories using V1 API
        
        Args:
            query: Search query
            **kwargs: Additional parameters (user_id, agent_id, run_id, filters, limit)
            
        Returns:
            V1 API response
        """
        try:
            payload = {
                "query": query,
                **kwargs
            }
            
            response = await self.client.post("memories/search/", payload)
            logger.debug(f"V1 search_memories response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 search_memories failed: {str(e)}")
            raise ToolExecutionError(f"Failed to search memories: {str(e)}", "search_memories")
    
    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        """
        Get memories using V1 API
        
        Args:
            **kwargs: Parameters (user_id, agent_id, run_id)
            
        Returns:
            V1 API response
        """
        try:
            # V1 uses GET with query parameters
            response = await self.client.get("memories", params=kwargs)
            logger.debug(f"V1 get_memories response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 get_memories failed: {str(e)}")
            raise ToolExecutionError(f"Failed to get memories: {str(e)}", "get_memories")
    
    async def get_memory_by_id(self, memory_id: str) -> Dict[str, Any]:
        """
        Get memory by ID using V1 API
        
        Args:
            memory_id: Memory ID
            
        Returns:
            V1 API response
        """
        try:
            response = await self.client.get(f"memories/{memory_id}/")
            logger.debug(f"V1 get_memory_by_id response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 get_memory_by_id failed: {str(e)}")
            raise ToolExecutionError(f"Failed to get memory: {str(e)}", "get_memory_by_id")
    
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete memory by ID using V1 API
        
        Args:
            memory_id: Memory ID
            
        Returns:
            V1 API response
        """
        try:
            response = await self.client.delete(f"memories/{memory_id}/")
            logger.debug(f"V1 delete_memory response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 delete_memory failed: {str(e)}")
            raise ToolExecutionError(f"Failed to delete memory: {str(e)}", "delete_memory")
    
    async def update_memory(self, memory_id: str, data: str) -> Dict[str, Any]:
        """
        Update memory by ID using V1 API

        Args:
            memory_id: Memory ID
            data: New memory content

        Returns:
            V1 API response
        """
        try:
            payload = {
                "memory": data
            }
            
            response = await self.client.put(f"memories/{memory_id}/", payload)
            logger.debug(f"V1 update_memory response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 update_memory failed: {str(e)}")
            raise ToolExecutionError(f"Failed to update memory: {str(e)}", "update_memory")
    
    async def batch_delete_memories(self, **kwargs) -> Dict[str, Any]:
        """
        Batch delete memories using V1 API
        
        Args:
            **kwargs: Parameters (memory_ids: List[str] - required array of memory IDs)
            
        Returns:
            V1 API response
        """
        try:
            # 根据OpenAPI规范，batch delete需要memory_ids数组
            memory_ids = kwargs.get('memory_ids', [])
            
            if not memory_ids:
                raise ToolExecutionError(
                    "memory_ids parameter is required and must be a non-empty array of memory IDs", 
                    "batch_delete_memories"
                )
            
            payload = {
                "memory_ids": memory_ids  # 正确的参数名和格式
            }
            
            # 使用_make_request方法直接发送DELETE请求（因为需要请求体）
            response = await self.client._make_request("DELETE", "batch/", data=payload)
            logger.debug(f"V1 batch_delete_memories response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V1 batch_delete_memories failed: {str(e)}")
            raise ToolExecutionError(f"Failed to batch delete memories: {str(e)}", "batch_delete_memories")


class V2Adapter(BaseAdapter):
    """Adapter for Mem0 V2 API"""
    
    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Add memory using V2 API
        
        Args:
            messages: List of message objects with role and content
            **kwargs: Additional parameters (user_id, agent_id, run_id, metadata)
            
        Returns:
            V2 API response
        """
        try:
            # V2 API might have different format - adapt as needed
            payload = {
                "messages": messages,
                **kwargs
            }
            
            response = await self.client.post("memories", payload)
            logger.debug(f"V2 add_memory response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 add_memory failed: {str(e)}")
            raise ToolExecutionError(f"Failed to add memory: {str(e)}", "add_memory")
    
    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search memories using V2 API
        
        Args:
            query: Search query
            **kwargs: Additional parameters (filters, pagination, sort, etc.)
            
        Returns:
            V2 API response
        """
        try:
            payload = {
                "query": query,
                **kwargs
            }
            
            response = await self.client.post("memories/search/", payload)
            logger.debug(f"V2 search_memories response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 search_memories failed: {str(e)}")
            raise ToolExecutionError(f"Failed to search memories: {str(e)}", "search_memories")
    
    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        """
        Get memories using V2 API
        
        Args:
            **kwargs: Parameters (filters, pagination, sort, etc.)
            
        Returns:
            V2 API response
        """
        try:
            # V2 uses POST with JSON body for advanced filtering
            payload = kwargs
            
            response = await self.client.post("memories", payload)
            logger.debug(f"V2 get_memories response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 get_memories failed: {str(e)}")
            raise ToolExecutionError(f"Failed to get memories: {str(e)}", "get_memories")
    
    async def get_memory_by_id(self, memory_id: str) -> Dict[str, Any]:
        """
        Get memory by ID using V2 API
        
        Args:
            memory_id: Memory ID
            
        Returns:
            V2 API response
        """
        try:
            response = await self.client.get(f"memories/{memory_id}/")
            logger.debug(f"V2 get_memory_by_id response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 get_memory_by_id failed: {str(e)}")
            raise ToolExecutionError(f"Failed to get memory: {str(e)}", "get_memory_by_id")
    
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Delete memory by ID using V2 API
        
        Args:
            memory_id: Memory ID
            
        Returns:
            V2 API response
        """
        try:
            response = await self.client.delete(f"memories/{memory_id}/")
            logger.debug(f"V2 delete_memory response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 delete_memory failed: {str(e)}")
            raise ToolExecutionError(f"Failed to delete memory: {str(e)}", "delete_memory")
    
    async def update_memory(self, memory_id: str, data: str) -> Dict[str, Any]:
        """
        Update memory by ID using V2 API

        Args:
            memory_id: Memory ID
            data: New memory content

        Returns:
            V2 API response
        """
        try:
            payload = {
                "memory": data
            }
            
            response = await self.client.put(f"memories/{memory_id}/", payload)
            logger.debug(f"V2 update_memory response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 update_memory failed: {str(e)}")
            raise ToolExecutionError(f"Failed to update memory: {str(e)}", "update_memory")
    
    async def batch_delete_memories(self, **kwargs) -> Dict[str, Any]:
        """
        Batch delete memories using V2 API
        
        Args:
            **kwargs: Parameters (memory_ids: List[str] - required array of memory IDs)
            
        Returns:
            V2 API response
        """
        try:
            # 根据OpenAPI规范，batch delete需要memory_ids数组
            memory_ids = kwargs.get('memory_ids', [])
            
            if not memory_ids:
                raise ToolExecutionError(
                    "memory_ids parameter is required and must be a non-empty array of memory IDs", 
                    "batch_delete_memories"
                )
            
            payload = {
                "memory_ids": memory_ids  # 正确的参数名和格式
            }
            
            # 使用_make_request方法直接发送DELETE请求
            response = await self.client._make_request("DELETE", "batch/", data=payload)
            logger.debug(f"V2 batch_delete_memories response: {response}")
            return response
            
        except Exception as e:
            logger.error(f"V2 batch_delete_memories failed: {str(e)}")
            raise ToolExecutionError(f"Failed to batch delete memories: {str(e)}", "batch_delete_memories")