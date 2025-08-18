"""
HTTP client for connecting to Mem0 services
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin, urlparse

import httpx
from httpx import AsyncClient, Response

from ..config.settings import MCPConfig
from ..config.constants import HTTP_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from ..utils.errors import TransportError, ToolExecutionError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Mem0HTTPClient:
    """
    Async HTTP client for Mem0 services with retry logic and error handling
    """
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.base_url = config.mem0_base_url.rstrip('/')
        self.api_version = config.mem0_api_version
        self.timeout = config.request_timeout or HTTP_TIMEOUT
        self.client: Optional[AsyncClient] = None
        
        # Validate base URL
        parsed = urlparse(self.base_url)
        if not parsed.scheme or not parsed.netloc:
            raise TransportError(f"Invalid Mem0 base URL: {self.base_url}")
        
        logger.info(f"Initialized Mem0 client for {self.base_url}/{self.api_version}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self) -> None:
        """Initialize HTTP client connection"""
        if self.client is None:
            self.client = AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=100
                )
            )
            logger.debug("HTTP client connected")
    
    async def close(self) -> None:
        """Close HTTP client connection"""
        if self.client:
            await self.client.aclose()
            self.client = None
            logger.debug("HTTP client closed")
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL for API endpoint"""
        # Remove leading slash from endpoint if present
        endpoint = endpoint.lstrip('/')
        
        # Handle v2 endpoints explicitly (they already include version in path)
        if endpoint.startswith('v2/'):
            return f"{self.base_url}/{endpoint}"
        else:
            # Use configured API version for v1 endpoints
            return f"{self.base_url}/{self.api_version}/{endpoint}"
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body data (for POST/PUT)
            params: Query parameters (for GET)
            retry_count: Current retry attempt
            
        Returns:
            Response data as dictionary
            
        Raises:
            TransportError: If request fails after all retries
        """
        if not self.client:
            await self.connect()
        
        url = self._build_url(endpoint)
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            # Prepare request arguments
            request_kwargs = {
                "method": method,
                "url": url,
                "headers": {"Content-Type": "application/json"}
            }
            
            if data is not None:
                request_kwargs["json"] = data
            
            if params is not None:
                request_kwargs["params"] = params
            
            # Make request
            response: Response = await self.client.request(**request_kwargs)
            
            # Handle response
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # Handle empty or non-JSON responses
                    return {"success": True, "message": "Operation completed"}
            
            # Handle HTTP errors
            error_data = {}
            try:
                error_data = response.json()
            except json.JSONDecodeError:
                error_data = {"error": response.text or "Unknown error"}
            
            error_message = error_data.get("error", f"HTTP {response.status_code}: {response.reason_phrase}")
            
            logger.warning(f"Request failed: {error_message} (status: {response.status_code})")
            
            # Don't retry client errors (4xx), only server errors (5xx) and timeouts
            if response.status_code >= 400 and response.status_code < 500:
                raise TransportError(
                    f"Client error: {error_message}",
                    data={"status_code": response.status_code, "response": error_data}
                )
            
            # Retry on server errors
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self._make_request(method, endpoint, data, params, retry_count + 1)
            
            raise TransportError(
                f"Server error after {MAX_RETRIES} retries: {error_message}",
                data={"status_code": response.status_code, "response": error_data}
            )
            
        except httpx.TimeoutException:
            logger.warning(f"Request timeout for {url}")
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self._make_request(method, endpoint, data, params, retry_count + 1)
            raise TransportError(f"Request timeout after {MAX_RETRIES} retries")
        
        except httpx.RequestError as e:
            logger.error(f"Request error: {str(e)}")
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * (retry_count + 1))
                return await self._make_request(method, endpoint, data, params, retry_count + 1)
            raise TransportError(f"Request error after {MAX_RETRIES} retries: {str(e)}")
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request"""
        return await self._make_request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request"""
        return await self._make_request("POST", endpoint, data=data, params=params)
    
    async def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._make_request("PUT", endpoint, data=data)
    
    async def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._make_request("DELETE", endpoint, params=params)
    
    async def health_check(self) -> bool:
        """
        Check if Mem0 service is healthy
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.get("health")
            return response.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False

    # --- Domain-specific convenience methods ---
    async def add_memory(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Add memories (v1). Maps to POST /v1/memories/
        """
        payload: Dict[str, Any] = {"messages": messages}
        passthrough_keys = [
            "user_id", "agent_id", "run_id", "metadata",
            "custom_categories", "custom_instructions", "version",
            "includes", "excludes", "timestamp", "enable_graph", "output_format"
        ]
        for key in passthrough_keys:
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        return await self.post("memories/", data=payload)

    async def add_memory_v2(self, messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Contextual add (v2 semantics). Server uses version="v2" on the same endpoint.
        """
        kwargs = {**kwargs, "version": "v2"}
        return await self.add_memory(messages, **kwargs)

    async def search_memories(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search memories (v1). Maps to POST /v1/memories/search/
        """
        payload: Dict[str, Any] = {"query": query}
        passthrough_keys = [
            "user_id", "agent_id", "run_id", "filters",
            "keyword_search", "rerank", "filter_memories",
            "enable_graph", "output_format", "limit"
        ]
        for key in passthrough_keys:
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        return await self.post("memories/search/", data=payload)

    async def search_memories_v2(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search memories (v2). Maps to POST /v2/memories/search/
        """
        filters: Dict[str, Any] = dict(kwargs.get("filters") or {})
        for id_key in ("user_id", "agent_id", "run_id"):
            if id_key in kwargs and kwargs[id_key] is not None:
                filters[id_key] = kwargs[id_key]
        payload: Dict[str, Any] = {
            "query": query,
            "filters": filters or None,
            "limit": kwargs.get("limit") or 50,
            "keyword_search": kwargs.get("keyword_search"),
            "rerank": kwargs.get("rerank"),
            "filter_memories": kwargs.get("filter_memories"),
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        return await self.post("v2/memories/search/", data=payload)

    async def get_memories(self, **kwargs) -> Dict[str, Any]:
        """
        Get memories (v1). Maps to GET /v1/memories/
        """
        params: Dict[str, Any] = {}
        for key in ("user_id", "agent_id", "run_id", "limit", "enable_graph", "output_format"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        return await self.get("memories/", params=params)

    async def get_memories_v2(self, **kwargs) -> Dict[str, Any]:
        """
        Get memories (v2). Maps to POST /v2/memories/
        """
        filters: Dict[str, Any] = dict(kwargs.get("filters") or {})
        for id_key in ("user_id", "agent_id", "run_id"):
            if id_key in kwargs and kwargs[id_key] is not None:
                filters[id_key] = kwargs[id_key]
        payload: Dict[str, Any] = {
            "filters": filters or None,
            "limit": kwargs.get("limit") or 50,
        }
        return await self.post("v2/memories/", data=payload)

    async def update_memory(self, memory_id: str, text: str, **kwargs) -> Dict[str, Any]:
        """Update a memory (v1). PUT /v1/memories/{memory_id}/"""
        payload: Dict[str, Any] = {"text": text}
        if "metadata" in kwargs and kwargs["metadata"] is not None:
            payload["metadata"] = kwargs["metadata"]
        return await self.put(f"memories/{memory_id}/", data=payload)

    async def delete_memory(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        """Delete a memory (v1). DELETE /v1/memories/{memory_id}/"""
        return await self.delete(f"memories/{memory_id}/")

    async def get_memory_by_id(self, memory_id: str, **kwargs) -> Dict[str, Any]:
        """Get a memory by ID (v1). GET /v1/memories/{memory_id}/"""
        return await self.get(f"memories/{memory_id}/")

    async def batch_operations(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Batch operations (v1). Maps to /v1/batch/ endpoint
        Supports both batch_update and batch_delete operations
        """
        # 根据操作类型确定HTTP方法和数据结构
        if operation == "batch_update":
            # 批量更新 - PUT /v1/batch/
            payload = {
                "updates": kwargs.get("updates", []),
                "user_id": kwargs.get("user_id"),
            }
            return await self.put("batch/", data=payload)
        
        elif operation == "batch_delete":
            # 批量删除 - DELETE /v1/batch/
            payload = {
                "memory_ids": kwargs.get("memory_ids", []),
                "user_id": kwargs.get("user_id"),
            }
            return await self.delete("batch/", data=payload)
        
        elif operation == "analyze_batch":
            # 分析批处理操作（自定义操作，返回可用的批处理选项）
            return {
                "available_operations": ["batch_update", "batch_delete"],
                "endpoints": {
                    "batch_update": "/v1/batch/ (PUT)",
                    "batch_delete": "/v1/batch/ (DELETE)"
                },
                "user_id": kwargs.get("user_id"),
                "status": "success"
            }
        
        else:
            raise ValueError(f"Unsupported batch operation: {operation}")

    async def batch_operations_v2(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Batch operations (v2). Enhanced version with additional features
        """
        # V2版本可以添加更多高级功能
        return await self.batch_operations(operation, **kwargs)