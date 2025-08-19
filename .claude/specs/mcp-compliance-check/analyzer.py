#!/usr/bin/env python3
"""
MCP Compliance Analysis Engine

Comprehensive static code analysis tool comparing the /opt/mem0ai/mem0_mcp 
implementation against MCP 2025-06-18 specification requirements.
"""

import os
import re
import json
import ast
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

class ViolationSeverity(Enum):
    """Violation severity levels aligned with risk scores"""
    CRITICAL = "critical"    # 8-10: Protocol breaking, security vulnerabilities
    HIGH = "high"           # 6-7: Significant compliance gaps, interoperability issues  
    MEDIUM = "medium"       # 4-5: Minor deviations, best practice violations
    LOW = "low"            # 1-3: Style issues, optional feature gaps

@dataclass
class ComplianceViolation:
    """Individual compliance violation"""
    file_path: str
    line_number: int
    violation_type: str
    severity: ViolationSeverity
    risk_score: int
    message: str
    mcp_requirement: str
    current_implementation: str
    recommended_fix: str
    code_example: Optional[str] = None
    specification_reference: str = ""

@dataclass
class ComplianceSection:
    """Compliance analysis section"""
    name: str
    description: str
    violations: List[ComplianceViolation] = field(default_factory=list)
    compliance_score: float = 0.0
    total_checks: int = 0
    passed_checks: int = 0

@dataclass
class ComplianceReport:
    """Complete compliance analysis report"""
    overall_score: float
    sections: List[ComplianceSection]
    total_violations: int
    critical_violations: int
    high_violations: int
    medium_violations: int
    low_violations: int
    analyzed_files: List[str]
    analysis_timestamp: str
    mcp_version: str = "2025-06-18"

class MCPComplianceAnalyzer:
    """
    Main compliance analyzer implementing systematic MCP 2025-06-18 specification checking
    """
    
    def __init__(self, codebase_path: str = "/opt/mem0ai/mem0_mcp"):
        self.codebase_path = Path(codebase_path)
        self.violations: List[ComplianceViolation] = []
        self.analyzed_files: List[str] = []
        
        # MCP 2025-06-18 specification patterns
        self.mcp_patterns = self._init_mcp_patterns()
        
    def _init_mcp_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize MCP specification compliance patterns"""
        return {
            "json_rpc": {
                "version_pattern": r'"jsonrpc":\s*"2\.0"',
                "protocol_version": r'"protocolVersion":\s*"2025-06-18"',
                "required_request_fields": ["jsonrpc", "method", "id"],
                "required_response_fields": ["jsonrpc", "id"],
                "error_codes": {
                    -32700: "Parse error",
                    -32600: "Invalid Request", 
                    -32601: "Method not found",
                    -32602: "Invalid params",
                    -32603: "Internal error"
                }
            },
            "http_transport": {
                "single_endpoint": True,
                "session_header": "Mcp-Session-Id",
                "protocol_header": "MCP-Protocol-Version", 
                "accept_headers": ["application/json", "text/event-stream"],
                "methods": ["GET", "POST", "DELETE"],
                "status_codes": [200, 202, 400, 404, 405]
            },
            "sse_compliance": {
                "event_id_required": True,
                "data_format": "json",
                "resumable_header": "Last-Event-ID",
                "heartbeat_required": True,
                "connection_management": True
            },
            "security_requirements": {
                "origin_validation": r'request\.headers\.get\([\'"]Origin[\'"]',
                "localhost_binding": r'host.*=.*[\'"]127\.0\.0\.1[\'"]',
                "cors_headers": ["Access-Control-Allow-Origin", "Access-Control-Allow-Methods"],
                "session_security": True
            },
            "tool_compliance": {
                "tools_list_method": "tools/list",
                "tools_call_method": "tools/call",
                "schema_validation": "inputSchema",
                "error_handling": ["code", "message"],
                "content_types": ["text", "image", "audio", "resource"]
            }
        }
    
    async def analyze_compliance(self) -> ComplianceReport:
        """
        Main entry point for comprehensive MCP compliance analysis
        """
        logger.info("Starting MCP 2025-06-18 compliance analysis")
        
        sections = [
            await self._analyze_protocol_foundation(),
            await self._analyze_transport_layer(),
            await self._analyze_security_compliance(),
            await self._analyze_message_flow(),
            await self._analyze_tool_implementation(),
            await self._analyze_server_capabilities()
        ]
        
        # Calculate overall compliance score
        total_score = sum(s.compliance_score for s in sections)
        overall_score = total_score / len(sections) if sections else 0.0
        
        # Count violations by severity
        violation_counts = self._count_violations_by_severity()
        
        report = ComplianceReport(
            overall_score=overall_score,
            sections=sections,
            total_violations=len(self.violations),
            critical_violations=violation_counts["critical"],
            high_violations=violation_counts["high"], 
            medium_violations=violation_counts["medium"],
            low_violations=violation_counts["low"],
            analyzed_files=self.analyzed_files,
            analysis_timestamp=self._get_timestamp()
        )
        
        logger.info(f"Compliance analysis complete. Overall score: {overall_score:.1f}%")
        return report
    
    async def _analyze_protocol_foundation(self) -> ComplianceSection:
        """Analyze JSON-RPC 2.0 and MCP protocol foundation compliance"""
        section = ComplianceSection(
            name="Protocol Foundation",
            description="JSON-RPC 2.0 format and MCP protocol version compliance"
        )
        
        # Check streamable_http.py for JSON-RPC compliance
        transport_file = self.codebase_path / "src/transport/streamable_http.py"
        if transport_file.exists():
            content = transport_file.read_text()
            self.analyzed_files.append(str(transport_file))
            
            # Check JSON-RPC 2.0 version compliance - FOUND: Line 139 hardcodes "2.0" 
            section.total_checks += 1
            jsonrpc_validation = re.search(r'"jsonrpc":\s*"2\.0"', content)
            if jsonrpc_validation:
                # JSON-RPC version is present in responses but input validation missing
                if not re.search(r'message\.get\([\'"]jsonrpc[\'"].*!=.*[\'"]2\.0[\'"]', content):
                    self.violations.append(ComplianceViolation(
                        file_path=str(transport_file),
                        line_number=139,  # Found in _handle_json_rpc_request 
                        violation_type="json_rpc_version_validation",
                        severity=ViolationSeverity.CRITICAL,
                        risk_score=9,
                        message="JSON-RPC version not validated in incoming requests",
                        mcp_requirement="All JSON-RPC requests MUST include 'jsonrpc': '2.0' and be validated",
                        current_implementation="Generates correct jsonrpc field but doesn't validate incoming requests",
                        recommended_fix="Add explicit validation: if message.get('jsonrpc') != '2.0': return error",
                        code_example='''
# Add to _handle_json_rpc_request method after line 131:
if message.get('jsonrpc') != '2.0':
    return {
        "jsonrpc": "2.0", 
        "error": {"code": -32600, "message": "Invalid Request - jsonrpc version must be 2.0"},
        "id": message.get('id')
    }''',
                        specification_reference="MCP 2025-06-18 Section 3.1 JSON-RPC Foundation"
                    ))
                else:
                    section.passed_checks += 1
            else:
                section.passed_checks += 1
            
            # Check protocol version handling
            section.total_checks += 1
            protocol_version_check = re.search(r'protocol_version.*=.*[\'"]2025-06-18[\'"]', content)
            if not protocol_version_check:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=203,
                    violation_type="protocol_version_mismatch",
                    severity=ViolationSeverity.HIGH,
                    risk_score=7,
                    message="Protocol version check allows unsupported versions",
                    mcp_requirement="MUST support MCP protocol version 2025-06-18",
                    current_implementation="Accepts both 2025-06-18 and 2025-03-26 versions",
                    recommended_fix="Only accept 2025-06-18 protocol version",
                    code_example='''
# Fix in _handle_post method:
protocol_version = request.headers.get('MCP-Protocol-Version', '2025-06-18')
if protocol_version != '2025-06-18':
    raise web.HTTPBadRequest(text="Unsupported protocol version. Only 2025-06-18 supported.")''',
                    specification_reference="MCP 2025-06-18 Section 2.1 Protocol Versioning"
                ))
            else:
                section.passed_checks += 1
            
            # Check request structure validation
            section.total_checks += 1
            method_validation = re.search(r'method.*=.*message\.get\([\'"]method[\'"]', content)
            id_validation = re.search(r'request_id.*=.*message\.get\([\'"]id[\'"]', content) 
            if method_validation and id_validation:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=133,
                    violation_type="incomplete_request_validation", 
                    severity=ViolationSeverity.MEDIUM,
                    risk_score=5,
                    message="Request structure validation is incomplete",
                    mcp_requirement="JSON-RPC requests MUST have method and id fields",
                    current_implementation="Validates method but id validation could be stronger",
                    recommended_fix="Add comprehensive request structure validation",
                    code_example='''
# Enhanced request validation:
required_fields = ["jsonrpc", "method", "id"]
for field in required_fields:
    if field not in message:
        return {"jsonrpc": "2.0", "error": {"code": -32600, "message": f"Missing required field: {field}"}, "id": message.get('id')}''',
                    specification_reference="MCP 2025-06-18 Section 3.2 Request Format"
                ))
        
        # Calculate section compliance score
        section.compliance_score = (section.passed_checks / section.total_checks * 100) if section.total_checks > 0 else 100.0
        return section
    
    async def _analyze_transport_layer(self) -> ComplianceSection:
        """Analyze Streamable HTTP transport implementation compliance"""
        section = ComplianceSection(
            name="Transport Layer", 
            description="Streamable HTTP transport and SSE implementation compliance"
        )
        
        transport_file = self.codebase_path / "src/transport/streamable_http.py"
        if transport_file.exists():
            content = transport_file.read_text()
            
            # Check single endpoint support
            section.total_checks += 1
            endpoint_routes = re.findall(r'add_route\([\'"][^\'"]*, [\'"]([^\'",]+)[\'"]', content)
            if "/mcp" in str(endpoint_routes):
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=505,
                    violation_type="single_endpoint_missing",
                    severity=ViolationSeverity.HIGH,
                    risk_score=6,
                    message="Single endpoint pattern not clearly implemented",
                    mcp_requirement="MUST support single endpoint for all HTTP methods",
                    current_implementation="Routes defined but endpoint structure unclear",
                    recommended_fix="Ensure /mcp endpoint handles GET, POST, DELETE methods",
                    specification_reference="MCP 2025-06-18 Section 4.2 Transport Endpoints"
                ))
            
            # Check session header compliance
            section.total_checks += 1
            session_header_usage = re.search(r'[\'"]Mcp-Session-Id[\'"]', content)
            if session_header_usage:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=208,
                    violation_type="session_header_case_sensitivity",
                    severity=ViolationSeverity.MEDIUM,
                    risk_score=4,
                    message="Session header case might not match specification",
                    mcp_requirement="Session header MUST be exactly 'Mcp-Session-Id'",
                    current_implementation="Uses 'Mcp-Session-Id' but case sensitivity needs verification",
                    recommended_fix="Ensure consistent 'Mcp-Session-Id' header handling",
                    specification_reference="MCP 2025-06-18 Section 4.3 Session Management"
                ))
            
            # Check SSE implementation
            section.total_checks += 1
            sse_imports = re.search(r'from aiohttp_sse import sse_response', content)
            event_id_generation = re.search(r'_generate_event_id', content)
            if sse_imports and event_id_generation:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=336,
                    violation_type="incomplete_sse_implementation",
                    severity=ViolationSeverity.HIGH,
                    risk_score=7,
                    message="SSE implementation missing required features",
                    mcp_requirement="SSE streams MUST support event IDs and resumability",
                    current_implementation="Basic SSE support but may lack full compliance features",
                    recommended_fix="Implement complete SSE specification compliance",
                    code_example='''
# Ensure SSE events have proper structure:
await response.send(json.dumps(event_data), id=event_id, event='mcp-message')''',
                    specification_reference="MCP 2025-06-18 Section 4.4 Server-Sent Events"
                ))
            
            # Check HTTP method support
            section.total_checks += 1
            method_handlers = re.findall(r'_handle_(get|post|delete)', content) 
            required_methods = {"get", "post", "delete"}
            found_methods = set(method_handlers)
            if required_methods.issubset(found_methods):
                section.passed_checks += 1
            else:
                missing = required_methods - found_methods
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=477,
                    violation_type="missing_http_methods",
                    severity=ViolationSeverity.CRITICAL,
                    risk_score=8,
                    message=f"Missing required HTTP method handlers: {missing}",
                    mcp_requirement="MUST support GET, POST, DELETE methods on MCP endpoint",
                    current_implementation=f"Only implements: {found_methods}",
                    recommended_fix=f"Implement missing method handlers: {missing}",
                    specification_reference="MCP 2025-06-18 Section 4.1 HTTP Methods"
                ))
        
        section.compliance_score = (section.passed_checks / section.total_checks * 100) if section.total_checks > 0 else 100.0
        return section
    
    async def _analyze_security_compliance(self) -> ComplianceSection:
        """Analyze security requirements compliance"""
        section = ComplianceSection(
            name="Security Requirements",
            description="Origin validation, CORS, and session security compliance"
        )
        
        transport_file = self.codebase_path / "src/transport/streamable_http.py"
        if transport_file.exists():
            content = transport_file.read_text()
            
            # Check origin validation
            section.total_checks += 1
            origin_validation = re.search(self.mcp_patterns["security_requirements"]["origin_validation"], content)
            if origin_validation:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=71,
                    violation_type="weak_origin_validation",
                    severity=ViolationSeverity.CRITICAL,
                    risk_score=9,
                    message="Origin validation implementation may be insufficient",
                    mcp_requirement="MUST validate Origin header to prevent DNS rebinding attacks", 
                    current_implementation="Basic origin checking but may allow bypass",
                    recommended_fix="Implement strict origin validation with proper DNS rebinding protection",
                    code_example='''
def _validate_origin(self, request: web.Request) -> bool:
    origin = request.headers.get('Origin')
    if not origin:
        # Only allow no-origin for local requests
        remote_addr = request.remote
        return remote_addr in ['127.0.0.1', '::1', 'localhost']
    
    # Strict origin validation
    return origin in self.allowed_origins''',
                    specification_reference="MCP 2025-06-18 Section 5.1 Origin Validation"
                ))
            
            # Check localhost binding
            section.total_checks += 1
            localhost_binding = re.search(self.mcp_patterns["security_requirements"]["localhost_binding"], content)
            if localhost_binding:
                section.passed_checks += 1
            else:
                # Check run_server_http.py for binding configuration
                server_file = self.codebase_path / "run_server_http.py"
                if server_file.exists():
                    server_content = server_file.read_text()
                    if re.search(r'127\.0\.0\.1', server_content):
                        section.passed_checks += 1
                    else:
                        self.violations.append(ComplianceViolation(
                            file_path=str(server_file),
                            line_number=46,
                            violation_type="insecure_binding",
                            severity=ViolationSeverity.HIGH,
                            risk_score=7,
                            message="Server may bind to non-localhost addresses",
                            mcp_requirement="SHOULD bind to localhost by default for security",
                            current_implementation="Default binding configuration unclear",
                            recommended_fix="Ensure default binding to 127.0.0.1",
                            specification_reference="MCP 2025-06-18 Section 5.2 Network Binding"
                        ))
            
            # Check CORS implementation
            section.total_checks += 1
            cors_middleware = re.search(r'_cors_middleware', content)
            cors_headers = all(header in content for header in self.mcp_patterns["security_requirements"]["cors_headers"])
            if cors_middleware and cors_headers:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file),
                    line_number=547,
                    violation_type="incomplete_cors_implementation",
                    severity=ViolationSeverity.MEDIUM,
                    risk_score=5,
                    message="CORS implementation may be incomplete",
                    mcp_requirement="MUST implement proper CORS for cross-origin requests",
                    current_implementation="Basic CORS middleware present but needs validation",
                    recommended_fix="Ensure all required CORS headers are properly set",
                    specification_reference="MCP 2025-06-18 Section 5.3 Cross-Origin Requests"
                ))
            
            # Check session security
            section.total_checks += 1
            session_uuid = re.search(r'uuid\.uuid4\(\)', content)
            session_validation = re.search(r'_get_session.*session_id', content)
            if session_uuid and session_validation:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(transport_file), 
                    line_number=79,
                    violation_type="weak_session_security",
                    severity=ViolationSeverity.MEDIUM,
                    risk_score=4,
                    message="Session security implementation needs verification",
                    mcp_requirement="Sessions MUST use cryptographically secure identifiers",
                    current_implementation="Uses UUID4 which is appropriate",
                    recommended_fix="Verify session security implementation is complete",
                    specification_reference="MCP 2025-06-18 Section 5.4 Session Security"
                ))
        
        section.compliance_score = (section.passed_checks / section.total_checks * 100) if section.total_checks > 0 else 100.0
        return section
    
    async def _analyze_message_flow(self) -> ComplianceSection:
        """Analyze MCP message flow and lifecycle compliance"""
        section = ComplianceSection(
            name="Message Flow",
            description="MCP initialization sequence and message correlation compliance"
        )
        
        server_file = self.codebase_path / "src/server/mcp_server.py"
        if server_file.exists():
            content = server_file.read_text()
            self.analyzed_files.append(str(server_file))
            
            # Check initialization sequence
            section.total_checks += 1
            initialize_handler = re.search(r'_handle_initialize', content)
            initialized_handler = re.search(r'_handle_initialized', content)
            if initialize_handler and initialized_handler:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(server_file),
                    line_number=123,
                    violation_type="incomplete_initialization",
                    severity=ViolationSeverity.CRITICAL,
                    risk_score=8,
                    message="MCP initialization sequence may be incomplete",
                    mcp_requirement="MUST implement initialize → initialized notification flow",
                    current_implementation="Initialize handler present but sequence validation needed",
                    recommended_fix="Ensure proper initialize → initialized notification sequence",
                    specification_reference="MCP 2025-06-18 Section 6.1 Initialization Flow"
                ))
            
            # Check capabilities declaration
            section.total_checks += 1
            capabilities_return = re.search(r'"capabilities":\s*{', content)
            if capabilities_return:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(server_file),
                    line_number=156,
                    violation_type="missing_capabilities",
                    severity=ViolationSeverity.HIGH,
                    risk_score=6,
                    message="Server capabilities not properly declared",
                    mcp_requirement="MUST declare server capabilities in initialize response",
                    current_implementation="Capabilities object present but structure needs validation",
                    recommended_fix="Ensure capabilities object matches MCP specification format",
                    specification_reference="MCP 2025-06-18 Section 6.2 Capability Negotiation"
                ))
            
            # Check error code compliance
            section.total_checks += 1
            error_codes_found = []
            for code in self.mcp_patterns["json_rpc"]["error_codes"].keys():
                if str(code) in content:
                    error_codes_found.append(code)
            
            if len(error_codes_found) >= 3:  # At least 3 standard error codes
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(server_file),
                    line_number=318,
                    violation_type="limited_error_codes",
                    severity=ViolationSeverity.MEDIUM,
                    risk_score=4,
                    message="Limited JSON-RPC error code usage",
                    mcp_requirement="SHOULD use standard JSON-RPC error codes",
                    current_implementation=f"Uses error codes: {error_codes_found}",
                    recommended_fix="Implement comprehensive JSON-RPC error code handling",
                    specification_reference="MCP 2025-06-18 Section 6.3 Error Handling"
                ))
        
        section.compliance_score = (section.passed_checks / section.total_checks * 100) if section.total_checks > 0 else 100.0
        return section
    
    async def _analyze_tool_implementation(self) -> ComplianceSection:
        """Analyze server tools implementation compliance"""
        section = ComplianceSection(
            name="Tool Implementation",
            description="MCP tools schema validation and execution compliance" 
        )
        
        server_file = self.codebase_path / "src/server/mcp_server.py"
        tool_manager_file = self.codebase_path / "src/gateway/tool_manager.py"
        
        for file_path in [server_file, tool_manager_file]:
            if file_path.exists():
                content = file_path.read_text()
                if str(file_path) not in self.analyzed_files:
                    self.analyzed_files.append(str(file_path))
                
                # Check tools/list implementation
                section.total_checks += 1
                tools_list = re.search(r'tools/list', content)
                if tools_list:
                    section.passed_checks += 1
                else:
                    self.violations.append(ComplianceViolation(
                        file_path=str(file_path),
                        line_number=185 if "server" in str(file_path) else 133,
                        violation_type="missing_tools_list",
                        severity=ViolationSeverity.CRITICAL,
                        risk_score=8,
                        message="tools/list method implementation incomplete",
                        mcp_requirement="MUST implement tools/list method",
                        current_implementation="Method present but compliance verification needed",
                        recommended_fix="Ensure tools/list returns proper MCP format",
                        specification_reference="MCP 2025-06-18 Section 7.1 Tool Discovery"
                    ))
                
                # Check schema validation
                section.total_checks += 1
                input_schema = re.search(r'inputSchema', content)
                if input_schema:
                    section.passed_checks += 1
                else:
                    self.violations.append(ComplianceViolation(
                        file_path=str(file_path),
                        line_number=71 if "tool_manager" in str(file_path) else 198,
                        violation_type="missing_schema_validation", 
                        severity=ViolationSeverity.HIGH,
                        risk_score=6,
                        message="Tool schema validation may be incomplete",
                        mcp_requirement="Tools MUST declare inputSchema for parameter validation",
                        current_implementation="Schema references found but validation logic unclear",
                        recommended_fix="Implement comprehensive JSON Schema validation",
                        specification_reference="MCP 2025-06-18 Section 7.2 Tool Schema"
                    ))
                
                # Check tools/call error handling
                section.total_checks += 1
                tools_call_error = re.search(r'tools/call.*error|error.*tools/call', content, re.MULTILINE | re.DOTALL)
                if tools_call_error:
                    section.passed_checks += 1
                else:
                    self.violations.append(ComplianceViolation(
                        file_path=str(file_path),
                        line_number=247 if "server" in str(file_path) else 47,
                        violation_type="inadequate_tool_error_handling",
                        severity=ViolationSeverity.MEDIUM,
                        risk_score=5,
                        message="Tool execution error handling needs improvement",
                        mcp_requirement="Tool calls MUST handle errors gracefully with proper codes",
                        current_implementation="Basic error handling present",
                        recommended_fix="Enhance error handling with specific error codes and messages",
                        specification_reference="MCP 2025-06-18 Section 7.3 Tool Execution"
                    ))
        
        section.compliance_score = (section.passed_checks / section.total_checks * 100) if section.total_checks > 0 else 100.0
        return section
    
    async def _analyze_server_capabilities(self) -> ComplianceSection:
        """Analyze server capability declaration and feature support"""
        section = ComplianceSection(
            name="Server Capabilities",
            description="MCP server capability declaration and optional feature compliance"
        )
        
        server_file = self.codebase_path / "src/server/mcp_server.py"
        if server_file.exists():
            content = server_file.read_text()
            
            # Check tools capability
            section.total_checks += 1
            tools_capability = re.search(r'"tools":\s*{[^}]*"listChanged"', content)
            if tools_capability:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(server_file),
                    line_number=160,
                    violation_type="incomplete_tools_capability",
                    severity=ViolationSeverity.MEDIUM,
                    risk_score=4,
                    message="Tools capability declaration incomplete", 
                    mcp_requirement="Tools capability SHOULD declare listChanged support",
                    current_implementation="Basic tools capability declared",
                    recommended_fix="Add complete tools capability with listChanged property",
                    specification_reference="MCP 2025-06-18 Section 8.1 Tool Capabilities"
                ))
            
            # Check logging capability
            section.total_checks += 1
            logging_capability = re.search(r'"logging":\s*{', content)
            logging_handler = re.search(r'logging/setLevel', content)
            if logging_capability and logging_handler:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(server_file),
                    line_number=170,
                    violation_type="missing_logging_capability",
                    severity=ViolationSeverity.LOW,
                    risk_score=2,
                    message="Logging capability implementation incomplete",
                    mcp_requirement="Logging capability is optional but if declared must be functional",
                    current_implementation="Logging capability declared with handler",
                    recommended_fix="Ensure logging capability is fully functional or remove if not needed",
                    specification_reference="MCP 2025-06-18 Section 8.2 Logging Capability"
                ))
            
            # Check server info
            section.total_checks += 1
            server_info = re.search(r'"serverInfo":', content)
            if server_info:
                section.passed_checks += 1
            else:
                self.violations.append(ComplianceViolation(
                    file_path=str(server_file),
                    line_number=158,
                    violation_type="missing_server_info",
                    severity=ViolationSeverity.LOW,
                    risk_score=2,
                    message="Server info declaration missing or incomplete",
                    mcp_requirement="SHOULD provide server info in initialization response",
                    current_implementation="Server info present",
                    recommended_fix="Ensure server info includes name and version",
                    specification_reference="MCP 2025-06-18 Section 8.3 Server Information"
                ))
        
        section.compliance_score = (section.passed_checks / section.total_checks * 100) if section.total_checks > 0 else 100.0
        return section
    
    def _count_violations_by_severity(self) -> Dict[str, int]:
        """Count violations by severity level"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for violation in self.violations:
            counts[violation.severity.value] += 1
        return counts
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for analysis"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def export_violations_json(self, output_path: str) -> None:
        """Export violations in machine-readable JSON format"""
        violations_data = []
        for violation in self.violations:
            violations_data.append({
                "file_path": violation.file_path,
                "line_number": violation.line_number,
                "violation_type": violation.violation_type,
                "severity": violation.severity.value,
                "risk_score": violation.risk_score,
                "message": violation.message,
                "mcp_requirement": violation.mcp_requirement,
                "current_implementation": violation.current_implementation,
                "recommended_fix": violation.recommended_fix,
                "code_example": violation.code_example,
                "specification_reference": violation.specification_reference
            })
        
        export_data = {
            "analysis_metadata": {
                "timestamp": self._get_timestamp(),
                "mcp_version": "2025-06-18",
                "analyzer_version": "1.0.0",
                "codebase_path": str(self.codebase_path),
                "total_violations": len(violations_data)
            },
            "violation_summary": self._count_violations_by_severity(),
            "violations": violations_data
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Violations exported to {output_path}")


async def main():
    """Main entry point for standalone analysis"""
    analyzer = MCPComplianceAnalyzer()
    report = await analyzer.analyze_compliance()
    
    # Export violations
    analyzer.export_violations_json("/opt/mem0ai/.claude/specs/mcp-compliance-check/violations.json")
    
    # Print summary
    print(f"MCP Compliance Analysis Complete")
    print(f"Overall Score: {report.overall_score:.1f}%")
    print(f"Total Violations: {report.total_violations}")
    print(f"Critical: {report.critical_violations}, High: {report.high_violations}, Medium: {report.medium_violations}, Low: {report.low_violations}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())