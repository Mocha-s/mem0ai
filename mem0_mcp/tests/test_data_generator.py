"""
Test Data Generator for MCP Compliance Analysis Tests

Creates realistic code samples with known MCP violations for testing
the accuracy of compliance analysis detection.
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ViolationScenario:
    """Represents a specific MCP violation scenario"""
    name: str
    description: str
    violation_type: str
    severity: str
    risk_score: int
    code_sample: str
    expected_line: int
    remediation: str

class MCPViolationTestDataGenerator:
    """Generates test data with known MCP violations for testing compliance analysis"""
    
    def __init__(self):
        self.scenarios = self._create_violation_scenarios()
        self.correct_implementations = self._create_correct_implementations()
    
    def _create_violation_scenarios(self) -> List[ViolationScenario]:
        """Create comprehensive set of MCP violation scenarios"""
        return [
            # Protocol Foundation Violations
            ViolationScenario(
                name="incorrect_jsonrpc_version",
                description="Using incorrect JSON-RPC version",
                violation_type="protocol_violation",
                severity="critical",
                risk_score=9,
                code_sample='''
async def create_response(self, result, request_id):
    """Create JSON-RPC response with wrong version"""
    return {
        "jsonrpc": "1.0",  # VIOLATION: Should be "2.0"
        "result": result,
        "id": request_id
    }''',
                expected_line=5,
                remediation='Change "jsonrpc": "1.0" to "jsonrpc": "2.0"'
            ),
            
            ViolationScenario(
                name="missing_protocol_version",
                description="Missing MCP protocol version declaration",
                violation_type="version_violation",
                severity="high",
                risk_score=8,
                code_sample='''
class MCPServerConfig:
    """Server configuration missing protocol version"""
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 8080
        # VIOLATION: Missing protocol_version = "2025-06-18"
        self.session_timeout = 3600''',
                expected_line=7,
                remediation='Add protocol_version: str = "2025-06-18"'
            ),
            
            ViolationScenario(
                name="wrong_protocol_version",
                description="Incorrect MCP protocol version",
                violation_type="version_violation", 
                severity="high",
                risk_score=7,
                code_sample='''
class MCPServer:
    def __init__(self):
        self.protocol_version = "2024-11-05"  # VIOLATION: Wrong version
        self.capabilities = {}''',
                expected_line=4,
                remediation='Change to protocol_version = "2025-06-18"'
            ),
            
            # Transport Layer Violations
            ViolationScenario(
                name="missing_session_header_validation",
                description="Missing Mcp-Session-Id header validation",
                violation_type="transport_violation",
                severity="high", 
                risk_score=7,
                code_sample='''
async def handle_request(self, request):
    """Handle request without session validation"""
    # VIOLATION: Missing session header validation
    data = await request.json()
    return await self.process_request(data)''',
                expected_line=5,
                remediation='Add: session_id = request.headers.get("Mcp-Session-Id")'
            ),
            
            ViolationScenario(
                name="incorrect_sse_implementation",
                description="SSE implementation missing required features",
                violation_type="transport_violation",
                severity="medium",
                risk_score=6,
                code_sample='''
async def stream_events(self, request):
    """SSE stream missing event ID and resumability"""
    async def event_generator():
        for event in self.events:
            # VIOLATION: Missing event ID and resumability
            yield {"data": json.dumps(event)}
    
    return sse_response(request, event_generator())''',
                expected_line=6,
                remediation='Add event ID: yield {"id": event_id, "data": json.dumps(event)}'
            ),
            
            # Security Violations
            ViolationScenario(
                name="missing_origin_validation",
                description="No origin header validation for security",
                violation_type="security_violation",
                severity="critical",
                risk_score=9,
                code_sample='''
async def handle_cors(self, request):
    """CORS handler without origin validation"""
    # VIOLATION: Missing origin validation
    response = web.Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response''',
                expected_line=5,
                remediation='Add: origin = request.headers.get("Origin"); validate origin'
            ),
            
            ViolationScenario(
                name="insecure_cors_configuration", 
                description="Overly permissive CORS configuration",
                violation_type="security_violation",
                severity="high",
                risk_score=8,
                code_sample='''
def setup_cors(self, app):
    """Insecure CORS setup"""
    app.router.add_options("*", self.handle_options)
    # VIOLATION: Wildcard origin is insecure
    self.allowed_origins = ["*"]''',
                expected_line=6,
                remediation='Use specific origins: ["http://localhost", "http://127.0.0.1"]'
            ),
            
            ViolationScenario(
                name="weak_session_management",
                description="Session ID generation is predictable",
                violation_type="security_violation", 
                severity="medium",
                risk_score=6,
                code_sample='''
def create_session(self):
    """Weak session ID generation"""
    import time
    # VIOLATION: Predictable session ID
    session_id = f"session_{int(time.time())}"
    return MCPSession(session_id=session_id)''',
                expected_line=6,
                remediation='Use cryptographically secure random: uuid.uuid4().hex'
            ),
            
            # Tool Implementation Violations
            ViolationScenario(
                name="invalid_tool_schema",
                description="Tool definition missing required schema fields",
                violation_type="tool_violation",
                severity="medium",
                risk_score=5,
                code_sample='''
def list_tools(self):
    """Tool list with invalid schema"""
    return [
        {
            "name": "memory_search",
            "description": "Search memories"
            # VIOLATION: Missing inputSchema
        }
    ]''',
                expected_line=8,
                remediation='Add "inputSchema": {"type": "object", "properties": {...}}'
            ),
            
            ViolationScenario(
                name="incorrect_error_handling",
                description="Non-standard JSON-RPC error codes",
                violation_type="tool_violation",
                severity="medium", 
                risk_score=4,
                code_sample='''
def handle_tool_error(self, error):
    """Incorrect error code format"""
    return {
        "error": {
            "code": -1000,  # VIOLATION: Non-standard error code
            "message": str(error)
        }
    }''',
                expected_line=6,
                remediation='Use standard codes: -32600, -32601, -32602, -32603'
            ),
            
            # Message Flow Violations
            ViolationScenario(
                name="missing_initialization_sequence",
                description="Server doesn't implement proper initialization",
                violation_type="flow_violation",
                severity="high",
                risk_score=7,
                code_sample='''
async def start_server(self):
    """Server start without initialization handshake"""
    self.app = web.Application()
    # VIOLATION: Missing initialize/initialized sequence
    self.app.router.add_post("/mcp", self.handle_request)
    await self.run_app()''',
                expected_line=5,
                remediation='Implement initialize method and wait for initialized notification'
            ),
            
            ViolationScenario(
                name="missing_request_id_correlation",
                description="Responses don't correlate with request IDs",
                violation_type="flow_violation",
                severity="medium",
                risk_score=5,
                code_sample='''
async def process_request(self, request_data):
    """Request processing without ID correlation"""
    method = request_data.get("method")
    result = await self.execute_method(method)
    
    # VIOLATION: Response missing request ID correlation
    return {"jsonrpc": "2.0", "result": result}''',
                expected_line=7,
                remediation='Add "id": request_data.get("id") to response'
            )
        ]
    
    def _create_correct_implementations(self) -> Dict[str, str]:
        """Create correct MCP implementations for negative testing"""
        return {
            "correct_protocol": '''
"""Correct MCP Protocol Implementation"""
import json
import uuid

class CorrectMCPServer:
    def __init__(self):
        # CORRECT: Proper protocol version
        self.protocol_version = "2025-06-18"
        self.allowed_origins = [
            "http://localhost",
            "http://127.0.0.1",
            "vscode-file://vscode-app"
        ]
    
    async def create_response(self, result, request_id):
        """CORRECT: Proper JSON-RPC 2.0 response"""
        return {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }
    
    def validate_origin(self, request):
        """CORRECT: Origin validation implemented"""
        origin = request.headers.get("Origin")
        return origin in self.allowed_origins
    
    def create_session(self):
        """CORRECT: Secure session ID generation"""
        session_id = uuid.uuid4().hex
        return MCPSession(session_id=session_id)
''',
            
            "correct_transport": '''
"""Correct Streamable HTTP Transport"""
import asyncio
import json
from aiohttp import web
from aiohttp_sse import sse_response

class CorrectTransport:
    def __init__(self):
        self.protocol_version = "2025-06-18"
        self.event_counter = 0
    
    async def handle_request(self, request):
        """CORRECT: Request handling with session validation"""
        session_id = request.headers.get("Mcp-Session-Id")
        if not session_id:
            return web.json_response(
                {"error": {"code": -32600, "message": "Missing session ID"}},
                status=400
            )
        
        origin = request.headers.get("Origin")
        if not self.validate_origin(origin):
            return web.json_response(
                {"error": {"code": -32600, "message": "Invalid origin"}},
                status=403
            )
        
        data = await request.json()
        return await self.process_request(data)
    
    async def stream_events(self, request):
        """CORRECT: SSE with event IDs and resumability"""
        last_event_id = request.headers.get("Last-Event-ID")
        
        async def event_generator():
            start_id = int(last_event_id) if last_event_id else 0
            
            for event in self.get_events_from(start_id):
                self.event_counter += 1
                yield {
                    "id": str(self.event_counter),
                    "data": json.dumps(event)
                }
        
        return sse_response(request, event_generator())
''',
            
            "correct_tools": '''
"""Correct Tool Implementation"""
import json
from typing import Dict, Any, List

class CorrectToolManager:
    def list_tools(self) -> List[Dict[str, Any]]:
        """CORRECT: Tools with proper schema"""
        return [
            {
                "name": "memory_search",
                "description": "Search through stored memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            }
        ]
    
    def handle_tool_error(self, error: Exception) -> Dict[str, Any]:
        """CORRECT: Standard JSON-RPC error codes"""
        if isinstance(error, ValueError):
            code = -32602  # Invalid params
        elif isinstance(error, NotImplementedError):
            code = -32601  # Method not found
        else:
            code = -32603  # Internal error
            
        return {
            "error": {
                "code": code,
                "message": str(error)
            }
        }
'''
        }
    
    def generate_test_files(self, output_dir: Path):
        """Generate test files with known violations"""
        output_dir.mkdir(exist_ok=True)
        
        # Generate violation files
        for i, scenario in enumerate(self.scenarios):
            filename = f"violation_{i:02d}_{scenario.name}.py"
            file_path = output_dir / filename
            
            # Create complete file content with violation
            content = f'"""\nMCP Violation Test Case: {scenario.description}\n\nExpected Violation:\n- Type: {scenario.violation_type}\n- Severity: {scenario.severity}\n- Risk Score: {scenario.risk_score}\n- Line: {scenario.expected_line}\n- Remediation: {scenario.remediation}\n"""\n{scenario.code_sample}\n'
            
            file_path.write_text(content)
        
        # Generate correct implementation files
        for name, content in self.correct_implementations.items():
            file_path = output_dir / f"{name}.py"
            file_path.write_text(content)
        
        # Generate test manifest
        manifest = {
            "violation_scenarios": [
                {
                    "file": f"violation_{i:02d}_{s.name}.py",
                    "name": s.name,
                    "description": s.description,
                    "violation_type": s.violation_type,
                    "severity": s.severity,
                    "risk_score": s.risk_score,
                    "expected_line": s.expected_line,
                    "remediation": s.remediation
                }
                for i, s in enumerate(self.scenarios)
            ],
            "correct_implementations": list(self.correct_implementations.keys()),
            "total_violations": len(self.scenarios),
            "severity_distribution": self._get_severity_distribution()
        }
        
        manifest_path = output_dir / "test_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        return manifest
    
    def _get_severity_distribution(self) -> Dict[str, int]:
        """Get distribution of violation severities"""
        distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for scenario in self.scenarios:
            distribution[scenario.severity] += 1
        return distribution
    
    def get_expected_violations_for_file(self, filename: str) -> List[ViolationScenario]:
        """Get expected violations for a specific test file"""
        violations = []
        for i, scenario in enumerate(self.scenarios):
            expected_filename = f"violation_{i:02d}_{scenario.name}.py"
            if filename == expected_filename:
                violations.append(scenario)
        return violations

class ComplianceTestValidator:
    """Validates compliance analysis results against expected outcomes"""
    
    def __init__(self, test_data_generator: MCPViolationTestDataGenerator):
        self.generator = test_data_generator
    
    def validate_analysis_results(self, results: List[Dict[str, Any]], test_file: str) -> Dict[str, Any]:
        """Validate analysis results against expected violations"""
        expected_violations = self.generator.get_expected_violations_for_file(test_file)
        
        validation_result = {
            "file": test_file,
            "expected_violations": len(expected_violations),
            "detected_violations": len(results),
            "correctly_detected": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "accuracy_score": 0.0,
            "details": []
        }
        
        # Check for correctly detected violations
        for expected in expected_violations:
            found_match = False
            for detected in results:
                if self._violations_match(expected, detected):
                    found_match = True
                    validation_result["correctly_detected"] += 1
                    validation_result["details"].append({
                        "type": "correct_detection",
                        "expected": expected.name,
                        "detected_severity": detected.get("severity"),
                        "line_accuracy": abs(expected.expected_line - detected.get("line", 0)) <= 2
                    })
                    break
            
            if not found_match:
                validation_result["false_negatives"] += 1
                validation_result["details"].append({
                    "type": "false_negative", 
                    "expected": expected.name,
                    "expected_line": expected.expected_line,
                    "expected_severity": expected.severity
                })
        
        # Check for false positives
        for detected in results:
            found_match = False
            for expected in expected_violations:
                if self._violations_match(expected, detected):
                    found_match = True
                    break
            
            if not found_match:
                validation_result["false_positives"] += 1
                validation_result["details"].append({
                    "type": "false_positive",
                    "detected_line": detected.get("line"),
                    "detected_severity": detected.get("severity"),
                    "detected_description": detected.get("description")
                })
        
        # Calculate accuracy score
        total_expected = len(expected_violations)
        if total_expected > 0:
            validation_result["accuracy_score"] = validation_result["correctly_detected"] / total_expected
        
        return validation_result
    
    def _violations_match(self, expected: ViolationScenario, detected: Dict[str, Any]) -> bool:
        """Check if detected violation matches expected violation"""
        # Check severity match
        severity_match = expected.severity == detected.get("severity")
        
        # Check line proximity (within 2 lines is acceptable)
        line_proximity = abs(expected.expected_line - detected.get("line", 0)) <= 2
        
        # Check violation type similarity
        type_keywords = {
            "protocol_violation": ["protocol", "jsonrpc", "version"],
            "security_violation": ["origin", "cors", "security", "session"],
            "transport_violation": ["transport", "http", "sse", "header"],
            "tool_violation": ["tool", "schema", "error"],
            "flow_violation": ["flow", "initialization", "sequence"]
        }
        
        type_match = False
        expected_keywords = type_keywords.get(expected.violation_type, [])
        detected_description = detected.get("description", "").lower()
        
        for keyword in expected_keywords:
            if keyword in detected_description:
                type_match = True
                break
        
        return severity_match and line_proximity and type_match

if __name__ == "__main__":
    # Generate test data when run directly
    generator = MCPViolationTestDataGenerator()
    output_dir = Path(__file__).parent / "test_data" / "mcp_violations"
    
    print(f"Generating MCP violation test data in: {output_dir}")
    manifest = generator.generate_test_files(output_dir)
    
    print(f"Generated {manifest['total_violations']} violation scenarios")
    print(f"Severity distribution: {manifest['severity_distribution']}")
    print(f"Test manifest written to: {output_dir / 'test_manifest.json'}")