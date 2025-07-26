"""
Context-based identity management for MCP server.

This module provides Context Variables based user identity management
similar to OpenMemory's approach, allowing session-level identity binding
without requiring explicit parameters in every tool call.
"""

import contextvars
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Context variables for user identity
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
agent_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("agent_id") 
run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id")
session_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("session_id")


@dataclass
class Identity:
    """User identity information"""
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def get_primary_id(self) -> str:
        """Get the primary identifier (user_id, agent_id, or run_id in that order)"""
        return self.user_id or self.agent_id or self.run_id or ""
    
    def is_valid(self) -> bool:
        """Check if at least one identity field is provided"""
        return bool(self.user_id or self.agent_id or self.run_id)


class IdentityManager:
    """Manages user identity context for MCP tools"""
    
    @staticmethod
    def set_identity(identity: Identity) -> Dict[str, contextvars.Token]:
        """Set identity context variables and return tokens for cleanup"""
        tokens = {}
        
        if identity.user_id:
            tokens['user_id'] = user_id_var.set(identity.user_id)
            
        if identity.agent_id:
            tokens['agent_id'] = agent_id_var.set(identity.agent_id)
            
        if identity.run_id:
            tokens['run_id'] = run_id_var.set(identity.run_id)
            
        if identity.session_id:
            tokens['session_id'] = session_id_var.set(identity.session_id)
            
        logger.debug(f"Set identity context: {identity}")
        return tokens
    
    @staticmethod
    def clear_identity(tokens: Dict[str, contextvars.Token]) -> None:
        """Clear identity context variables using tokens"""
        for var_name, token in tokens.items():
            try:
                if var_name == 'user_id':
                    user_id_var.reset(token)
                elif var_name == 'agent_id':
                    agent_id_var.reset(token)
                elif var_name == 'run_id':
                    run_id_var.reset(token)
                elif var_name == 'session_id':
                    session_id_var.reset(token)
            except LookupError:
                # Token was already reset, ignore
                pass
        
        logger.debug("Cleared identity context")
    
    @staticmethod
    def get_current_identity() -> Identity:
        """Get current identity from context variables"""
        return Identity(
            user_id=user_id_var.get(None),
            agent_id=agent_id_var.get(None),
            run_id=run_id_var.get(None),
            session_id=session_id_var.get(None)
        )
    
    @staticmethod
    def resolve_identity_from_arguments(arguments: Dict[str, Any]) -> Identity:
        """Extract identity from tool arguments (fallback for backward compatibility)"""
        return Identity(
            user_id=arguments.get('user_id'),
            agent_id=arguments.get('agent_id'),
            run_id=arguments.get('run_id')
        )
    
    @staticmethod
    def get_effective_identity(arguments: Dict[str, Any] = None) -> Identity:
        """
        Get effective identity by combining context and arguments.
        Context variables take precedence over arguments.
        """
        # Get from context first
        context_identity = IdentityManager.get_current_identity()
        
        # If arguments provided, use as fallback
        if arguments:
            args_identity = IdentityManager.resolve_identity_from_arguments(arguments)
            
            # Merge: context takes precedence
            return Identity(
                user_id=context_identity.user_id or args_identity.user_id,
                agent_id=context_identity.agent_id or args_identity.agent_id,
                run_id=context_identity.run_id or args_identity.run_id,
                session_id=context_identity.session_id
            )
        
        return context_identity


def require_identity(func):
    """Decorator to ensure identity is available in tool functions"""
    def wrapper(*args, **kwargs):
        identity = IdentityManager.get_effective_identity(kwargs.get('arguments', {}))
        if not identity.is_valid():
            raise ValueError("No user identity found. Please provide user_id, agent_id, or run_id.")
        return func(*args, **kwargs)
    return wrapper