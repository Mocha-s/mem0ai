from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from fastapi import Depends
from ..config.settings import get_mcp_config, MCPConfig
from ..client.mem0_client import Mem0HTTPClient


class BaseAdapter(ABC):
    """Base adapter interface for memory operations"""

    @abstractmethod
    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def update_memory(self, memory_id: str, text: str, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def delete_memory(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def batch_operations(self, operation: str, **kwargs) -> Dict[str, Any]:
        pass


class V1Adapter(BaseAdapter):
    """V1 API adapter"""

    def __init__(self, client: Mem0HTTPClient):
        self.client = client

    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        return await self.client.add_memory(messages, **kwargs)

    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        return await self.client.search_memories(query, **kwargs)

    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        return await self.client.get_memories(**kwargs)

    async def update_memory(self, memory_id: str, text: str, **kwargs) -> Dict[str, Any]:
        return await self.client.update_memory(memory_id, text, **kwargs)

    async def delete_memory(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        return await self.client.delete_memory(memory_id, **kwargs)

    async def batch_operations(self, operation: str, **kwargs) -> Dict[str, Any]:
        return await self.client.batch_operations(operation, **kwargs)


class V2Adapter(BaseAdapter):
    """V2 API adapter with enhanced features"""

    def __init__(self, client: Mem0HTTPClient):
        self.client = client

    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        return await self.client.add_memory_v2(messages, **kwargs)

    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        return await self.client.search_memories_v2(query, **kwargs)

    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        return await self.client.get_memories_v2(**kwargs)

    async def update_memory(self, memory_id: str, text: str, **kwargs) -> Dict[str, Any]:
        return await self.client.update_memory_v2(memory_id, text, **kwargs)

    async def delete_memory(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        return await self.client.delete_memory_v2(memory_id, **kwargs)

    async def batch_operations(self, operation: str, **kwargs) -> Dict[str, Any]:
        return await self.client.batch_operations_v2(operation, **kwargs)


class HybridAdapter(BaseAdapter):
    """Hybrid adapter that combines V1 and V2 capabilities"""

    def __init__(self, client: Mem0HTTPClient):
        self.client = client
        self.v1_adapter = V1Adapter(client)
        self.v2_adapter = V2Adapter(client)

    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        # Use V2 for enhanced features, fallback to V1
        try:
            return await self.v2_adapter.add_memory(messages, **kwargs)
        except Exception:
            return await self.v1_adapter.add_memory(messages, **kwargs)

    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        try:
            return await self.v2_adapter.search_memories(query, **kwargs)
        except Exception:
            return await self.v1_adapter.search_memories(query, **kwargs)

    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        try:
            return await self.v2_adapter.get_memories(**kwargs)
        except Exception:
            return await self.v1_adapter.get_memories(**kwargs)

    async def update_memory(self, memory_id: str, text: str, **kwargs) -> Dict[str, Any]:
        try:
            return await self.v2_adapter.update_memory(memory_id, text, **kwargs)
        except Exception:
            return await self.v1_adapter.update_memory(memory_id, text, **kwargs)

    async def delete_memory(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        try:
            return await self.v2_adapter.delete_memory(memory_id, **kwargs)
        except Exception:
            return await self.v1_adapter.delete_memory(memory_id, **kwargs)

    async def batch_operations(self, operation: str, **kwargs) -> Dict[str, Any]:
        try:
            return await self.v2_adapter.batch_operations(operation, **kwargs)
        except Exception:
            return await self.v1_adapter.batch_operations(operation, **kwargs)


# This is a simplified dependency injection mechanism.
# In a real-world app, you might use a more robust system like FastAPI's Depends.

_adapter_instance = None

def get_adapter_instance(config: MCPConfig = Depends(get_mcp_config)) -> BaseAdapter:
    global _adapter_instance
    if _adapter_instance is None:
        mem0_client = Mem0HTTPClient(config)
        _adapter_instance = HybridAdapter(mem0_client)
    return _adapter_instance

# Alias for clarity in service files
get_adapter = get_adapter_instance
