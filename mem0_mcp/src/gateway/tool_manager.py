"""
Tool Manager - API Gateway for Mem0 MCP Services

Implements the service gateway pattern for routing tool calls to appropriate microservices.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
import json
import logging
from dataclasses import asdict

from registry.registry_manager import registry, ServiceConfig
from protocol.messages import ToolResult, ErrorResult

logger = logging.getLogger(__name__)

class ToolManager:
    """
    API Gateway for MCP tool services.
    
    Responsibilities:
    - Route tool calls to appropriate services
    - Provide service discovery and health checks
    - Implement circuit breaker and retry logic
    - Enable inter-service communication
    """
    
    def __init__(self):
        self.registry = registry
        self._circuit_breakers: Dict[str, 'CircuitBreaker'] = {}
        self._load_balancers: Dict[str, 'LoadBalancer'] = {}
        
    async def initialize(self) -> None:
        """Initialize the ToolManager and load all services"""
        logger.info("Initializing ToolManager...")
        
        # Initialize circuit breakers for all services
        for service_name in self.registry.discover_services():
            self._circuit_breakers[service_name] = CircuitBreaker(
                failure_threshold=self.registry.global_config.get('circuit_breaker', {}).get('failure_threshold', 5),
                reset_timeout=self.registry.global_config.get('circuit_breaker', {}).get('reset_timeout_seconds', 60)
            )
        
        logger.info(f"Initialized ToolManager with {len(self.registry.discover_services())} services")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Union[ToolResult, ErrorResult]:
        """
        Main entry point for tool calls.
        Routes requests to appropriate service instances.
        """
        try:
            # 验证服务是否存在
            service_config = self.registry.get_service_config(tool_name)
            if not service_config:
                return ErrorResult(
                    error_code=-32601,
                    error_message=f"Tool '{tool_name}' not found",
                    error_data={"available_tools": self.registry.discover_services()}
                )
            
            # 验证依赖
            if not self.registry.validate_service_dependencies(tool_name):
                return ErrorResult(
                    error_code=-32602,
                    error_message=f"Service dependencies not satisfied for '{tool_name}'",
                    error_data={"dependencies": service_config.dependencies}
                )
            
            # 验证参数Schema
            if not self.registry.validate_service_schema(tool_name, arguments):
                return ErrorResult(
                    error_code=-32602,
                    error_message=f"Invalid arguments for tool '{tool_name}'",
                    error_data={"schema": service_config.schema}
                )
            
            # 检查Circuit Breaker状态
            circuit_breaker = self._circuit_breakers.get(tool_name)
            if circuit_breaker and not circuit_breaker.can_execute():
                return ErrorResult(
                    error_code=-32603,
                    error_message=f"Service '{tool_name}' is currently unavailable (circuit breaker open)",
                    error_data={"retry_after": circuit_breaker.get_retry_after()}
                )
            
            # 获取服务实例并执行
            service_instance = self.registry.get_service_instance(tool_name)
            if not service_instance:
                return ErrorResult(
                    error_code=-32603,
                    error_message=f"Failed to load service '{tool_name}'",
                    error_data={}
                )
            
            # 执行服务调用
            try:
                result = await service_instance.execute(arguments, tool_manager=self)
                
                # 记录成功调用
                if circuit_breaker:
                    circuit_breaker.record_success()
                
                return ToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False)
                    }],
                    structured_content=result,
                    is_error=result.get('status') != 'success'
                )
                
            except Exception as e:
                # 记录失败调用
                if circuit_breaker:
                    circuit_breaker.record_failure()
                
                logger.error(f"Service execution failed for {tool_name}: {e}")
                return ErrorResult(
                    error_code=-32603,
                    error_message=f"Service execution failed: {str(e)}",
                    error_data={"service": tool_name}
                )
                
        except Exception as e:
            logger.error(f"ToolManager call_tool failed: {e}")
            return ErrorResult(
                error_code=-32603,
                error_message=f"Internal error: {str(e)}",
                error_data={}
            )
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """Return list of available tools for MCP client"""
        tools = []
        
        for service_name in self.registry.discover_services():
            config = self.registry.get_service_config(service_name)
            if config:
                tools.append({
                    "name": config.name,
                    "title": config.title,
                    "description": config.description,
                    "inputSchema": config.schema,
                    "outputSchema": config.output_schema
                })
        
        return tools
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of all services"""
        health_status = {}
        
        for service_name in self.registry.discover_services():
            try:
                is_healthy = self.registry.get_service_health_status(service_name)
                circuit_breaker = self._circuit_breakers.get(service_name)
                
                health_status[service_name] = {
                    "healthy": is_healthy,
                    "circuit_breaker_state": circuit_breaker.get_state() if circuit_breaker else "unknown",
                    "version": self.registry.get_service_config(service_name).version
                }
            except Exception as e:
                health_status[service_name] = {
                    "healthy": False,
                    "error": str(e)
                }
        
        return health_status
    
    async def discover_services_by_category(self, category: str) -> List[str]:
        """Discover services by category"""
        from registry.registry_manager import ServiceCategory
        try:
            cat_enum = ServiceCategory(category)
            services = self.registry.get_services_by_category(cat_enum)
            return [s.name for s in services]
        except ValueError:
            return []


class CircuitBreaker:
    """Circuit Breaker pattern implementation for service resilience"""
    
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if service can be executed"""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self) -> None:
        """Record successful execution"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self) -> None:
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def get_state(self) -> str:
        """Get current circuit breaker state"""
        return self.state
    
    def get_retry_after(self) -> Optional[int]:
        """Get seconds until retry is allowed"""
        if self.state == "open" and self.last_failure_time:
            elapsed = asyncio.get_event_loop().time() - self.last_failure_time
            return max(0, self.reset_timeout - int(elapsed))
        return None
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        if self.last_failure_time is None:
            return False
        
        elapsed = asyncio.get_event_loop().time() - self.last_failure_time
        return elapsed >= self.reset_timeout


class LoadBalancer:
    """Simple round-robin load balancer for service instances"""
    
    def __init__(self, service_instances: List[Any]):
        self.service_instances = service_instances
        self.current_index = 0
    
    def get_next_instance(self) -> Any:
        """Get next service instance using round-robin"""
        if not self.service_instances:
            return None
        
        instance = self.service_instances[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.service_instances)
        return instance


# Global ToolManager instance
tool_manager = ToolManager()