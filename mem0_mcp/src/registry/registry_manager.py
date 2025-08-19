"""
Tool Registry Manager

Manages dynamic service registration and discovery for Mem0 MCP tools.
"""

import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path
import importlib
from dataclasses import dataclass
from enum import Enum

class ServiceCategory(Enum):
    MEMORY = "memory"
    AGGREGATED = "aggregated" 
    SPECIALIZED = "specialized"

@dataclass
class ServiceStrategy:
    name: str
    description: str
    default: bool = False

@dataclass 
class ServiceConfig:
    name: str
    title: str
    description: str
    version: str
    category: ServiceCategory
    endpoint: str
    strategies: List[ServiceStrategy]
    schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    dependencies: List[str]
    health_check: str
    metrics: str

class RegistryManager:
    """Tool Registry管理器，负责服务注册、发现和验证"""
    
    def __init__(self, registry_path: str = "src/registry/tools.json"):
        self.registry_path = Path(registry_path)
        self._services: Dict[str, ServiceConfig] = {}
        self._service_instances: Dict[str, Any] = {}
        self.global_config = {}
        self.load_registry()
    
    def load_registry(self) -> None:
        """从tools.json加载服务注册表"""
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            
            self.global_config = registry_data.get('global_config', {})
            
            for service_name, service_data in registry_data.get('services', {}).items():
                strategies = [
                    ServiceStrategy(
                        name=s['name'],
                        description=s['description'],
                        default=s.get('default', False)
                    ) for s in service_data.get('strategies', [])
                ]
                
                config = ServiceConfig(
                    name=service_data['name'],
                    title=service_data['title'],
                    description=service_data['description'],
                    version=service_data['version'],
                    category=ServiceCategory(service_data['category']),
                    endpoint=service_data['endpoint'],
                    strategies=strategies,
                    schema=service_data['schema'],
                    output_schema=service_data['output_schema'],
                    dependencies=service_data.get('dependencies', []),
                    health_check=service_data.get('health_check', '/health'),
                    metrics=service_data.get('metrics', '/metrics')
                )
                
                self._services[service_name] = config
                
        except FileNotFoundError:
            raise RuntimeError(f"Registry file not found: {self.registry_path}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in registry file: {e}")
    
    def register_service(self, service_config: ServiceConfig) -> None:
        """动态注册新服务"""
        self._services[service_config.name] = service_config
        
        # 更新registry文件
        self._save_registry()
    
    def discover_services(self) -> List[str]:
        """发现所有可用服务"""
        return list(self._services.keys())
    
    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """获取服务配置"""
        return self._services.get(service_name)
    
    def get_services_by_category(self, category: ServiceCategory) -> List[ServiceConfig]:
        """根据类别获取服务列表"""
        return [
            config for config in self._services.values()
            if config.category == category
        ]
    
    def validate_service_dependencies(self, service_name: str) -> bool:
        """验证服务依赖是否满足"""
        config = self.get_service_config(service_name)
        if not config:
            return False
            
        for dep in config.dependencies:
            if dep not in self._services:
                return False
        return True
    
    def get_service_instance(self, service_name: str) -> Optional[Any]:
        """获取服务实例，如果不存在则动态加载"""
        if service_name in self._service_instances:
            return self._service_instances[service_name]
        
        config = self.get_service_config(service_name)
        if not config:
            return None
        
        # 动态加载服务类
        try:
            module_path, class_name = config.endpoint.split(':')
            module = importlib.import_module(module_path)
            service_class = getattr(module, class_name)
            
            # 实例化服务
            service_instance = service_class(config=config)
            self._service_instances[service_name] = service_instance
            
            return service_instance
            
        except (ImportError, AttributeError) as e:
            raise RuntimeError(f"Failed to load service {service_name}: {e}")
    
    def get_default_strategy(self, service_name: str) -> Optional[str]:
        """获取服务的默认策略"""
        config = self.get_service_config(service_name)
        if not config:
            return None
            
        for strategy in config.strategies:
            if strategy.default:
                return strategy.name
        
        # 如果没有明确的默认策略，返回第一个
        return config.strategies[0].name if config.strategies else None
    
    def validate_service_schema(self, service_name: str, arguments: Dict[str, Any]) -> bool:
        """验证服务调用参数是否符合Schema"""
        config = self.get_service_config(service_name)
        if not config:
            return False
        
        # 这里应该实现JSON Schema验证
        # 为简化，暂时返回True
        return True
    
    def get_service_health_status(self, service_name: str) -> bool:
        """获取服务健康状态"""
        # 这里应该实现实际的健康检查
        # 为简化，暂时返回True
        return True
    
    def _save_registry(self) -> None:
        """保存注册表到文件"""
        registry_data = {
            "version": "2.0",
            "metadata": {
                "created": "2025-08-19",
                "description": "Mem0 MCP Tool Services Registry",
                "protocol_version": "2025-06-18"
            },
            "services": {},
            "global_config": self.global_config
        }
        
        for service_name, config in self._services.items():
            registry_data["services"][service_name] = {
                "name": config.name,
                "title": config.title,
                "description": config.description,
                "version": config.version,
                "category": config.category.value,
                "endpoint": config.endpoint,
                "strategies": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "default": s.default
                    } for s in config.strategies
                ],
                "schema": config.schema,
                "output_schema": config.output_schema,
                "dependencies": config.dependencies,
                "health_check": config.health_check,
                "metrics": config.metrics
            }
        
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(registry_data, f, indent=2, ensure_ascii=False)

# 全局注册表实例
registry = RegistryManager()