import time
import logging
import functools
from typing import Callable, Any, Dict, Optional
import os

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performance monitoring utilities for advanced retrieval components."""
    
    # Performance targets in milliseconds
    PERFORMANCE_TARGETS = {
        "BM25Search": 10,
        "LLMRerank": 200,
        "MemoryFilter": 300,
        "AdvancedRetrieval": 500,
    }
    
    # Configuration for performance monitoring
    _enabled = os.getenv("MEM0_PERFORMANCE_MONITORING", "true").lower() == "true"
    _log_level = os.getenv("MEM0_PERFORMANCE_LOG_LEVEL", "info").lower()
    
    @classmethod
    def is_enabled(cls) -> bool:
        """Check if performance monitoring is enabled."""
        return cls._enabled
    
    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        """Enable or disable performance monitoring."""
        cls._enabled = enabled
    
    @classmethod
    def get_target_latency(cls, component: str) -> int:
        """Get target latency for a component in milliseconds."""
        return cls.PERFORMANCE_TARGETS.get(component, 1000)
    
    @staticmethod
    def monitor_latency(component_name: str, target_ms: Optional[int] = None):
        """
        Decorator to monitor function execution latency.
        
        Args:
            component_name (str): Name of the component being monitored
            target_ms (Optional[int]): Target latency in milliseconds. If None, uses default from PERFORMANCE_TARGETS
        """
        if target_ms is None:
            target_ms = PerformanceMonitor.get_target_latency(component_name)
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                if not PerformanceMonitor.is_enabled():
                    return func(*args, **kwargs)
                
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    # Log performance based on target
                    if elapsed_ms > target_ms:
                        if PerformanceMonitor._log_level in ["warning", "error"]:
                            logger.warning(
                                f"{component_name} exceeded target latency: {elapsed_ms:.2f}ms > {target_ms}ms"
                            )
                    else:
                        if PerformanceMonitor._log_level in ["info", "debug"]:
                            logger.info(f"{component_name} completed in {elapsed_ms:.2f}ms")
                    
                    # Add performance metadata to result if it's a dict
                    if isinstance(result, list) and result and isinstance(result[0], dict):
                        # Add performance info to first result item
                        result[0]["_performance"] = {
                            "component": component_name,
                            "elapsed_ms": elapsed_ms,
                            "target_ms": target_ms,
                            "within_target": elapsed_ms <= target_ms
                        }
                    
                    return result
                    
                except Exception as e:
                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.error(f"{component_name} failed after {elapsed_ms:.2f}ms: {str(e)}")
                    raise
            
            return wrapper
        return decorator
    
    @staticmethod
    def monitor_async_latency(component_name: str, target_ms: Optional[int] = None):
        """
        Decorator to monitor async function execution latency.
        
        Args:
            component_name (str): Name of the component being monitored
            target_ms (Optional[int]): Target latency in milliseconds
        """
        if target_ms is None:
            target_ms = PerformanceMonitor.get_target_latency(component_name)
        
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                if not PerformanceMonitor.is_enabled():
                    return await func(*args, **kwargs)
                
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    elapsed_ms = (time.time() - start_time) * 1000
                    
                    # Log performance based on target
                    if elapsed_ms > target_ms:
                        if PerformanceMonitor._log_level in ["warning", "error"]:
                            logger.warning(
                                f"{component_name} exceeded target latency: {elapsed_ms:.2f}ms > {target_ms}ms"
                            )
                    else:
                        if PerformanceMonitor._log_level in ["info", "debug"]:
                            logger.info(f"{component_name} completed in {elapsed_ms:.2f}ms")
                    
                    # Add performance metadata to result if it's a dict
                    if isinstance(result, list) and result and isinstance(result[0], dict):
                        # Add performance info to first result item
                        result[0]["_performance"] = {
                            "component": component_name,
                            "elapsed_ms": elapsed_ms,
                            "target_ms": target_ms,
                            "within_target": elapsed_ms <= target_ms
                        }
                    
                    return result
                    
                except Exception as e:
                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.error(f"{component_name} failed after {elapsed_ms:.2f}ms: {str(e)}")
                    raise
            
            return wrapper
        return decorator


class PerformanceCollector:
    """Collect and aggregate performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    def record_metric(self, component: str, elapsed_ms: float, target_ms: int, success: bool = True):
        """Record a performance metric."""
        if component not in self.metrics:
            self.metrics[component] = []
        
        self.metrics[component].append({
            "elapsed_ms": elapsed_ms,
            "target_ms": target_ms,
            "success": success,
            "within_target": elapsed_ms <= target_ms,
            "timestamp": time.time()
        })
    
    def get_summary(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for a component or all components."""
        if component:
            if component not in self.metrics:
                return {}
            
            metrics = self.metrics[component]
            if not metrics:
                return {}
            
            elapsed_times = [m["elapsed_ms"] for m in metrics if m["success"]]
            if not elapsed_times:
                return {"component": component, "total_calls": len(metrics), "success_rate": 0}
            
            return {
                "component": component,
                "total_calls": len(metrics),
                "success_rate": sum(1 for m in metrics if m["success"]) / len(metrics),
                "avg_latency_ms": sum(elapsed_times) / len(elapsed_times),
                "min_latency_ms": min(elapsed_times),
                "max_latency_ms": max(elapsed_times),
                "within_target_rate": sum(1 for m in metrics if m["within_target"]) / len(metrics),
                "target_ms": metrics[0]["target_ms"] if metrics else 0
            }
        else:
            # Return summary for all components
            return {comp: self.get_summary(comp) for comp in self.metrics.keys()}
    
    def clear_metrics(self, component: Optional[str] = None):
        """Clear metrics for a component or all components."""
        if component:
            if component in self.metrics:
                self.metrics[component] = []
        else:
            self.metrics = {}


# Global performance collector instance
performance_collector = PerformanceCollector()
