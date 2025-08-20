"""
Base Service Classes

Provides the foundation for all tool microservices in the Mem0 MCP architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass 
class ServiceResponse:
    """Standardized service response format"""
    status: str  # success, error
    message: str
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseStrategy(ABC):
    """Base class for service execution strategies"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any], context: Dict[str, Any]) -> ServiceResponse:
        """Execute the strategy with given arguments and context"""
        pass
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """Validate strategy-specific arguments"""
        return True


class BaseService(ABC):
    """Base class for all tool microservices"""
    
    def __init__(self, config, tool_manager=None):
        self.config = config
        self.tool_manager = tool_manager
        self.strategies: Dict[str, BaseStrategy] = {}
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
        
        # Initialize strategies
        self._initialize_strategies()
    
    @abstractmethod
    def _initialize_strategies(self) -> None:
        """Initialize available strategies for this service"""
        pass
    
    def register_strategy(self, strategy: BaseStrategy) -> None:
        """Register a new strategy"""
        self.strategies[strategy.name] = strategy
        self.logger.info(f"Registered strategy: {strategy.name}")
    
    def get_strategy(self, strategy_name: Optional[str] = None) -> BaseStrategy:
        """Get strategy by name, or default strategy if none specified"""
        if strategy_name and strategy_name in self.strategies:
            return self.strategies[strategy_name]
        
        # Get default strategy from config
        for strategy_config in self.config.strategies:
            if strategy_config.default and strategy_config.name in self.strategies:
                return self.strategies[strategy_config.name]
        
        # Fallback to first available strategy
        if self.strategies:
            return next(iter(self.strategies.values()))
        
        raise RuntimeError(f"No strategies available for service {self.config.name}")
    
    async def execute(self, arguments: Dict[str, Any], tool_manager=None) -> Dict[str, Any]:
        """Main execution method for the service"""
        try:
            # Set tool_manager if provided
            if tool_manager:
                self.tool_manager = tool_manager
            
            # Validate arguments
            if not self._validate_arguments(arguments):
                return {
                    "status": "error",
                    "message": "Invalid arguments provided",
                    "data": {"arguments": arguments}
                }
            
            # Select strategy
            strategy_name = arguments.get('strategy')
            strategy = self.get_strategy(strategy_name)
            
            self.logger.info(f"Executing {self.config.name} with strategy: {strategy.name}")
            
            # Execute strategy
            context = {
                "service_name": self.config.name,
                "service_version": self.config.version,
                "tool_manager": self.tool_manager
            }
            
            response = await strategy.execute(arguments, context)
            
            # Convert to dict format with strict schema compliance
            result = {
                "status": response.status,
                "message": response.message
            }
            
            # Apply data with schema filtering for Dify strict compliance
            if response.data:
                result.update(response.data)
            
            # Filter response to match declared output_schema exactly
            # This ensures compatibility with strict MCP clients like Dify
            result = self._apply_output_schema_filter(result)
            
            # Add metadata only if not filtered out by schema compliance
            if response.metadata and not self._is_strict_schema_mode():
                result["_metadata"] = response.metadata
            
            return result
            
        except Exception as e:
            self.logger.error(f"Service execution failed: {e}")
            return {
                "status": "error", 
                "message": f"Service execution failed: {str(e)}",
                "error_type": type(e).__name__
            }
    
    def _validate_arguments(self, arguments: Dict[str, Any]) -> bool:
        """Validate service arguments against schema"""
        # Basic validation - should be enhanced with JSON schema validation
        required_fields = self.config.schema.get('required', [])
        
        for field in required_fields:
            if field not in arguments:
                self.logger.error(f"Missing required field: {field}")
                return False
        
        return True
    
    async def call_dependency_service(self, service_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call another service through the ToolManager"""
        if not self.tool_manager:
            raise RuntimeError("ToolManager not available for service calls")
        
        if service_name not in self.config.dependencies:
            raise RuntimeError(f"Service {service_name} is not a declared dependency")
        
        self.logger.info(f"Calling dependency service: {service_name}")
        result = await self.tool_manager.call_tool(service_name, arguments)
        
        if hasattr(result, 'is_error') and result.is_error:
            raise RuntimeError(f"Dependency service call failed: {result}")
        
        if hasattr(result, 'structured_content'):
            return result.structured_content
        
        return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint for the service"""
        try:
            # Basic health check - can be overridden by subclasses
            return {
                "status": "healthy",
                "service": self.config.name,
                "version": self.config.version,
                "strategies": list(self.strategies.keys())
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": self.config.name,
                "error": str(e)
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return {
            "service": self.config.name,
            "version": self.config.version,
            "strategies_count": len(self.strategies),
            "dependencies_count": len(self.config.dependencies)
        }
    
    def _is_strict_schema_mode(self) -> bool:
        """Check if strict schema compliance is enabled"""
        return os.getenv('MCP_STRICT_SCHEMA', 'true').lower() == 'true'
    
    def _apply_output_schema_filter(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Filter response to match declared output_schema exactly for strict MCP clients like Dify"""
        if not self._is_strict_schema_mode():
            return result
        
        try:
            # Load output schema from tools registry
            tools_registry_path = Path(__file__).parent.parent.parent / "registry" / "tools.json"
            if not tools_registry_path.exists():
                self.logger.warning(f"Tools registry not found at {tools_registry_path}, skipping schema filtering")
                return result
            
            with open(tools_registry_path, 'r') as f:
                tools_registry = json.load(f)
            
            service_config = tools_registry.get('services', {}).get(self.config.name)
            if not service_config or 'output_schema' not in service_config:
                self.logger.warning(f"No output_schema found for {self.config.name}, skipping schema filtering")
                return result
            
            output_schema = service_config['output_schema']
            schema_properties = output_schema.get('properties', {})
            
            # Filter result to only include properties declared in schema
            filtered_result = {}
            for key in schema_properties:
                if key in result:
                    filtered_result[key] = result[key]
                # Add default values for required fields if missing
                elif output_schema.get('required') and key in output_schema['required']:
                    if schema_properties[key].get('type') == 'array':
                        filtered_result[key] = []
                    elif schema_properties[key].get('type') == 'integer':
                        filtered_result[key] = 0
                    elif schema_properties[key].get('type') == 'string':
                        filtered_result[key] = ''
                    else:
                        filtered_result[key] = None
            
            self.logger.info(f"Schema filtering applied for {self.config.name}: {len(result)} -> {len(filtered_result)} fields")
            return filtered_result
            
        except Exception as e:
            self.logger.error(f"Schema filtering failed for {self.config.name}: {e}, returning original result")
            return result