"""
Streamable HTTP Transport Implementation

Implements MCP 2025-06-18 Streamable HTTP transport specification.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, AsyncIterator, Callable
from dataclasses import dataclass, field
from aiohttp import web, ClientSession, ClientError
from aiohttp_sse import sse_response
import weakref
import time

logger = logging.getLogger(__name__)

@dataclass
class MCPSession:
    """MCP session state management"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    client_info: Optional[Dict[str, Any]] = None
    initialized: bool = False
    event_counter: int = 0
    streams: Dict[str, Any] = field(default_factory=dict)

class StreamableHTTPTransport:
    """
    MCP Streamable HTTP Transport implementation
    
    Supports:
    - HTTP POST for client requests
    - HTTP GET for SSE streams
    - Session management with Mcp-Session-Id header
    - Resumable streams with Last-Event-ID
    - Multiple concurrent connections
    """
    
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8080,
        endpoint_path: str = "/mcp",
        session_timeout: int = 3600,  # 1 hour
        allowed_origins: Optional[List[str]] = None
    ):
        self.host = host
        self.port = port
        self.endpoint_path = endpoint_path
        self.session_timeout = session_timeout
        self.allowed_origins = allowed_origins or ["http://localhost", "http://127.0.0.1"]
        
        # State management
        self.sessions: Dict[str, MCPSession] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def register_handler(self, method: str, handler: Callable):
        """Register a handler for specific JSON-RPC methods"""
        self.message_handlers[method] = handler
    
    def _validate_origin(self, request: web.Request) -> bool:
        """Validate Origin header to prevent DNS rebinding attacks"""
        origin = request.headers.get('Origin')
        if not origin:
            return True  # Allow requests without Origin header for local development
        
        # Check for wildcard permission
        if "*" in self.allowed_origins:
            return True
        
        # Check specific origin patterns
        return any(origin.startswith(allowed) for allowed in self.allowed_origins)
    
    def _create_session(self, session_id: Optional[str] = None) -> MCPSession:
        """Create a new MCP session"""
        if not session_id:
            session_id = str(uuid.uuid4())
        session = MCPSession(session_id=session_id)
        self.sessions[session_id] = session
        logger.debug(f"Created session: {session_id}")
        return session
    
    def _get_session(self, session_id: Optional[str]) -> Optional[MCPSession]:
        """Get existing session by ID"""
        if not session_id:
            return None
        
        session = self.sessions.get(session_id)
        if session:
            session.last_activity = time.time()
        
        return session
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if current_time - session.last_activity > self.session_timeout
        ]
        
        for session_id in expired_sessions:
            logger.info(f"Cleaning up expired session: {session_id}")
            del self.sessions[session_id]
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
    
    def _generate_event_id(self, session: MCPSession) -> str:
        """Generate unique event ID for SSE"""
        session.event_counter += 1
        return f"{session.session_id}:{session.event_counter}"
    
    async def _handle_json_rpc_request(
        self,
        message: Dict[str, Any],
        session: MCPSession
    ) -> Dict[str, Any]:
        """Process JSON-RPC request and return response"""
        
        # Validate JSON-RPC 2.0 format according to MCP 2025-06-18
        if message.get('jsonrpc') != '2.0':
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: jsonrpc field must be '2.0'"},
                "id": message.get('id')
            }
        
        method = message.get('method')
        request_id = message.get('id')
        logger.info(f"📨 Processing JSON-RPC request: {method} (id: {request_id}) for session {session.session_id}")
        
        # Enhanced logging for specific clients (only essential info)
        client_info = session.client_info or {}
        if client_info.get('name', '').startswith('Dify'):
            logger.info(f"🎯 DIFY CLIENT: {client_info.get('name')} {client_info.get('version')} - {method}")
        
        if not method:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: method field required"},
                "id": message.get('id')
            }
            if client_info.get('name', '').startswith('Dify'):
                logger.error(f"💥 DIFY ERROR: Missing method field")
            return error_response
        
        handler = self.message_handlers.get(method)
        if not handler:
            logger.error(f"❌ Method not found: {method}. Available handlers: {list(self.message_handlers.keys())}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": message.get('id')
            }
            if client_info.get('name', '').startswith('Dify'):
                logger.error(f"💥 DIFY ERROR: Method not found: {method}")
            return error_response
        
        try:
            logger.debug(f"🎯 Calling handler for method: {method}")
            
            # Dify-specific timeout adjustments
            handler_timeout = 10  # Default timeout
            if client_info.get('name', '').startswith('Dify'):
                # Dify might have stricter timeout expectations
                handler_timeout = 15  # Slightly longer for Dify
                
            if method == "tools/call":
                handler_timeout = 30 if client_info.get('name', '').startswith('Dify') else 120
            elif method in ["initialize", "tools/list", "resources/list", "prompts/list"]:
                handler_timeout = 10 if client_info.get('name', '').startswith('Dify') else 30
            
            result = await asyncio.wait_for(
                handler(message.get('params', {}), session),
                timeout=handler_timeout
            )
            
            logger.debug(f"✅ Handler completed for method: {method}")
            
            # Success logging for specific clients (condensed)
            if client_info.get('name', '').startswith('Dify'):
                logger.debug(f"🎯 DIFY SUCCESS: {method}")
            
            # Handle initialization - mark as initialized immediately for better client compatibility
            if method == "initialize":
                # Store client info and mark as initialized
                session.client_info = message.get('params', {}).get('clientInfo', {})
                session.initialized = True  # Mark as initialized immediately to prevent client disconnection
                logger.info(f"✅ Session {session.session_id} marked as initialized for {session.client_info.get('name', 'unknown')}")
            
            success_response = {
                "jsonrpc": "2.0",
                "result": result,
                "id": message.get('id')
            }
            
            # Enhanced logging for successful responses (condensed for production)
            if client_info.get('name', '').startswith('Dify'):
                logger.debug(f"🎯 DIFY RESPONSE: {method} completed successfully")
                
            return success_response
            
        except asyncio.TimeoutError:
            timeout_msg = f"Handler timeout for {method} after {handler_timeout}s"
            logger.error(timeout_msg)
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": timeout_msg},  # Server error code
                "id": message.get('id')
            }
            if client_info.get('name', '').startswith('Dify'):
                logger.error(f"💥 DIFY TIMEOUT: {timeout_msg}")
            return error_response
        except ValueError as ve:
            # Parameter validation errors - use Invalid params code
            logger.error(f"Parameter validation error for {method}: {ve}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Invalid params: {str(ve)}"},
                "id": message.get('id')
            }
            if client_info.get('name', '').startswith('Dify'):
                logger.error(f"💥 DIFY PARAMS ERROR: {ve}")
            return error_response
        except Exception as e:
            logger.error(f"Handler error for {method}: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},  # Internal error code
                "id": message.get('id')
            }
            if client_info.get('name', '').startswith('Dify'):
                logger.error(f"💥 DIFY HANDLER ERROR: {e}")
                import traceback
                logger.error(f"💥 DIFY STACK TRACE: {traceback.format_exc()}")
            return error_response
    
    async def _handle_post(self, request: web.Request) -> web.Response:
        """Handle HTTP POST requests (client sends message)"""
        
        # Validate origin
        if not self._validate_origin(request):
            raise web.HTTPForbidden(text="Invalid origin")
        
        # Check protocol version - Support multiple versions for client compatibility
        protocol_version = request.headers.get('MCP-Protocol-Version', '2025-06-18')
        supported_versions = ["2025-06-18", "2025-03-26", "2024-11-05", "2024-10-07"]
        
        if protocol_version not in supported_versions:
            raise web.HTTPBadRequest(
                text=f"Unsupported protocol version: {protocol_version}. Supported: {', '.join(supported_versions)}"
            )
        
        # Get or create session
        session_id = request.headers.get('Mcp-Session-Id')
        session = self._get_session(session_id)
        
        # Extract user_id from multiple sources (priority: path > query > header)
        user_id = (request.get('extracted_user_id') or 
                  request.query.get('user_id') or 
                  request.headers.get('X-User-Id'))
        
        try:
            # Parse JSON-RPC message first to check if it's initialize
            body = await request.json()
            
            # Check session requirements after parsing the message
            if not session:
                # For initialize method, always create a new session
                if body.get('method') == 'initialize':
                    session = self._create_session()
                    if user_id:
                        session.client_info = session.client_info or {}
                        session.client_info['user_id'] = user_id
                else:
                    # For other methods, try to find existing session or create one if needed
                    if session_id:
                        # Client provided session_id but session not found
                        # This is normal after server restarts or session timeouts
                        logger.debug(f"Session {session_id} not found, creating new one (likely server restart or timeout)")
                        session = self._create_session(session_id)
                    else:
                        # No session_id provided - create new session for backward compatibility
                        logger.debug(f"Creating new session for method: {body.get('method')} (no session_id provided)")
                        session = self._create_session()
                    
                    if user_id:
                        session.client_info = session.client_info or {}
                        session.client_info['user_id'] = user_id
            
            # Check if client supports SSE
            accept_header = request.headers.get('Accept', '')
            supports_sse = 'text/event-stream' in accept_header
            supports_json = 'application/json' in accept_header
            
            message_type = None
            if 'method' in body:
                if 'id' in body:
                    message_type = 'request'
                else:
                    message_type = 'notification'
            elif 'result' in body or 'error' in body:
                message_type = 'response'
            else:
                raise web.HTTPBadRequest(text="Invalid JSON-RPC message")
            
            # Handle different message types
            if message_type in ['response', 'notification']:
                # Process notifications properly - especially 'initialized'
                method = body.get('method')
                
                # Handle critical 'initialized' notification per MCP 2025-06-18 spec
                if method == 'notifications/initialized' or method == 'initialized':
                    logger.info(f"🎯 Processing MCP initialized notification for session {session.session_id}")
                    
                    # Call the initialized handler to complete the handshake
                    # Try both possible handler names
                    handler = self.message_handlers.get('notifications/initialized') or self.message_handlers.get('initialized')
                    if handler and session:
                        try:
                            await handler(body.get('params', {}), session)
                            logger.info(f"✅ MCP handshake completed for session {session.session_id}")
                        except Exception as e:
                            logger.error(f"❌ Failed to process initialized notification: {e}")
                    else:
                        logger.warning(f"⚠️ No initialized handler found (checked: notifications/initialized, initialized)")
                        # Log available handlers for debugging
                        available_handlers = list(self.message_handlers.keys())
                        logger.debug(f"🔍 Available handlers: {available_handlers}")
                
                
                # Log other notifications for debugging
                elif method:
                    logger.info(f"📨 Received notification: {method}")
                
                # Return 202 Accepted for all notifications (as per JSON-RPC spec)
                return web.Response(status=202)
            
            elif message_type == 'request':
                # Session should already be created for initialize method in earlier logic
                if not session:
                    raise web.HTTPBadRequest(text="Session required")
                
                # Inject user_id into tool calls if provided
                if user_id and body.get('method') == 'tools/call':
                    params = body.get('params', {})
                    arguments = params.get('arguments', {})
                    if 'user_id' not in arguments:
                        arguments['user_id'] = user_id
                        params['arguments'] = arguments
                        body['params'] = params
                
                # Process the request
                response = await self._handle_json_rpc_request(body, session)
                
                # Decide response format based on client preferences and request type
                # For simple requests (initialize, tools/list), prefer JSON unless client only accepts SSE
                # For complex requests that might stream, prefer SSE if client supports both
                prefer_json_for_simple_requests = body.get('method') in ['initialize', 'tools/list', 'resources/list', 'prompts/list', 'tools/call']
                
                if supports_json and (not supports_sse or prefer_json_for_simple_requests):
                    # Return JSON response with connection persistence headers
                    headers = {
                        'Connection': 'keep-alive',  # Encourage connection reuse
                        'Keep-Alive': 'timeout=300, max=100'  # 5 minute timeout, 100 requests max
                    }
                    if body.get('method') == 'initialize':
                        headers['Mcp-Session-Id'] = session.session_id
                        # Add session validation info for client confidence
                        headers['Mcp-Session-Status'] = 'active'
                        headers['Mcp-Session-Capabilities'] = 'tools,resources,prompts,logging'
                    
                    return web.json_response(response, headers=headers)
                elif supports_sse and 'error' not in response:
                    # Start SSE stream for streaming responses
                    return await self._start_sse_stream(request, session, response)
                else:
                    # Fallback to JSON if no suitable format with persistence headers
                    headers = {
                        'Connection': 'keep-alive',
                        'Keep-Alive': 'timeout=300, max=100'
                    }
                    if body.get('method') == 'initialize':
                        headers['Mcp-Session-Id'] = session.session_id
                        headers['Mcp-Session-Status'] = 'active'
                        headers['Mcp-Session-Capabilities'] = 'tools,resources,prompts,logging'
                    
                    return web.json_response(response, headers=headers)
            
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(text="Invalid JSON")
        except Exception as e:
            logger.error(f"POST handler error: {e}")
            raise web.HTTPInternalServerError(text=str(e))
    
    async def _start_sse_stream(
        self,
        request: web.Request,
        session: MCPSession,
        initial_response: Dict[str, Any]
    ) -> web.StreamResponse:
        """Start Server-Sent Events stream"""
        
        async def event_generator():
            # Send initial response
            event_id = self._generate_event_id(session)
            yield {
                'id': event_id,
                'data': json.dumps(initial_response)
            }
            
            # For simple requests, close the stream immediately after sending the response
            # Only keep streams alive for requests that might need server-initiated messages
            request_method = getattr(session, '_current_method', None)
            should_keep_alive = request_method in ['tools/call'] and 'streaming' in initial_response.get('capabilities', {})
            
            if should_keep_alive:
                # Keep connection alive and send any additional messages
                # This is where server-initiated messages would be sent
                try:
                    while True:
                        await asyncio.sleep(1)
                        # Check if session is still valid
                        if session.session_id not in self.sessions:
                            break
                except asyncio.CancelledError:
                    pass
            # For other requests, the stream will close naturally after sending the initial response
        
        headers = {}
        if request.headers.get('Accept') == 'text/event-stream':
            headers['Mcp-Session-Id'] = session.session_id
        
        response = await sse_response(request, headers=headers)
        
        try:
            async for event in event_generator():
                await response.send(json.dumps(event['data']), id=event['id'])
        except ConnectionResetError:
            logger.info("SSE connection closed by client")
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            await response.wait()
        
        return response
    
    async def _handle_get(self, request: web.Request) -> web.Response:
        """Handle HTTP GET requests - SSE stream for server messages"""
        
        # Validate origin
        if not self._validate_origin(request):
            raise web.HTTPForbidden(text="Invalid origin")
        
        # Check if client accepts SSE
        accept_header = request.headers.get('Accept', '')
        if 'text/event-stream' not in accept_header:
            raise web.HTTPMethodNotAllowed(method='GET', allowed_methods=['POST'])
        
        # Get session if provided
        session_id = request.headers.get('Mcp-Session-Id')
        session = self._get_session(session_id)
        
        # Session is optional for GET - some clients may open SSE before initialization
        
        # Handle resumable streams
        last_event_id = request.headers.get('Last-Event-ID')
        
        async def event_generator():
            # If resuming, replay missed messages (simplified implementation)
            if last_event_id:
                # TODO: Implement message replay based on last_event_id
                pass
            
            # Send server-initiated messages
            try:
                while True:
                    await asyncio.sleep(30)  # Heartbeat every 30 seconds
                    
                    # Check if session is still valid (if session exists)
                    if session and session.session_id not in self.sessions:
                        break
                    
                    # Send heartbeat
                    if session:
                        event_id = self._generate_event_id(session)
                        yield {
                            'id': event_id,
                            'data': json.dumps({"type": "heartbeat", "timestamp": time.time()})
                        }
                    else:
                        # No session, just send basic heartbeat
                        yield {
                            'data': json.dumps({"type": "heartbeat", "timestamp": time.time()})
                        }
                    
            except asyncio.CancelledError:
                pass
        
        response = await sse_response(request)
        
        try:
            async for event in event_generator():
                if 'id' in event:
                    await response.send(event['data'], id=event['id'])
                else:
                    await response.send(event['data'])
        except ConnectionResetError:
            logger.info("SSE connection closed by client")
        except Exception as e:
            logger.error(f"GET SSE stream error: {e}")
        finally:
            await response.wait()
        
        return response
    
    async def _handle_delete(self, request: web.Request) -> web.Response:
        """Handle HTTP DELETE requests (terminate session)"""
        
        session_id = request.headers.get('Mcp-Session-Id')
        if not session_id:
            raise web.HTTPBadRequest(text="Session ID required")
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session terminated: {session_id}")
            return web.Response(status=200, text="Session terminated")
        else:
            raise web.HTTPNotFound(text="Session not found")
    
    async def _handle_health_check(self, request: web.Request) -> web.Response:
        """Handle health check requests"""
        health_data = {
            "status": "healthy",
            "service": "mem0-mcp-server", 
            "version": "1.0.0",
            "protocol_version": "2025-06-18",
            "transport": "streamable-http",
            "endpoint": self.endpoint_path,
            "active_sessions": len(self.sessions),
            "timestamp": time.time()
        }
        return web.json_response(health_data)
    
    async def _handle_status_check(self, request: web.Request) -> web.Response:
        """Handle detailed status check"""
        status_data = {
            "server_info": {
                "name": "mem0-mcp-server",
                "version": "1.0.0", 
                "protocol_version": "2025-06-18",
                "capabilities": ["tools", "resources", "prompts", "logging"]
            },
            "transport_info": {
                "type": "streamable-http",
                "host": self.host,
                "port": self.port,
                "endpoint": self.endpoint_path
            },
            "session_info": {
                "active_sessions": len(self.sessions),
                "sessions": [
                    {
                        "session_id": s.session_id[:8] + "...",
                        "created_at": s.created_at,
                        "last_activity": s.last_activity,
                        "initialized": s.initialized
                    } for s in self.sessions.values()
                ]
            },
            "timestamp": time.time()
        }
        return web.json_response(status_data)
    
    async def _handle_mcp_endpoint(self, request: web.Request) -> web.Response:
        """Main MCP endpoint handler"""
        
        # Extract user_id from URL path parameter if present
        # Support both /mcp and /mcp/{user_id} formats
        user_id = request.match_info.get('user_id')
        
        # Store user_id in request for later use
        request['extracted_user_id'] = user_id
        
        method = request.method
        
        if method == 'POST':
            return await self._handle_post(request)
        elif method == 'GET':
            return await self._handle_get(request)
        elif method == 'DELETE':
            return await self._handle_delete(request)
        else:
            raise web.HTTPMethodNotAllowed(['GET', 'POST', 'DELETE'])
    
    async def start(self):
        """Start the HTTP server"""
        
        # Create web application
        self.app = web.Application()
        
        # Add routes - MCP 2025-06-18 single endpoint requirement
        # The server MUST provide a single HTTP endpoint path that supports POST and GET methods
        self.app.router.add_route('*', self.endpoint_path, self._handle_mcp_endpoint)
        self.app.router.add_route('*', self.endpoint_path + '/{user_id}', self._handle_mcp_endpoint)
        
        # Add health check endpoints for debugging
        self.app.router.add_route('GET', '/', self._handle_health_check)
        self.app.router.add_route('GET', '/health', self._handle_health_check)
        self.app.router.add_route('GET', '/status', self._handle_status_check)
        
        # Add CORS headers
        self.app.middlewares.append(self._cors_middleware)
        
        # Start server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info(f"Streamable HTTP transport started on {self.host}:{self.port}{self.endpoint_path}")
    
    async def stop(self):
        """Stop the HTTP server"""
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.site:
            await self.site.stop()
        
        if self.runner:
            await self.runner.cleanup()
        
        self.sessions.clear()
        logger.info("Streamable HTTP transport stopped")
    
    @web.middleware
    async def _cors_middleware(self, request: web.Request, handler):
        """CORS middleware for handling cross-origin requests"""
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            response = web.Response()
        else:
            response = await handler(request)
        
        # Add CORS headers
        origin = request.headers.get('Origin')
        if "*" in self.allowed_origins:
            # Allow all origins
            response.headers['Access-Control-Allow-Origin'] = '*'
        elif origin and any(origin.startswith(allowed) for allowed in self.allowed_origins):
            # Allow specific origins
            response.headers['Access-Control-Allow-Origin'] = origin
        
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, MCP-Protocol-Version, Mcp-Session-Id, Last-Event-ID, X-User-Id'
        response.headers['Access-Control-Expose-Headers'] = 'Mcp-Session-Id, Mcp-Session-Status, Mcp-Session-Capabilities'
        response.headers['Access-Control-Max-Age'] = '86400'
        
        return response
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        return {
            "active_sessions": len(self.sessions),
            "sessions": [
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at,
                    "last_activity": session.last_activity,
                    "initialized": session.initialized,
                    "active_streams": len(session.streams)
                }
                for session in self.sessions.values()
            ]
        }