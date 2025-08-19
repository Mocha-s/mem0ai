"""
Base Service Classes

Provides the foundation for all tool microservices in the Mem0 MCP architecture.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

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
            
            # Convert to dict format
            result = {
                "status": response.status,
                "message": response.message
            }
            
            if response.data:
                result.update(response.data)
            
            if response.metadata:
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