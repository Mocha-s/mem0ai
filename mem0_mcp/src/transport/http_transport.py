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
from ..utils.errors import TransportError, ProtocolError, ValidationError, ErrorHandler
from ..utils.logger import get_logger
from ..utils.metrics import get_metrics_collector, initialize_metrics, performance_monitor
from ..utils.cancellation import get_cancellation_manager, cancellable_operation
from ..identity import IdentityManager, Identity
from .monitoring import MCPMonitoringMiddleware, MonitoringEndpoints

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
        
        # Initialize metrics collection
        self.metrics_collector = get_metrics_collector()
        if not hasattr(self.metrics_collector, '_running') or not self.metrics_collector._running:
            initialize_metrics()
        
        # Initialize cancellation manager
        self.cancellation_manager = get_cancellation_manager()
        
        # Setup monitoring middleware and endpoints
        self.monitoring_endpoints = MonitoringEndpoints(self.metrics_collector)
        
        self._setup_routes()
        self._setup_middleware()
        self._setup_monitoring()
        
        logger.info(f"HTTP transport initialized on {config.host}:{config.port} with monitoring and cancellation support")
    
    def _setup_middleware(self) -> None:
        """Setup FastAPI middleware"""
        # Add monitoring middleware first (to capture all requests)
        self.app.add_middleware(
            MCPMonitoringMiddleware,
            metrics_collector=self.metrics_collector
        )
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify allowed origins
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )
    
    def _setup_monitoring(self) -> None:
        """Setup monitoring endpoints"""
        # Add monitoring endpoints to the app
        self.monitoring_endpoints.setup_routes(self.app)
        
        # Add cancellation endpoints
        self._setup_cancellation_endpoints()
    
    def _setup_cancellation_endpoints(self) -> None:
        """Setup cancellation-related endpoints"""
        
        @self.app.post("/cancel/{request_id}")
        async def cancel_request(request_id: str):
            """Cancel a specific request"""
            success = self.cancellation_manager.cancel_request(
                request_id, 
                "User requested cancellation via API"
            )
            
            return {
                "success": success,
                "request_id": request_id,
                "message": "Request cancelled" if success else "Request not found"
            }
        
        @self.app.get("/cancellation/stats")
        async def get_cancellation_stats():
            """Get cancellation manager statistics"""
            return self.cancellation_manager.get_stats()
        
        @self.app.get("/cancellation/tokens")
        async def list_active_tokens():
            """List active cancellation tokens"""
            return {
                "active_tokens": [
                    {
                        "request_id": token.request_id,
                        "created_at": token.created_at.isoformat(),
                        "timeout": token.timeout,
                        "is_cancelled": token.is_cancelled(),
                        "is_expired": token.is_expired()
                    }
                    for token in self.cancellation_manager.active_tokens.values()
                ]
            }
    
    def _setup_routes(self) -> None:
        """Setup HTTP routes"""
        
        @self.app.get("/health")
        @performance_monitor("health_check")
        async def health_check():
            """Health check endpoint with performance monitoring"""
            system_metrics = self.metrics_collector.get_system_metrics()
            performance_stats = self.metrics_collector.get_performance_report()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "sessions": len(self.sessions),
                "config": {
                    "mem0_url": self.config.mem0_base_url,
                    "api_version": self.config.mem0_api_version
                },
                "metrics": {
                    "system": system_metrics,
                    "requests_total": performance_stats.get("system", {}).get("requests", {}).get("total", 0),
                    "active_requests": performance_stats.get("system", {}).get("requests", {}).get("active", 0)
                }
            }
        
        # Simplified context-aware endpoints without client_name
        @self.app.post("/mcp/user/{user_id}")
        async def handle_mcp_with_user_id(request: Request, user_id: str):
            """Handle MCP messages with explicit user_id in path"""
            return await self._handle_mcp_with_identity(request, user_id=user_id)
        
        @self.app.post("/mcp/agent/{agent_id}")
        async def handle_mcp_with_agent_id(request: Request, agent_id: str):
            """Handle MCP messages with explicit agent_id in path"""
            return await self._handle_mcp_with_identity(request, agent_id=agent_id)
        
        @self.app.post("/mcp/run/{run_id}")
        async def handle_mcp_with_run_id(request: Request, run_id: str):
            """Handle MCP messages with explicit run_id in path"""
            return await self._handle_mcp_with_identity(request, run_id=run_id)
        
        @self.app.post("/mcp/{identity_value}")
        async def handle_mcp_with_identity_default(request: Request, identity_value: str):
            """Handle MCP messages with default identity (treated as user_id)"""
            return await self._handle_mcp_with_identity(request, user_id=identity_value)
        
        @self.app.post("/mcp")
        async def handle_mcp_standard(request: Request):
            """Handle MCP messages via standard /mcp endpoint"""
            return await self._handle_mcp_standard(request)
        
        @self.app.get("/mcp") 
        async def handle_mcp_get(request: Request):
            """Handle MCP GET requests for SSE streaming (per MCP spec)"""
            # Check if client accepts SSE
            accept_header = request.headers.get("accept", "")
            if "text/event-stream" in accept_header:
                return await self._handle_sse_stream(request)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
        
        @self.app.post("/message")
        async def handle_message_legacy(request: Request):
            """Handle MCP messages via HTTP POST (legacy endpoint)"""
            return await self._handle_mcp_standard(request)
    
    @performance_monitor("sse_stream")
    async def _handle_sse_stream(self, request: Request) -> EventSourceResponse:
        """Handle SSE stream for MCP communications"""
        try:
            # Get session ID from headers
            session_id = request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID", str(uuid.uuid4()))
            protocol_version = request.headers.get("MCP-Protocol-Version", "2025-03-26")
            
            logger.debug(f"Starting SSE stream for session {session_id}, protocol {protocol_version}")
            
            # Check for resumable stream (Last-Event-ID header)
            last_event_id = request.headers.get("Last-Event-ID")
            if last_event_id:
                logger.debug(f"Resuming SSE stream from event ID: {last_event_id}")
            
            # Create or get session
            if session_id not in self.sessions:
                session = HTTPSession(session_id)
                self.sessions[session_id] = session
                logger.debug(f"Created new SSE session: {session_id}")
            else:
                session = self.sessions[session_id]
                logger.debug(f"Resuming existing SSE session: {session_id}")
            
            async def stream_generator():
                """Generator for SSE events"""
                event_counter = 0
                
                try:
                    while session.connected:
                        try:
                            # Wait for message with timeout
                            message = await asyncio.wait_for(
                                session.message_queue.get(), 
                                timeout=30.0  # 30 second keepalive
                            )
                            
                            # Send SSE event with ID for resumability
                            event_counter += 1
                            event_id = f"{session_id}:{event_counter}"
                            
                            yield {
                                "id": event_id,
                                "event": "message", 
                                "data": message
                            }
                            
                        except asyncio.TimeoutError:
                            # Send keepalive ping
                            yield {
                                "event": "ping",
                                "data": "keepalive"
                            }
                            
                        except Exception as e:
                            logger.error(f"Error in SSE stream generator: {str(e)}")
                            yield {
                                "event": "error",
                                "data": f"Stream error: {str(e)}"
                            }
                            break
                            
                except Exception as e:
                    logger.error(f"SSE stream generator failed: {str(e)}")
                    yield {
                        "event": "error", 
                        "data": f"Stream failed: {str(e)}"
                    }
                finally:
                    # Clean up session on disconnect
                    session.disconnect()
                    logger.debug(f"SSE stream ended for session {session_id}")
            
            # Return SSE response
            return EventSourceResponse(
                stream_generator(),
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Last-Event-ID"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create SSE stream: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to create SSE stream: {str(e)}"
            )
    
    @performance_monitor("mcp_with_identity")
    async def _handle_mcp_with_identity(self, request: Request, 
                                      user_id: str = None, agent_id: str = None, run_id: str = None):
        # Generate request ID for cancellation tracking
        request_id = f"mcp_identity_{uuid.uuid4()}"
        
        # Create cancellable operation context
        async with cancellable_operation(
            request_id=request_id,
            timeout=self.config.request_timeout if hasattr(self.config, 'request_timeout') else 300,
            cancellation_manager=self.cancellation_manager
        ) as token:
            try:
                # Check cancellation before proceeding
                token.check_cancelled()
                
                # Check for legacy client_name in URL path for backward compatibility
                path_parts = request.url.path.split('/')
                if len(path_parts) > 3 and path_parts[1] != 'mcp':
                    # Legacy format detected, log warning
                    logger.warning(f"Legacy URL format detected: {request.url.path}")

                # Create identity object from path parameters
                identity = Identity(
                    user_id=user_id,
                    agent_id=agent_id,
                    run_id=run_id
                )

                # Set identity context
                tokens = IdentityManager.set_identity(identity)

                # Get session ID from headers or create new one
                session_id = request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID", str(uuid.uuid4()))
                
                # Create simplified session_id for tracking
                full_session_id = f"{session_id}:{identity.get_primary_id()}"
                
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
                    # Return enhanced JSON-RPC parse error
                    logger.error(f"Parse error in MCP request: {str(e)}")
                    parse_error = ProtocolError(
                        f"Parse error: {str(e)}",
                        code=-32700,
                        data={"raw_content": str(await request.body())[:100]},
                        user_message="请求格式错误，请检查JSON格式是否正确"
                    )
                    return JSONResponse(
                        content=ErrorHandler.format_error_for_client(parse_error, None, self.config.debug),
                        status_code=400
                    )
                
                logger.debug(f"Received MCP message for {identity.get_primary_id()}: {message[:100]}...")
                
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
                    
            except Exception as e:
                logger.error(f"Error handling MCP request with identity: {str(e)}", exc_info=True)
                # Return enhanced JSON-RPC internal error
                internal_error = TransportError(
                    f"Internal server error: {str(e)}",
                    data={"request_path": str(request.url.path)},
                    transport_type="HTTP",
                    user_message="服务器内部错误，请稍后重试"
                )
                return JSONResponse(
                    content=ErrorHandler.format_error_for_client(internal_error, None, self.config.debug),
                    status_code=500
                )
            finally:
                # Always clear identity context
                if 'tokens' in locals():
                    IdentityManager.clear_identity(tokens)
    
    @performance_monitor("mcp_standard")
    async def _handle_mcp_standard(self, request: Request):
        """Handle standard MCP requests - supports both 2025-06-18 and 2025-03-26 versions"""
        try:
            # Check MCP protocol version header (required per MCP 2025-06-18, optional for 2025-03-26)
            protocol_version = request.headers.get("MCP-Protocol-Version")

            # For backwards compatibility, assume 2025-03-26 if no header is present
            if not protocol_version:
                protocol_version = "2025-03-26"
                logger.debug("No MCP-Protocol-Version header found, assuming 2025-03-26 for backwards compatibility")
            else:
                logger.debug(f"Client protocol version: {protocol_version}")

                # Validate protocol version
                from ..config.constants import SUPPORTED_MCP_VERSIONS
                if protocol_version not in SUPPORTED_MCP_VERSIONS:
                    logger.warning(f"Unsupported protocol version: {protocol_version}")
                    return JSONResponse(
                        content={
                            "error": "Unsupported MCP protocol version",
                            "supported_versions": SUPPORTED_MCP_VERSIONS,
                            "received_version": protocol_version
                        },
                        status_code=400
                    )
            
            # Get session ID from standard MCP header or fallback to X-Session-ID
            session_id = request.headers.get("Mcp-Session-Id") or request.headers.get("X-Session-ID", str(uuid.uuid4()))
            
            # Get message content with error handling
            content_type = request.headers.get("content-type", "")
            message = None
            
            try:
                if "application/json" in content_type:
                    data = await request.json()
                    # Support for JSON-RPC batching (MCP 2025-03-26 feature)
                    if isinstance(data, list):
                        # Handle batch request
                        logger.debug(f"Received JSON-RPC batch with {len(data)} messages")
                        message = json.dumps(data)
                    elif isinstance(data, dict):
                        message = json.dumps(data)
                    else:
                        message = str(data)
                else:
                    message = (await request.body()).decode('utf-8')
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # Return enhanced JSON-RPC parse error
                logger.error(f"Parse error in standard MCP request: {str(e)}")
                parse_error = ProtocolError(
                    f"Parse error: {str(e)}",
                    code=-32700,
                    data={"session_id": session_id, "protocol_version": protocol_version},
                    user_message="请求格式错误，请检查JSON格式是否正确"
                )
                return JSONResponse(
                    content=ErrorHandler.format_error_for_client(parse_error, None, self.config.debug)
                )

            logger.debug(f"Received MCP message from session {session_id}: {message[:100]}...")

            # Create session if it doesn't exist
            if session_id not in self.sessions:
                self.sessions[session_id] = HTTPSession(session_id)

            # Store protocol version in session for consistency
            self.sessions[session_id].protocol_version = protocol_version

            # Handle message using base class method (supports both single and batch)
            response = await self.handle_message(message, session_id)
            
            if response:
                # Parse response to determine if it's JSON
                try:
                    response_data = json.loads(response)
                    # Check if this is a batch response or single response
                    if isinstance(response_data, list):
                        # Batch response
                        logger.debug(f"Returning batch response with {len(response_data)} items")
                        return JSONResponse(content=response_data)
                    else:
                        # Single response
                        return JSONResponse(content=response_data)
                except json.JSONDecodeError:
                    return JSONResponse(content={"response": response})
            else:
                # No response means all were notifications - return 202 Accepted per MCP 2025-03-26
                return JSONResponse(content=None, status_code=202)
                
        except Exception as e:
            logger.error(f"Error handling standard MCP request: {str(e)}", exc_info=True)
            # Return enhanced JSON-RPC internal error
            internal_error = TransportError(
                f"Internal server error: {str(e)}",
                data={"session_id": session_id, "protocol_version": protocol_version},
                transport_type="HTTP",
                user_message="服务器内部错误，请稍后重试"
            )
            return JSONResponse(
                content=ErrorHandler.format_error_for_client(internal_error, None, self.config.debug),
                status_code=500
            )
        
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
        """Stop HTTP server and cleanup metrics"""
        if not self.is_running:
            logger.warning("HTTP transport not running")
            return
        
        logger.info("Stopping HTTP server...")
        
        # Disconnect all sessions
        for session in self.sessions.values():
            session.disconnect()
        self.sessions.clear()
        
        # Stop metrics collection
        try:
            await self.metrics_collector.stop()
            logger.info("Metrics collection stopped")
        except Exception as e:
            logger.error(f"Error stopping metrics collection: {e}")
        
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
        
    def _should_use_sse(self, request_data: Dict[str, Any]) -> bool:
        """Determine if SSE should be used based on request type"""
        if not isinstance(request_data, dict):
            return False
            
        method = request_data.get("method")
        
        # Use SSE for long-running operations
        sse_methods = {
            "tools/call",  # Tool calls might need streaming responses
            "sampling/createMessage",  # LLM sampling requests
            "roots/list",  # File system operations
            "notifications/progress"  # Progress notifications
        }
        
        return method in sse_methods
    
    async def _send_sse_response(self, request: Request, response: str, session_id: str) -> EventSourceResponse:
        """Send response via SSE stream"""
        try:
            async def response_generator():
                """Generate SSE response"""
                try:
                    # Send the response as SSE event
                    yield {
                        "id": f"{session_id}:{uuid.uuid4()}",
                        "event": "response",
                        "data": response
                    }
                    
                    # Send completion event
                    yield {
                        "id": f"{session_id}:{uuid.uuid4()}",
                        "event": "complete",
                        "data": json.dumps({"status": "completed"})
                    }
                    
                except Exception as e:
                    logger.error(f"Error in SSE response generator: {str(e)}")
                    yield {
                        "event": "error",
                        "data": json.dumps({"error": str(e)})
                    }
            
            return EventSourceResponse(
                response_generator(),
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Mcp-Session-Id": session_id
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create SSE response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create SSE response: {str(e)}"
            )