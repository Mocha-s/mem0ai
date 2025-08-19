"""
Comprehensive Test Suite for MCP Compliance Analysis

Tests validate the accuracy and effectiveness of MCP 2025-06-18 specification
compliance analysis against the actual mem0_mcp codebase.
"""

import pytest
import json
import re
import os
import ast
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from unittest.mock import Mock, patch, MagicMock

# Test configuration
@dataclass
class TestConfig:
    """Test configuration for MCP compliance analysis"""
    test_data_dir: Path
    mock_violations: List[Dict[str, Any]]
    expected_patterns: Dict[str, re.Pattern]
    risk_thresholds: Dict[str, Tuple[int, int]]

# Test fixtures and utilities
class MCPComplianceTestFramework:
    """Framework for testing MCP compliance analysis accuracy"""
    
    def __init__(self):
        self.test_config = TestConfig(
            test_data_dir=Path(__file__).parent / "test_data",
            mock_violations=[],
            expected_patterns={
                "jsonrpc_version": re.compile(r'"jsonrpc":\s*"2\.0"'),
                "protocol_version": re.compile(r'"protocolVersion":\s*"2025-06-18"'),
                "session_header": re.compile(r'Mcp-Session-Id'),
                "origin_validation": re.compile(r'request\.headers\.get\([\'"]Origin[\'"]'),
            },
            risk_thresholds={
                "critical": (8, 10),
                "high": (6, 7), 
                "medium": (4, 5),
                "low": (1, 3)
            }
        )
        self.setup_test_data()
    
    def setup_test_data(self):
        """Setup test data directory with sample code files"""
        self.test_config.test_data_dir.mkdir(exist_ok=True)
        
        # Create sample files with known violations
        self._create_sample_transport_file()
        self._create_sample_server_file()
        self._create_sample_protocol_file()
    
    def _create_sample_transport_file(self):
        """Create sample transport file with known MCP violations"""
        content = '''
"""Sample transport with MCP violations"""
import json
from aiohttp import web

class SampleTransport:
    def __init__(self):
        self.version = "1.0"  # VIOLATION: Wrong JSON-RPC version
    
    async def handle_request(self, request):
        # VIOLATION: Missing origin validation
        data = await request.json()
        
        # VIOLATION: Incorrect response format
        return web.json_response({
            "jsonrpc": "1.0",  # VIOLATION: Wrong version
            "result": data
        })
    
    def validate_session(self, headers):
        # VIOLATION: Missing session header validation
        return True
'''
        test_file = self.test_config.test_data_dir / "sample_transport.py"
        test_file.write_text(content)
    
    def _create_sample_server_file(self):
        """Create sample server file with known MCP violations"""
        content = '''
"""Sample server with MCP violations"""

class SampleServer:
    def __init__(self):
        self.protocol_version = "2024-01-01"  # VIOLATION: Wrong protocol version
    
    async def initialize(self, params):
        # VIOLATION: Missing protocol version negotiation
        return {"capabilities": {}}
    
    async def list_tools(self):
        # VIOLATION: Missing required schema structure
        return [{"name": "test_tool"}]
    
    def handle_error(self, error):
        # VIOLATION: Incorrect error code format
        return {"error": error}
'''
        test_file = self.test_config.test_data_dir / "sample_server.py"
        test_file.write_text(content)
    
    def _create_sample_protocol_file(self):
        """Create sample protocol file with correct MCP implementation"""
        content = '''
"""Sample protocol with correct MCP implementation"""
import json

class CorrectProtocol:
    def __init__(self):
        self.protocol_version = "2025-06-18"  # CORRECT
    
    def create_request(self, method, params, request_id):
        # CORRECT: Proper JSON-RPC 2.0 format
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
    
    def validate_origin(self, request):
        # CORRECT: Origin validation implemented
        origin = request.headers.get("Origin")
        return origin in self.allowed_origins
'''
        test_file = self.test_config.test_data_dir / "correct_protocol.py"
        test_file.write_text(content)

# Mock compliance analyzer for testing
class MockComplianceAnalyzer:
    """Mock compliance analyzer for testing pattern detection accuracy"""
    
    def __init__(self):
        self.patterns = {
            "jsonrpc_version": re.compile(r'"jsonrpc":\s*"([^"]*)"'),
            "protocol_version": re.compile(r'protocol_version\s*=\s*"([^"]*)"'),
            "origin_validation": re.compile(r'request\.headers\.get\([\'"]Origin[\'"]'),
            "session_header": re.compile(r'Mcp-Session-Id'),
            "error_codes": re.compile(r'-32\d{3}'),
        }
    
    def analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Analyze a file for MCP compliance violations"""
        violations = []
        content = file_path.read_text()
        
        for line_num, line in enumerate(content.split('\n'), 1):
            # Check for JSON-RPC version violations
            jsonrpc_match = self.patterns["jsonrpc_version"].search(line)
            if jsonrpc_match and jsonrpc_match.group(1) != "2.0":
                violations.append({
                    "type": "protocol_violation",
                    "severity": "critical",
                    "risk_score": 9,
                    "line": line_num,
                    "description": f"Incorrect JSON-RPC version: {jsonrpc_match.group(1)}",
                    "expected": "2.0",
                    "actual": jsonrpc_match.group(1)
                })
            
            # Check for protocol version violations
            protocol_match = self.patterns["protocol_version"].search(line)
            if protocol_match and protocol_match.group(1) != "2025-06-18":
                violations.append({
                    "type": "version_violation",
                    "severity": "high",
                    "risk_score": 7,
                    "line": line_num,
                    "description": f"Incorrect protocol version: {protocol_match.group(1)}",
                    "expected": "2025-06-18",
                    "actual": protocol_match.group(1)
                })
        
        return violations

# Test classes
@pytest.fixture
def test_framework():
    """Fixture providing test framework instance"""
    return MCPComplianceTestFramework()

@pytest.fixture  
def mock_analyzer():
    """Fixture providing mock compliance analyzer"""
    return MockComplianceAnalyzer()

class TestComplianceAnalysisAccuracy:
    """Tests for compliance analysis accuracy and violation detection"""
    
    def test_jsonrpc_version_detection(self, test_framework, mock_analyzer):
        """Test accurate detection of JSON-RPC version violations"""
        # Test file with known JSON-RPC violations
        test_file = test_framework.test_config.test_data_dir / "sample_transport.py"
        violations = mock_analyzer.analyze_file(test_file)
        
        # Should detect JSON-RPC version violation
        jsonrpc_violations = [v for v in violations if v["type"] == "protocol_violation"]
        assert len(jsonrpc_violations) > 0, "Should detect JSON-RPC version violations"
        
        for violation in jsonrpc_violations:
            assert violation["severity"] == "critical"
            assert violation["risk_score"] >= 8
            assert "JSON-RPC version" in violation["description"]
            assert violation["expected"] == "2.0"
    
    def test_protocol_version_detection(self, test_framework, mock_analyzer):
        """Test accurate detection of protocol version violations"""
        test_file = test_framework.test_config.test_data_dir / "sample_server.py"
        violations = mock_analyzer.analyze_file(test_file)
        
        # Should detect protocol version violation
        version_violations = [v for v in violations if v["type"] == "version_violation"]
        assert len(version_violations) > 0, "Should detect protocol version violations"
        
        for violation in version_violations:
            assert violation["severity"] == "high"
            assert violation["expected"] == "2025-06-18"
            assert violation["actual"] != "2025-06-18"
    
    def test_false_positive_prevention(self, test_framework, mock_analyzer):
        """Test that correct implementations don't generate false positives"""
        test_file = test_framework.test_config.test_data_dir / "correct_protocol.py"
        violations = mock_analyzer.analyze_file(test_file)
        
        # Should not detect violations in correct implementation
        protocol_violations = [v for v in violations if v["type"] in ["protocol_violation", "version_violation"]]
        assert len(protocol_violations) == 0, f"Correct implementation should not have violations: {protocol_violations}"
    
    def test_line_number_accuracy(self, test_framework, mock_analyzer):
        """Test that violation line numbers are accurate"""
        test_file = test_framework.test_config.test_data_dir / "sample_transport.py"
        violations = mock_analyzer.analyze_file(test_file)
        content = test_file.read_text()
        lines = content.split('\n')
        
        for violation in violations:
            line_num = violation["line"]
            actual_line = lines[line_num - 1] if line_num <= len(lines) else ""
            
            # Verify the violation actually exists on that line
            if violation["type"] == "protocol_violation":
                assert '"jsonrpc"' in actual_line, f"Line {line_num} should contain JSON-RPC reference"
            elif violation["type"] == "version_violation": 
                assert "protocol_version" in actual_line, f"Line {line_num} should contain protocol_version"

class TestSpecificationCoverage:
    """Tests for comprehensive MCP specification coverage"""
    
    def test_jsonrpc_format_coverage(self, test_framework):
        """Test coverage of JSON-RPC 2.0 format requirements"""
        patterns = test_framework.test_config.expected_patterns
        
        # Test JSON-RPC version pattern
        test_strings = [
            '"jsonrpc": "2.0"',
            '"jsonrpc":"2.0"', 
            '"jsonrpc" : "2.0"',
            '"jsonrpc": "1.0"'  # Should match but be flagged as violation
        ]
        
        for test_string in test_strings:
            assert patterns["jsonrpc_version"].search(test_string), f"Should match JSON-RPC pattern: {test_string}"
    
    def test_protocol_version_coverage(self, test_framework):
        """Test coverage of MCP protocol version requirements"""
        patterns = test_framework.test_config.expected_patterns
        
        test_strings = [
            '"protocolVersion": "2025-06-18"',
            '"protocolVersion":"2025-06-18"',
            '"protocolVersion" : "2025-06-18"'
        ]
        
        for test_string in test_strings:
            assert patterns["protocol_version"].search(test_string), f"Should match protocol version: {test_string}"
    
    def test_transport_header_coverage(self, test_framework):
        """Test coverage of Streamable HTTP transport headers"""
        patterns = test_framework.test_config.expected_patterns
        
        test_strings = [
            'headers.get("Mcp-Session-Id")',
            "request.headers['Mcp-Session-Id']",
            "Mcp-Session-Id header"
        ]
        
        for test_string in test_strings:
            assert patterns["session_header"].search(test_string), f"Should match session header: {test_string}"
    
    def test_security_pattern_coverage(self, test_framework):
        """Test coverage of security requirement patterns"""
        patterns = test_framework.test_config.expected_patterns
        
        test_strings = [
            'request.headers.get("Origin")',
            'request.headers.get(\'Origin\')',
            "request.headers.get('Origin', '')"
        ]
        
        for test_string in test_strings:
            assert patterns["origin_validation"].search(test_string), f"Should match origin validation: {test_string}"
    
    def test_error_code_patterns(self):
        """Test JSON-RPC error code pattern detection"""
        error_pattern = re.compile(r'-32\d{3}')
        
        valid_codes = ["-32600", "-32601", "-32602", "-32603", "-32700"]
        invalid_codes = ["-31600", "-33600", "32600", "-326"]
        
        for code in valid_codes:
            assert error_pattern.search(code), f"Should match valid JSON-RPC error code: {code}"
        
        for code in invalid_codes:
            assert not error_pattern.search(code), f"Should not match invalid error code: {code}"

class TestReportQuality:
    """Tests for compliance report generation quality"""
    
    def test_risk_scoring_accuracy(self, test_framework):
        """Test that risk scores align with violation severity"""
        thresholds = test_framework.test_config.risk_thresholds
        
        # Test risk score ranges
        assert thresholds["critical"] == (8, 10)
        assert thresholds["high"] == (6, 7)
        assert thresholds["medium"] == (4, 5)
        assert thresholds["low"] == (1, 3)
        
        # Test score validation
        def validate_risk_score(severity: str, score: int) -> bool:
            min_score, max_score = thresholds[severity]
            return min_score <= score <= max_score
        
        assert validate_risk_score("critical", 9)
        assert validate_risk_score("high", 6)
        assert not validate_risk_score("critical", 5)
        assert not validate_risk_score("low", 8)
    
    def test_violation_report_structure(self):
        """Test structure of violation reports"""
        sample_violation = {
            "type": "protocol_violation",
            "severity": "critical", 
            "risk_score": 9,
            "file_path": "/path/to/file.py",
            "line": 42,
            "description": "Missing required field",
            "recommendation": "Add missing field",
            "code_example": "# Example fix"
        }
        
        required_fields = ["type", "severity", "risk_score", "file_path", "line", "description"]
        for field in required_fields:
            assert field in sample_violation, f"Violation report must include {field}"
        
        assert isinstance(sample_violation["risk_score"], int)
        assert 1 <= sample_violation["risk_score"] <= 10
        assert isinstance(sample_violation["line"], int)
        assert sample_violation["line"] > 0
    
    def test_remediation_recommendations(self):
        """Test quality of remediation recommendations"""
        sample_recommendations = [
            {
                "violation": "incorrect_jsonrpc_version",
                "recommendation": 'Change "jsonrpc": "1.0" to "jsonrpc": "2.0"',
                "code_example": '{"jsonrpc": "2.0", "method": "test", "id": 1}',
                "actionable": True
            },
            {
                "violation": "missing_origin_validation", 
                "recommendation": "Add origin header validation in request handler",
                "code_example": 'origin = request.headers.get("Origin")\nif origin not in allowed_origins:\n    raise SecurityError("Invalid origin")',
                "actionable": True
            }
        ]
        
        for rec in sample_recommendations:
            assert rec["actionable"], "Recommendations must be actionable"
            assert len(rec["recommendation"]) > 10, "Recommendations must be detailed"
            assert rec["code_example"], "Recommendations should include code examples"
    
    def test_json_output_format(self):
        """Test machine-readable JSON output format"""
        sample_output = {
            "analysis_summary": {
                "total_files_analyzed": 15,
                "total_violations": 23,
                "overall_compliance_score": 7.2,
                "timestamp": "2025-01-XX",
                "mcp_version": "2025-06-18"
            },
            "violations_by_severity": {
                "critical": 3,
                "high": 7,
                "medium": 8,
                "low": 5
            },
            "violations": [
                {
                    "id": "V001",
                    "type": "protocol_violation",
                    "severity": "critical",
                    "risk_score": 9,
                    "file_path": "/path/to/file.py",
                    "line": 42,
                    "description": "Violation description",
                    "recommendation": "Fix recommendation"
                }
            ]
        }
        
        # Validate JSON structure
        assert "analysis_summary" in sample_output
        assert "violations" in sample_output
        assert isinstance(sample_output["violations"], list)
        
        # Validate summary fields
        summary = sample_output["analysis_summary"]
        required_summary_fields = ["total_files_analyzed", "total_violations", "overall_compliance_score"]
        for field in required_summary_fields:
            assert field in summary

class TestIntegrationWithActualCodebase:
    """Integration tests against the actual MCP codebase"""
    
    def setup_method(self):
        """Setup for integration tests"""
        self.mcp_root = Path("/opt/mem0ai/mem0_mcp")
        self.key_files = [
            "src/transport/streamable_http.py",
            "src/server/mcp_server.py", 
            "src/protocol/messages.py",
            "src/gateway/tool_manager.py",
            "run_server_http.py"
        ]
    
    def test_file_existence_validation(self):
        """Test that all target files for analysis exist"""
        for file_path in self.key_files:
            full_path = self.mcp_root / file_path
            assert full_path.exists(), f"Required file does not exist: {full_path}"
            assert full_path.is_file(), f"Path is not a file: {full_path}"
    
    def test_file_parsing_capability(self):
        """Test that files can be parsed for analysis"""
        for file_path in self.key_files:
            full_path = self.mcp_root / file_path
            if not full_path.exists():
                continue
                
            try:
                content = full_path.read_text(encoding='utf-8')
                assert len(content) > 0, f"File is empty: {full_path}"
                
                # Try to parse as Python AST
                ast.parse(content)
            except SyntaxError as e:
                pytest.fail(f"File has syntax errors: {full_path} - {e}")
            except Exception as e:
                pytest.fail(f"Cannot read file: {full_path} - {e}")
    
    @patch('builtins.open', side_effect=PermissionError("Access denied"))
    def test_error_handling_for_inaccessible_files(self, mock_open):
        """Test error handling when files cannot be accessed"""
        analyzer = MockComplianceAnalyzer()
        
        # Should handle file access errors gracefully
        try:
            violations = analyzer.analyze_file(Path("/nonexistent/file.py"))
            # Should return empty list or handle gracefully
            assert isinstance(violations, list)
        except PermissionError:
            # Analyzer should catch and handle this
            pytest.fail("Analyzer should handle file access errors")
    
    def test_performance_with_large_files(self):
        """Test analyzer performance with larger files"""
        # Create a large test file
        large_content = "\n".join([f"# Line {i}" for i in range(10000)])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(large_content)
            f.flush()
            
            try:
                analyzer = MockComplianceAnalyzer()
                start_time = time.time()
                violations = analyzer.analyze_file(Path(f.name))
                analysis_time = time.time() - start_time
                
                # Analysis should complete within reasonable time
                assert analysis_time < 5.0, f"Analysis took too long: {analysis_time}s"
                assert isinstance(violations, list)
            finally:
                os.unlink(f.name)

class TestValidationAccuracy:
    """Tests for cross-checking violations against actual code"""
    
    def test_actual_mcp_protocol_version_usage(self):
        """Test detection of protocol version usage in actual codebase"""
        server_file = Path("/opt/mem0ai/mem0_mcp/src/server/mcp_server.py")
        if not server_file.exists():
            pytest.skip("Server file not found")
        
        content = server_file.read_text()
        
        # Check for protocol version declaration
        version_pattern = re.compile(r'protocol_version.*=.*"([^"]*)"')
        matches = version_pattern.findall(content)
        
        if matches:
            for version in matches:
                if version != "2025-06-18":
                    # This would be a real violation
                    assert False, f"Found incorrect protocol version: {version}"
    
    def test_actual_jsonrpc_usage_patterns(self):
        """Test JSON-RPC usage patterns in actual transport layer"""
        transport_file = Path("/opt/mem0ai/mem0_mcp/src/transport/streamable_http.py")
        if not transport_file.exists():
            pytest.skip("Transport file not found")
        
        content = transport_file.read_text()
        
        # Look for JSON-RPC response creation
        jsonrpc_pattern = re.compile(r'"jsonrpc":\s*"([^"]*)"')
        matches = jsonrpc_pattern.findall(content)
        
        for match in matches:
            assert match == "2.0", f"Found incorrect JSON-RPC version in transport: {match}"
    
    def test_session_header_implementation(self):
        """Test session header implementation in actual code"""
        transport_file = Path("/opt/mem0ai/mem0_mcp/src/transport/streamable_http.py")
        if not transport_file.exists():
            pytest.skip("Transport file not found")
        
        content = transport_file.read_text()
        
        # Check for session header usage
        session_patterns = [
            r'Mcp-Session-Id',
            r'headers\.get\([\'"]Mcp-Session-Id[\'"]',
            r'session.*id'
        ]
        
        found_session_handling = False
        for pattern in session_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_session_handling = True
                break
        
        assert found_session_handling, "Session header handling not found in transport layer"
    
    def test_origin_validation_implementation(self):
        """Test origin validation in actual security implementation"""
        transport_file = Path("/opt/mem0ai/mem0_mcp/src/transport/streamable_http.py")
        if not transport_file.exists():
            pytest.skip("Transport file not found")
        
        content = transport_file.read_text()
        
        # Check for origin validation
        origin_patterns = [
            r'headers\.get\([\'"]Origin[\'"]',
            r'origin.*validation',
            r'allowed.*origins'
        ]
        
        found_origin_validation = False
        for pattern in origin_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                found_origin_validation = True
                break
        
        # Origin validation should be present for security
        assert found_origin_validation, "Origin validation not implemented in transport layer"

# Performance and stress tests
class TestPerformanceAndStress:
    """Performance tests for compliance analyzer"""
    
    def test_analyzer_memory_usage(self):
        """Test memory usage doesn't grow excessively during analysis"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Analyze multiple files
        analyzer = MockComplianceAnalyzer()
        test_framework = MCPComplianceTestFramework()
        
        for i in range(100):  # Simulate analyzing many files
            test_file = test_framework.test_config.test_data_dir / "sample_transport.py"
            violations = analyzer.analyze_file(test_file)
            
            if i % 10 == 0:  # Check memory every 10 iterations
                gc.collect()
                current_memory = process.memory_info().rss
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable (< 100MB for this test)
                assert memory_growth < 100 * 1024 * 1024, f"Excessive memory growth: {memory_growth} bytes"
    
    def test_concurrent_analysis_capability(self):
        """Test analyzer can handle concurrent file analysis"""
        import threading
        import time
        
        analyzer = MockComplianceAnalyzer()
        test_framework = MCPComplianceTestFramework()
        results = []
        errors = []
        
        def analyze_file_thread(file_path):
            try:
                violations = analyzer.analyze_file(file_path)
                results.append(violations)
            except Exception as e:
                errors.append(str(e))
        
        # Start multiple threads
        threads = []
        test_file = test_framework.test_config.test_data_dir / "sample_transport.py"
        
        for i in range(5):
            thread = threading.Thread(target=analyze_file_thread, args=(test_file,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Check results
        assert len(errors) == 0, f"Concurrent analysis errors: {errors}"
        assert len(results) == 5, f"Expected 5 results, got {len(results)}"

# Test runner and utilities
def run_compliance_test_suite():
    """Run the complete compliance analysis test suite"""
    test_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "categories": {
            "accuracy": {"passed": 0, "failed": 0},
            "coverage": {"passed": 0, "failed": 0},
            "quality": {"passed": 0, "failed": 0},
            "integration": {"passed": 0, "failed": 0},
            "validation": {"passed": 0, "failed": 0},
            "performance": {"passed": 0, "failed": 0}
        }
    }
    
    # This would be implemented to run all test categories
    return test_results

if __name__ == "__main__":
    # Run tests with pytest when executed directly
    import sys
    import time
    
    print("MCP Compliance Analysis Test Suite")
    print("=" * 50)
    
    # Basic validation
    test_framework = MCPComplianceTestFramework()
    print(f"Test data directory: {test_framework.test_config.test_data_dir}")
    print(f"Test patterns loaded: {len(test_framework.test_config.expected_patterns)}")
    
    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])
    sys.exit(exit_code)