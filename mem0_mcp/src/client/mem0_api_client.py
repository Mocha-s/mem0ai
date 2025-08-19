"""
Mem0 API Client

HTTP client for interacting with Mem0 platform APIs.
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Mem0Config:
    """Configuration for Mem0 API client"""
    api_key: str
    api_url: str = "http://localhost:8000"  # Local Mem0 API server
    org_id: Optional[str] = None
    project_id: Optional[str] = None
    timeout: int = 60  # Increased timeout for complex memory operations

class Mem0APIClient:
    """Asynchronous client for Mem0 Platform API"""
    
    def __init__(self, config: Mem0Config):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Only add authorization header if api_key is provided and not empty
        self.headers = {"Content-Type": "application/json"}
        if config.api_key and config.api_key.strip():
            self.headers["Authorization"] = f"Token {config.api_key}"
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """Initialize HTTP session"""
        if not self.session:
            # Use larger connection limits for better performance
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection pool size
                limit_per_host=30,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
            )
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=10,  # Connection timeout
                sock_read=self.config.timeout  # Socket read timeout
            )
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
            logger.info("Connected to Mem0 API")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("Disconnected from Mem0 API")
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to Mem0 API"""
        if not self.session:
            await self.connect()
        
        url = f"{self.config.api_url}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.request(method, url, headers=self.headers, **kwargs) as response:
                if response.status == 204:
                    return {"message": "Success", "status_code": 204}
                
                response_data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"API error {response.status}: {response_data}")
                    raise Exception(f"Mem0 API error {response.status}: {response_data}")
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise Exception(f"HTTP client error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise Exception(f"Invalid JSON response: {e}")
    
    # Memory Operations
    
    async def add_memory(
        self,
        messages: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        includes: Optional[str] = None,
        excludes: Optional[str] = None,
        infer: bool = True,
        output_format: str = "v1.1",
        custom_categories: Optional[Dict[str, Any]] = None,
        custom_instructions: Optional[str] = None,
        immutable: bool = False,
        async_mode: bool = False,
        timestamp: Optional[int] = None,
        expiration_date: Optional[str] = None,
        version: str = "v2"  # This is parameter version, not API version
    ) -> List[Dict[str, Any]]:
        """Add memories to Mem0 using v1 API endpoint"""
        
        payload = {
            "messages": messages,
            "infer": infer,
            "output_format": output_format,
            "immutable": immutable,
            "async_mode": async_mode,
            "version": version  # This parameter controls processing, not API endpoint
        }
        
        # Add optional parameters
        optional_params = {
            "user_id": user_id,
            "agent_id": agent_id,
            "app_id": app_id,
            "run_id": run_id,
            "metadata": metadata,
            "includes": includes,
            "excludes": excludes,
            "custom_categories": custom_categories,
            "custom_instructions": custom_instructions,
            "timestamp": timestamp,
            "expiration_date": expiration_date,
            "org_id": self.config.org_id,
            "project_id": self.config.project_id
        }
        
        for key, value in optional_params.items():
            if value is not None:
                payload[key] = value
        
        # NOTE: Add Memory API only supports v1 endpoint
        return await self._request("POST", "/v1/memories/", json=payload)
    
    async def search_memories(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        fields: Optional[List[str]] = None,
        rerank: bool = False,
        keyword_search: bool = False,
        filter_memories: bool = False,
        threshold: float = 0.3,
        version: str = "v2"
    ) -> List[Dict[str, Any]]:
        """Search memories using v2 API"""
        
        payload = {
            "query": query,
            "filters": filters or {},
            "top_k": top_k,
            "rerank": rerank,
            "keyword_search": keyword_search,
            "filter_memories": filter_memories,
            "threshold": threshold
        }
        
        # Add optional parameters
        if fields:
            payload["fields"] = fields
        if self.config.org_id:
            payload["org_id"] = self.config.org_id
        if self.config.project_id:
            payload["project_id"] = self.config.project_id
        
        return await self._request("POST", "/v2/memories/search/", json=payload)
    
    async def update_memory(
        self,
        memory_id: str,
        text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update a specific memory"""
        
        payload = {}
        if text is not None:
            payload["text"] = text
        if metadata is not None:
            payload["metadata"] = metadata
        
        return await self._request("PUT", f"/v1/memories/{memory_id}/", json=payload)
    
    async def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a specific memory"""
        return await self._request("DELETE", f"/v1/memories/{memory_id}/")
    
    async def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """Get a specific memory by ID"""
        return await self._request("GET", f"/v1/memories/{memory_id}/")
    
    async def get_all_memories(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        app_id: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 100,
        version: str = "v2"
    ) -> List[Dict[str, Any]]:
        """Get all memories with filters"""
        
        params = {"limit": limit, "version": version}
        
        # Add filters
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if agent_id:
            filters["agent_id"] = agent_id
        if app_id:
            filters["app_id"] = app_id
        if run_id:
            filters["run_id"] = run_id
        if self.config.org_id:
            params["org_id"] = self.config.org_id
        if self.config.project_id:
            params["project_id"] = self.config.project_id
        
        if filters:
            params.update(filters)
        
        return await self._request("GET", "/v2/memories/", params=params)
    
    async def batch_delete_memories(
        self,
        memory_ids: List[str]
    ) -> Dict[str, Any]:
        """Batch delete multiple memories"""
        payload = {"memory_ids": memory_ids}
        return await self._request("POST", "/v1/memories/batch/delete/", json=payload)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        try:
            # Use the memories endpoint with minimal parameters to test API availability
            response = await self._request("GET", "/v1/memories/", params={"limit": 1}, timeout=5)
            return {"status": "healthy", "api_accessible": True}
        except Exception as e:
            error_str = str(e)
            if "At least one identifier is required" in error_str:
                # This error means API is accessible but we need proper parameters
                return {"status": "healthy", "api_accessible": True, "note": "API accessible, authentication working"}
            return {"status": "unhealthy", "error": error_str, "api_accessible": False}