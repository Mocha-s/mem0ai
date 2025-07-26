"""
Streamable HTTP transport implementation for MCP server
"""

import asyncio
import json
import uuid
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sse_starlette.sse import EventSourceResponse

from .base_transport import BaseTransport
from ..config.settings import MCPConfig
from ..utils.errors import TransportError
from ..utils.logger import get_logger
from ..identity import IdentityManager, Identity

logger = get_logger(__name__)


class HTTPSession:
    """HTTP session for MCP client"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.initialized = False
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.connected = True
    
    async def send_message(self, message: str) -> None:
        """Send message to client via SSE"""
        if self.connected:
            await self.message_queue.put(message)
            self.last_activity = datetime.now()
    
    def disconnect(self) -> None:
        """Mark session as disconnected"""
        self.connected = False


class HTTPTransport(BaseTransport):
    """
    Streamable HTTP transport for MCP protocol
    
    Supports both regular HTTP requests and Server-Sent Events for streaming
    """
    
    def __init__(self, config: MCPConfig, message_handler: Optional[Any] = None):
        super().__init__(message_handler)
        self.config = config
        self.app = FastAPI(
            title="Mem0 MCP Server",
            description="Model Context Protocol server for Mem0",
            version="1.0.0",
            docs_url="/docs" if config.debug else None,
            redoc_url="/redoc" if config.debug else None
        )
        self.sessions: Dict[str, HTTPSession] = {}
        self.server: Optional[uvicorn.Server] = None
        
        self._setup_routes()
        self._setup_middleware()
        
        logger.info(f"HTTP transport initialized on {config.host}:{config.port}")
    
    def _setup_middleware(self) -> None:
        """Setup FastAPI middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify allowed origins
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self) -> None:
        """Setup HTTP routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "sessions": len(self.sessions),
                "config": {
                    "mem0_url": self.config.mem0_base_url,
                    "api_version": self.config.mem0_api_version
                }
            }
        
        # OpenMemory-style endpoint with user identity in URL path
        @self.app.post("/{client_name}/mcp/{user_id}")
        async def handle_mcp_with_identity(request: Request, client_name: str, user_id: str):
            """Handle MCP messages with identity in URL path (OpenMemory style)"""
            return await self._handle_mcp_with_identity(request, client_name, user_id)
        
        # Alternative endpoint format for different identity types
        @self.app.post("/{client_name}/mcp/user/{user_id}")
        async def handle_mcp_with_user_id(request: Request, client_name: str, user_id: str):
            """Handle MCP messages with explicit user_id in path"""
            return await self._handle_mcp_with_identity(request, client_name, user_id=user_id)
        
        @self.app.post("/{client_name}/mcp/agent/{agent_id}")
        async def handle_mcp_with_agent_id(request: Request, client_name: str, agent_id: str):
            """Handle MCP messages with explicit agent_id in path"""
            return await self._handle_mcp_with_identity(request, client_name, agent_id=agent_id)
        
        @self.app.post("/{client_name}/mcp/run/{run_id}")
        async def handle_mcp_with_run_id(request: Request, client_name: str, run_id: str):
            """Handle MCP messages with explicit run_id in path"""
            return await self._handle_mcp_with_identity(request, client_name, run_id=run_id)
        
        @self.app.post("/mcp")
        async def handle_mcp_standard(request: Request):
            """Handle MCP messages via standard /mcp endpoint"""
            return await self._handle_mcp_standard(request)
        
        @self.app.get("/mcp") 
        async def handle_mcp_get(request: Request):
            """Handle MCP GET requests (per MCP spec)"""
            # Check if client accepts SSE
            accept_header = request.headers.get("accept", "")
            if "text/event-stream" in accept_header:
                # For now, return 405 Method Not Allowed (streaming not fully implemented)
                raise HTTPException(status_code=405, detail="GET method for streaming not yet implemented")
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
        
        @self.app.post("/message")
        async def handle_message_legacy(request: Request):
            """Handle MCP messages via HTTP POST (legacy endpoint)"""
            return await self._handle_mcp_standard(request)
    
    async def _handle_mcp_with_identity(self, request: Request, client_name: str, 
                                      user_id: str = None, agent_id: str = None, run_id: str = None):
        """Handle MCP messages with identity from URL path"""
        try:
            # Create identity object from path parameters
            identity = Identity(
                user_id=user_id,
                agent_id=agent_id, 
                run_id=run_id
            )
            
            # Set identity context
            tokens = IdentityManager.set_identity(identity)
            
            try:
                # Get session ID from headers or create new one
                session_id = request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID", str(uuid.uuid4()))
                
                # Add client_name to session_id for tracking
                full_session_id = f"{client_name}:{session_id}:{identity.get_primary_id()}"
                
                # Get message content with error handling
                content_type = request.headers.get("content-type", "")
                message = None
                
                try:
                    if "application/json" in content_type:
                        data = await request.json()
                        message = json.dumps(data) if isinstance(data, dict) else str(data)
                    else:
                        message = (await request.body()).decode('utf-8')
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    # Return JSON-RPC parse error
                    from ..protocol.jsonrpc import JSONRPCHandler
                    error_response = JSONRPCHandler.create_error_response(
                        -32700,  # Parse error
                        "Parse error: Invalid JSON",
                        id=None
                    )
                    return JSONResponse(content=error_response.to_dict())
                
                logger.debug(f"Received MCP message for {client_name}:{identity.get_primary_id()}: {message[:100]}...")
                
                # Create session if it doesn't exist
                if full_session_id not in self.sessions:
                    self.sessions[full_session_id] = HTTPSession(full_session_id)
                
                # Handle message using base class method
                response = await self.handle_message(message, full_session_id)
                
                if response:
                    # Parse response to determine if it's JSON
                    try:
                        response_data = json.loads(response)
                        return JSONResponse(content=response_data)
                    except json.JSONDecodeError:
                        return JSONResponse(content={"response": response})
                else:
                    return JSONResponse(content={"status": "processed"})
                    
            finally:
                # Always clear identity context
                IdentityManager.clear_identity(tokens)
                
        except Exception as e:
            logger.error(f"Error handling MCP request with identity: {str(e)}")
            # Return JSON-RPC internal error
            from ..protocol.jsonrpc import JSONRPCHandler
            error_response = JSONRPCHandler.create_error_response(
                -32603,  # Internal error
                f"Internal server error: {str(e)}",
                id=None
            )
            return JSONResponse(content=error_response.to_dict(), status_code=500)
    
    async def _handle_mcp_standard(self, request: Request):
        """Handle standard MCP requests without URL identity"""
        try:
            # Check MCP protocol version header (optional but recommended)
            protocol_version = request.headers.get("MCP-Protocol-Version")
            if protocol_version:
                logger.debug(f"Client protocol version: {protocol_version}")
            
            # Get session ID from standard MCP header or fallback to X-Session-ID
            session_id = request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID", str(uuid.uuid4()))
            
            # Get message content with error handling
            content_type = request.headers.get("content-type", "")
            message = None
            
            try:
                if "application/json" in content_type:
                    data = await request.json()
                    message = json.dumps(data) if isinstance(data, dict) else str(data)
                else:
                    message = (await request.body()).decode('utf-8')
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # Return JSON-RPC parse error instead of HTTP 500
                from ..protocol.jsonrpc import JSONRPCHandler
                error_response = JSONRPCHandler.create_error_response(
                    -32700,  # Parse error
                    "Parse error: Invalid JSON",
                    id=None
                )
                return JSONResponse(content=error_response.to_dict())
            
            logger.debug(f"Received MCP message from session {session_id}: {message[:100]}...")
            
            # Create session if it doesn't exist
            if session_id not in self.sessions:
                self.sessions[session_id] = HTTPSession(session_id)
            
            # Handle message using base class method
            response = await self.handle_message(message, session_id)
            
            if response:
                # Parse response to determine if it's JSON
                try:
                    response_data = json.loads(response)
                    return JSONResponse(content=response_data)
                except json.JSONDecodeError:
                    return JSONResponse(content={"response": response})
            else:
                return JSONResponse(content={"status": "processed"})
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {str(e)}")
            # Return JSON-RPC internal error instead of HTTP 500
            from ..protocol.jsonrpc import JSONRPCHandler
            error_response = JSONRPCHandler.create_error_response(
                -32603,  # Internal error
                f"Internal server error: {str(e)}",
                id=None
            )
            return JSONResponse(content=error_response.to_dict(), status_code=500)
        
        @self.app.get("/stream/{session_id}")
        async def stream_messages(session_id: str):
            """Stream messages to client via Server-Sent Events"""
            
            # Create session if it doesn't exist
            if session_id not in self.sessions:
                self.sessions[session_id] = HTTPSession(session_id)
            
            session = self.sessions[session_id]
            
            async def event_generator():
                """Generate SSE events"""
                try:
                    while session.connected:
                        try:
                            # Wait for message with timeout
                            message = await asyncio.wait_for(
                                session.message_queue.get(),
                                timeout=30.0  # 30 second timeout for keep-alive
                            )
                            
                            # Yield message as SSE event
                            yield {
                                "event": "message",
                                "data": message,
                                "id": str(uuid.uuid4())
                            }
                            
                        except asyncio.TimeoutError:
                            # Send keep-alive ping
                            yield {
                                "event": "ping",
                                "data": json.dumps({"timestamp": datetime.now().isoformat()}),
                                "id": str(uuid.uuid4())
                            }
                            
                except asyncio.CancelledError:
                    logger.info(f"Stream cancelled for session {session_id}")
                finally:
                    # Clean up session
                    session.disconnect()
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                    logger.info(f"Session {session_id} disconnected")
            
            return EventSourceResponse(
                event_generator(),
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        @self.app.get("/sessions")
        async def list_sessions():
            """List active sessions (debug endpoint)"""
            if not self.config.debug:
                raise HTTPException(status_code=404, detail="Not found")
            
            session_info = []
            for session_id, session in self.sessions.items():
                session_info.append({
                    "session_id": session_id,
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "initialized": session.initialized,
                    "connected": session.connected,
                    "queue_size": session.message_queue.qsize()
                })
            
            return {
                "total_sessions": len(self.sessions),
                "sessions": session_info
            }
        
        @self.app.delete("/sessions/{session_id}")
        async def disconnect_session(session_id: str):
            """Disconnect a specific session"""
            if session_id in self.sessions:
                self.sessions[session_id].disconnect()
                del self.sessions[session_id]
                return {"status": "disconnected", "session_id": session_id}
            else:
                raise HTTPException(status_code=404, detail="Session not found")
    
    async def start(self) -> None:
        """Start HTTP server"""
        if self.is_running:
            logger.warning("HTTP transport already running")
            return
        
        config = uvicorn.Config(
            app=self.app,
            host=self.config.host,
            port=self.config.port,
            log_level="debug" if self.config.debug else "info",
            access_log=self.config.debug
        )
        
        self.server = uvicorn.Server(config)
        
        logger.info(f"Starting HTTP server on {self.config.host}:{self.config.port}")
        
        try:
            self.is_running = True
            await self.server.serve()
        except Exception as e:
            logger.error(f"Error starting HTTP server: {str(e)}")
            self.is_running = False
            raise TransportError(f"Failed to start HTTP server: {str(e)}")
    
    async def stop(self) -> None:
        """Stop HTTP server"""
        if not self.is_running:
            logger.warning("HTTP transport not running")
            return
        
        logger.info("Stopping HTTP server...")
        
        # Disconnect all sessions
        for session in self.sessions.values():
            session.disconnect()
        self.sessions.clear()
        
        # Stop server
        if self.server:
            self.server.should_exit = True
            # Wait a bit for graceful shutdown
            await asyncio.sleep(1)
        
        self.is_running = False
        logger.info("HTTP server stopped")
    
    async def send_message(self, message: str, session_id: Optional[str] = None) -> None:
        """
        Send message to client(s) via SSE
        
        Args:
            message: Message to send
            session_id: Optional session ID for targeted sending
        """
        if session_id:
            # Send to specific session
            if session_id in self.sessions:
                await self.sessions[session_id].send_message(message)
                logger.debug(f"Message sent to session {session_id}")
            else:
                logger.warning(f"Session {session_id} not found")
        else:
            # Broadcast to all sessions
            for session in self.sessions.values():
                if session.connected:
                    await session.send_message(message)
            logger.debug(f"Message broadcast to {len(self.sessions)} sessions")
    
    async def cleanup_sessions(self) -> None:
        """Clean up inactive sessions"""
        current_time = datetime.now()
        inactive_sessions = []
        
        for session_id, session in self.sessions.items():
            # Remove sessions inactive for more than 1 hour
            if (current_time - session.last_activity).seconds > 3600:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            logger.info(f"Cleaning up inactive session: {session_id}")
            self.sessions[session_id].disconnect()
            del self.sessions[session_id]
        
        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)
        
    def get_connected_sessions(self) -> List[str]:
        """Get list of connected session IDs"""
        return [
            session_id for session_id, session in self.sessions.items()
            if session.connected
        ]