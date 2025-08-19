"""
Integration Tests for MCP Compliance Analysis

Tests the compliance analyzer against the actual /opt/mem0ai/mem0_mcp codebase
to validate accuracy of violation detection and reporting.
"""

import pytest
import json
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

# Import the test data generator
from test_data_generator import MCPViolationTestDataGenerator, ComplianceTestValidator

@dataclass
class CodebaseAnalysisResult:
    """Results from analyzing the actual codebase"""
    file_path: Path
    violations: List[Dict[str, Any]]
    analysis_time: float
    file_size: int
    line_count: int
    compliance_score: float

class ActualCodebaseIntegrationTester:
    """Integration tester for the actual MCP codebase"""
    
    def __init__(self):
        self.mcp_root = Path("/opt/mem0ai/mem0_mcp")
        self.key_files = self._discover_key_files()
        self.test_data_generator = MCPViolationTestDataGenerator()
        self.validator = ComplianceTestValidator(self.test_data_generator)
    
    def _discover_key_files(self) -> List[Path]:
        """Discover key files in the MCP codebase for analysis"""
        patterns = [
            "src/transport/streamable_http.py",
            "src/server/mcp_server.py", 
            "src/protocol/messages.py",
            "src/gateway/tool_manager.py",
            "src/services/*/service.py",
            "run_server_http.py",
            "run_server.py"
        ]
        
        files = []
        for pattern in patterns:
            if "*" in pattern:
                # Handle glob patterns
                matches = list(self.mcp_root.glob(pattern))
                files.extend(matches)
            else:
                # Handle direct file paths
                file_path = self.mcp_root / pattern
                if file_path.exists():
                    files.append(file_path)
        
        return files
    
    def analyze_codebase_structure(self) -> Dict[str, Any]:
        """Analyze the structure of the MCP codebase"""
        structure_analysis = {
            "total_files": 0,
            "python_files": 0,
            "total_lines": 0,
            "file_sizes": {},
            "import_dependencies": {},
            "missing_files": [],
            "analysis_coverage": 0.0
        }
        
        # Check for expected files
        expected_files = [
            "src/transport/streamable_http.py",
            "src/server/mcp_server.py",
            "src/protocol/messages.py",
            "run_server_http.py"
        ]
        
        for expected_file in expected_files:
            file_path = self.mcp_root / expected_file
            if file_path.exists():
                structure_analysis["total_files"] += 1
                if file_path.suffix == ".py":
                    structure_analysis["python_files"] += 1
                    
                    # Analyze file
                    content = file_path.read_text()
                    lines = len(content.split('\n'))
                    structure_analysis["total_lines"] += lines
                    structure_analysis["file_sizes"][str(file_path)] = len(content)
                    
                    # Extract imports
                    try:
                        tree = ast.parse(content)
                        imports = []
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                imports.extend([alias.name for alias in node.names])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports.append(node.module)
                        
                        structure_analysis["import_dependencies"][str(file_path)] = imports
                    except SyntaxError:
                        structure_analysis["import_dependencies"][str(file_path)] = ["PARSE_ERROR"]
            else:
                structure_analysis["missing_files"].append(expected_file)
        
        structure_analysis["analysis_coverage"] = structure_analysis["python_files"] / len(expected_files)
        return structure_analysis

class TestActualCodebaseCompliance:
    """Test suite for actual MCP codebase compliance"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.tester = ActualCodebaseIntegrationTester()
        self.mcp_root = Path("/opt/mem0ai/mem0_mcp")
        
    def test_codebase_structure_analysis(self):
        """Test analysis of the actual codebase structure"""
        structure = self.tester.analyze_codebase_structure()
        
        # Validate structure analysis
        assert structure["total_files"] > 0, "Should find files in the codebase"
        assert structure["python_files"] > 0, "Should find Python files"
        assert structure["analysis_coverage"] > 0.5, "Should cover majority of expected files"
        
        # Check for critical files
        critical_files = [
            "src/server/mcp_server.py",
            "src/transport/streamable_http.py"
        ]
        
        found_critical = 0
        for critical_file in critical_files:
            if (self.mcp_root / critical_file).exists():
                found_critical += 1
        
        assert found_critical >= 1, f"Should find at least 1 critical file, found {found_critical}"
    
    def test_transport_layer_compliance(self):
        """Test compliance analysis of the transport layer"""
        transport_file = self.mcp_root / "src/transport/streamable_http.py"
        
        if not transport_file.exists():
            pytest.skip("Transport file not found")
        
        # Analyze transport file for MCP compliance
        violations = self._analyze_file_for_violations(transport_file)
        
        # Transport layer compliance checks
        compliance_checks = {
            "session_header_usage": self._check_session_header_usage(transport_file),
            "sse_implementation": self._check_sse_implementation(transport_file),
            "cors_security": self._check_cors_security(transport_file),
            "jsonrpc_format": self._check_jsonrpc_format(transport_file)
        }
        
        # Validate compliance checks
        for check_name, check_result in compliance_checks.items():
            assert check_result["implemented"], f"Transport layer missing {check_name}: {check_result.get('details', '')}"
    
    def test_server_implementation_compliance(self):
        """Test compliance of the MCP server implementation"""
        server_file = self.mcp_root / "src/server/mcp_server.py"
        
        if not server_file.exists():
            pytest.skip("Server file not found")
        
        content = server_file.read_text()
        
        # Server compliance checks
        protocol_version_check = self._check_protocol_version_declaration(content)
        initialization_check = self._check_initialization_sequence(content)
        capability_check = self._check_capability_declaration(content)
        
        assert protocol_version_check["valid"], f"Protocol version issue: {protocol_version_check['details']}"
        assert initialization_check["implemented"], f"Initialization sequence issue: {initialization_check['details']}"
        assert capability_check["implemented"], f"Capability declaration issue: {capability_check['details']}"
    
    def test_protocol_message_compliance(self):
        """Test compliance of protocol message handling"""
        protocol_file = self.mcp_root / "src/protocol/messages.py"
        
        if not protocol_file.exists():
            pytest.skip("Protocol messages file not found")
        
        content = protocol_file.read_text()
        
        # Message format compliance checks
        message_structure_check = self._check_message_structure(content)
        error_handling_check = self._check_error_handling_format(content)
        
        assert message_structure_check["compliant"], f"Message structure issue: {message_structure_check['details']}"
        assert error_handling_check["compliant"], f"Error handling issue: {error_handling_check['details']}"
    
    def test_tool_implementation_compliance(self):
        """Test compliance of tool implementations"""
        tool_manager_file = self.mcp_root / "src/gateway/tool_manager.py"
        
        if not tool_manager_file.exists():
            pytest.skip("Tool manager file not found")
        
        content = tool_manager_file.read_text()
        
        # Tool compliance checks
        schema_validation_check = self._check_tool_schema_validation(content)
        tool_registration_check = self._check_tool_registration_format(content)
        
        assert schema_validation_check["implemented"], f"Schema validation issue: {schema_validation_check['details']}"
        assert tool_registration_check["compliant"], f"Tool registration issue: {tool_registration_check['details']}"
    
    def test_security_implementation_validation(self):
        """Test security implementation against MCP requirements"""
        transport_file = self.mcp_root / "src/transport/streamable_http.py"
        server_file = self.mcp_root / "src/server/mcp_server.py"
        
        security_findings = {
            "origin_validation": False,
            "session_security": False,
            "cors_configuration": False,
            "localhost_binding": False
        }
        
        # Check transport layer security
        if transport_file.exists():
            transport_content = transport_file.read_text()
            
            # Origin validation
            if re.search(r'headers\.get\([\'"]Origin[\'"]', transport_content, re.IGNORECASE):
                security_findings["origin_validation"] = True
            
            # Session security
            if re.search(r'session.*id|Mcp-Session-Id', transport_content, re.IGNORECASE):
                security_findings["session_security"] = True
            
            # CORS configuration
            if re.search(r'Access-Control-Allow-Origin|cors', transport_content, re.IGNORECASE):
                security_findings["cors_configuration"] = True
        
        # Check server security configuration
        if server_file.exists():
            server_content = server_file.read_text()
            
            # Localhost binding
            if re.search(r'127\.0\.0\.1|localhost', server_content):
                security_findings["localhost_binding"] = True
        
        # Validate security implementation
        critical_security = ["origin_validation", "localhost_binding"]
        for critical in critical_security:
            assert security_findings[critical], f"Critical security feature missing: {critical}"
    
    def test_performance_under_load(self):
        """Test compliance analyzer performance with actual codebase"""
        start_time = time.time()
        
        analysis_results = []
        for file_path in self.tester.key_files[:5]:  # Test with first 5 files
            if file_path.exists():
                file_start = time.time()
                violations = self._analyze_file_for_violations(file_path)
                file_time = time.time() - file_start
                
                analysis_results.append(CodebaseAnalysisResult(
                    file_path=file_path,
                    violations=violations,
                    analysis_time=file_time,
                    file_size=file_path.stat().st_size,
                    line_count=len(file_path.read_text().split('\n')),
                    compliance_score=self._calculate_compliance_score(violations)
                ))
        
        total_time = time.time() - start_time
        
        # Performance assertions
        assert total_time < 10.0, f"Analysis took too long: {total_time}s"
        
        for result in analysis_results:
            assert result.analysis_time < 5.0, f"File analysis too slow: {result.file_path} took {result.analysis_time}s"
            
            # Performance should scale with file size
            time_per_kb = result.analysis_time / (result.file_size / 1024) if result.file_size > 0 else 0
            assert time_per_kb < 0.1, f"Analysis inefficient for {result.file_path}: {time_per_kb}s per KB"
    
    def test_violation_reporting_accuracy(self):
        """Test accuracy of violation reporting with line numbers"""
        # Generate test data with known violations
        test_data_dir = Path("/tmp/mcp_test_violations")
        self.tester.test_data_generator.generate_test_files(test_data_dir)
        
        # Analyze test files and validate results
        violation_files = list(test_data_dir.glob("violation_*.py"))
        validation_results = []
        
        for test_file in violation_files[:3]:  # Test first 3 files
            violations = self._analyze_file_for_violations(test_file)
            validation = self.tester.validator.validate_analysis_results(
                violations, test_file.name
            )
            validation_results.append(validation)
        
        # Clean up test data
        import shutil
        shutil.rmtree(test_data_dir, ignore_errors=True)
        
        # Validate accuracy
        total_accuracy = sum(v["accuracy_score"] for v in validation_results) / len(validation_results)
        assert total_accuracy > 0.7, f"Accuracy too low: {total_accuracy}"
        
        false_positive_rate = sum(v["false_positives"] for v in validation_results) / sum(v["detected_violations"] for v in validation_results if v["detected_violations"] > 0)
        assert false_positive_rate < 0.3, f"Too many false positives: {false_positive_rate}"
    
    # Helper methods for compliance checking
    def _analyze_file_for_violations(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a file for MCP violations (mock implementation)"""
        violations = []
        content = file_path.read_text()
        
        # Mock violation detection - would use real analyzer in production
        for line_num, line in enumerate(content.split('\n'), 1):
            # Check for JSON-RPC version issues
            jsonrpc_match = re.search(r'"jsonrpc":\s*"([^"]*)"', line)
            if jsonrpc_match and jsonrpc_match.group(1) != "2.0":
                violations.append({
                    "type": "protocol_violation",
                    "severity": "critical",
                    "risk_score": 9,
                    "line": line_num,
                    "description": f"Incorrect JSON-RPC version: {jsonrpc_match.group(1)}"
                })
            
            # Check for protocol version issues
            protocol_match = re.search(r'protocol_version.*=.*"([^"]*)"', line)
            if protocol_match and protocol_match.group(1) != "2025-06-18":
                violations.append({
                    "type": "version_violation",
                    "severity": "high",
                    "risk_score": 7,
                    "line": line_num,
                    "description": f"Incorrect protocol version: {protocol_match.group(1)}"
                })
        
        return violations
    
    def _check_session_header_usage(self, file_path: Path) -> Dict[str, Any]:
        """Check for proper session header usage"""
        content = file_path.read_text()
        
        patterns = [
            r'Mcp-Session-Id',
            r'headers\.get\([\'"]Mcp-Session-Id[\'"]',
            r'session.*id'
        ]
        
        implemented = any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
        
        return {
            "implemented": implemented,
            "details": "Session header handling found" if implemented else "No session header handling detected"
        }
    
    def _check_sse_implementation(self, file_path: Path) -> Dict[str, Any]:
        """Check for SSE implementation"""
        content = file_path.read_text()
        
        sse_indicators = [
            r'sse_response',
            r'text/event-stream',
            r'Server-Sent Events',
            r'Last-Event-ID'
        ]
        
        implemented = any(re.search(indicator, content, re.IGNORECASE) for indicator in sse_indicators)
        
        return {
            "implemented": implemented,
            "details": "SSE implementation found" if implemented else "No SSE implementation detected"
        }
    
    def _check_cors_security(self, file_path: Path) -> Dict[str, Any]:
        """Check CORS security implementation"""
        content = file_path.read_text()
        
        security_patterns = [
            r'Access-Control-Allow-Origin',
            r'origin.*validation',
            r'allowed_origins'
        ]
        
        implemented = any(re.search(pattern, content, re.IGNORECASE) for pattern in security_patterns)
        
        return {
            "implemented": implemented,
            "details": "CORS security implementation found" if implemented else "No CORS security detected"
        }
    
    def _check_jsonrpc_format(self, file_path: Path) -> Dict[str, Any]:
        """Check JSON-RPC format compliance"""
        content = file_path.read_text()
        
        jsonrpc_patterns = [
            r'"jsonrpc":\s*"2\.0"',
            r'jsonrpc.*2\.0'
        ]
        
        implemented = any(re.search(pattern, content) for pattern in jsonrpc_patterns)
        
        return {
            "implemented": implemented,
            "details": "JSON-RPC 2.0 format found" if implemented else "No JSON-RPC 2.0 format detected"
        }
    
    def _check_protocol_version_declaration(self, content: str) -> Dict[str, Any]:
        """Check protocol version declaration"""
        version_pattern = r'protocol_version.*=.*"([^"]*)"'
        matches = re.findall(version_pattern, content)
        
        valid = any(version == "2025-06-18" for version in matches)
        
        return {
            "valid": valid,
            "details": f"Found versions: {matches}" if matches else "No protocol version found"
        }
    
    def _check_initialization_sequence(self, content: str) -> Dict[str, Any]:
        """Check initialization sequence implementation"""
        init_patterns = [
            r'def initialize',
            r'async def initialize',
            r'initialized.*notification'
        ]
        
        implemented = any(re.search(pattern, content, re.IGNORECASE) for pattern in init_patterns)
        
        return {
            "implemented": implemented,
            "details": "Initialization sequence found" if implemented else "No initialization sequence"
        }
    
    def _check_capability_declaration(self, content: str) -> Dict[str, Any]:
        """Check capability declaration"""
        capability_patterns = [
            r'capabilities',
            r'server.*capabilities',
            r'tools.*list'
        ]
        
        implemented = any(re.search(pattern, content, re.IGNORECASE) for pattern in capability_patterns)
        
        return {
            "implemented": implemented,
            "details": "Capability declaration found" if implemented else "No capability declaration"
        }
    
    def _check_message_structure(self, content: str) -> Dict[str, Any]:
        """Check message structure compliance"""
        structure_patterns = [
            r'"jsonrpc"',
            r'"method"',
            r'"params"',
            r'"id"'
        ]
        
        compliant = all(re.search(pattern, content) for pattern in structure_patterns)
        
        return {
            "compliant": compliant,
            "details": "Message structure compliant" if compliant else "Missing message structure elements"
        }
    
    def _check_error_handling_format(self, content: str) -> Dict[str, Any]:
        """Check error handling format"""
        error_patterns = [
            r'-32\d{3}',  # JSON-RPC error codes
            r'"error".*"code"',
            r'"error".*"message"'
        ]
        
        compliant = any(re.search(pattern, content) for pattern in error_patterns)
        
        return {
            "compliant": compliant,
            "details": "Error handling format found" if compliant else "No proper error handling format"
        }
    
    def _check_tool_schema_validation(self, content: str) -> Dict[str, Any]:
        """Check tool schema validation"""
        schema_patterns = [
            r'inputSchema',
            r'schema.*validation',
            r'properties.*type'
        ]
        
        implemented = any(re.search(pattern, content, re.IGNORECASE) for pattern in schema_patterns)
        
        return {
            "implemented": implemented,
            "details": "Schema validation found" if implemented else "No schema validation"
        }
    
    def _check_tool_registration_format(self, content: str) -> Dict[str, Any]:
        """Check tool registration format"""
        registration_patterns = [
            r'list_tools',
            r'tool.*registration',
            r'name.*description'
        ]
        
        compliant = any(re.search(pattern, content, re.IGNORECASE) for pattern in registration_patterns)
        
        return {
            "compliant": compliant,
            "details": "Tool registration format found" if compliant else "No tool registration format"
        }
    
    def _calculate_compliance_score(self, violations: List[Dict[str, Any]]) -> float:
        """Calculate compliance score based on violations"""
        if not violations:
            return 10.0
        
        # Weight violations by severity
        severity_weights = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}
        total_weight = sum(severity_weights.get(v.get("severity", "low"), 0.5) for v in violations)
        
        # Score decreases with violation weight
        score = max(0.0, 10.0 - total_weight)
        return score

if __name__ == "__main__":
    # Run integration tests when executed directly
    tester = ActualCodebaseIntegrationTester()
    
    print("MCP Codebase Integration Analysis")
    print("=" * 40)
    
    # Analyze codebase structure
    structure = tester.analyze_codebase_structure()
    print(f"Files analyzed: {structure['python_files']}")
    print(f"Total lines: {structure['total_lines']}")
    print(f"Coverage: {structure['analysis_coverage']:.1%}")
    
    if structure['missing_files']:
        print(f"Missing files: {structure['missing_files']}")
    
    # Run with pytest
    import sys
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)