"""
Base transport class for MCP server
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


class BaseTransport(ABC):
    """
    Base class for MCP transport implementations
    """
    
    def __init__(self, message_handler: Optional[Callable] = None):
        self.message_handler = message_handler
        self.is_running = False
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def set_message_handler(self, handler: Callable) -> None:
        """
        Set message handler for processing incoming messages
        
        Args:
            handler: Function to handle incoming messages
        """
        self.message_handler = handler
        self.logger.debug("Message handler set")
    
    @abstractmethod
    async def start(self) -> None:
        """Start the transport server"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport server"""
        pass
    
    @abstractmethod
    async def send_message(self, message: str, session_id: Optional[str] = None) -> None:
        """
        Send message to client(s)
        
        Args:
            message: Message to send
            session_id: Optional session ID for targeted sending
        """
        pass
    
    async def handle_message(self, message: str, session_id: Optional[str] = None) -> Optional[str]:
        """
        Handle incoming message
        
        Args:
            message: Incoming message
            session_id: Session ID for the message
            
        Returns:
            Response message (if any)
        """
        if self.message_handler:
            try:
                return await self.message_handler(message, session_id)
            except Exception as e:
                self.logger.error(f"Error handling message: {str(e)}")
                return None
        else:
            self.logger.warning("No message handler set")
            return None
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(running={self.is_running})"