# MCP Compliance Analysis Test Suite

This comprehensive test suite validates the accuracy and effectiveness of MCP (Model Context Protocol) 2025-06-18 specification compliance analysis for the `/opt/mem0ai/mem0_mcp` codebase.

## Overview

The test suite ensures that the MCP compliance analyzer:
- Accurately identifies real MCP specification violations  
- Provides actionable remediation recommendations
- Generates high-quality compliance reports
- Performs efficiently with large codebases
- Maintains accuracy across different code patterns

## Test Structure

### Core Test Files

1. **`test_mcp_compliance_analysis.py`** - Core compliance analysis functionality tests
   - Pattern matching accuracy
   - False positive/negative detection
   - Line number accuracy validation
   - Specification coverage verification

2. **`test_data_generator.py`** - Test data generation and validation framework
   - Creates realistic code samples with known violations
   - Provides validation framework for analyzer results
   - Generates comprehensive violation scenarios

3. **`test_integration_actual_codebase.py`** - Integration tests against actual MCP codebase
   - Tests analyzer against real `/opt/mem0ai/mem0_mcp` code
   - Validates file scanning and parsing capabilities
   - Performance testing with actual codebase

4. **`test_compliance_report_validation.py`** - Report generation quality tests
   - Validates report structure and content
   - Tests risk scoring accuracy
   - Verifies remediation recommendation quality

5. **`run_compliance_tests.py`** - Test orchestration and reporting
   - Coordinates execution of all test suites
   - Generates comprehensive test reports
   - Provides environment validation

## Test Categories

### 1. Compliance Analysis Accuracy Tests

**Purpose**: Verify the analyzer correctly identifies MCP specification violations

**Coverage**:
- JSON-RPC 2.0 format violations
- MCP protocol version mismatches  
- Transport layer implementation gaps
- Security requirement violations
- Tool implementation compliance issues

**Example Test**:
```python
def test_jsonrpc_version_detection(self):
    # Test file with known JSON-RPC violations
    violations = analyzer.analyze_file(test_file)
    jsonrpc_violations = [v for v in violations if v["type"] == "protocol_violation"]
    assert len(jsonrpc_violations) > 0
    assert all(v["severity"] == "critical" for v in jsonrpc_violations)
```

### 2. Specification Coverage Tests

**Purpose**: Ensure comprehensive coverage of MCP 2025-06-18 specification

**Coverage**:
- JSON-RPC 2.0 message format requirements
- Streamable HTTP transport specifications
- Security and origin validation requirements
- Server tools implementation standards
- Message flow and lifecycle validation

### 3. Report Quality Tests

**Purpose**: Validate quality and accuracy of compliance reports

**Coverage**:
- Report structure validation
- Risk scoring system accuracy (1-10 scale)
- Remediation recommendation actionability
- Machine-readable JSON output format
- Line number accuracy in violation reports

### 4. Integration Tests

**Purpose**: Test analyzer against actual MCP codebase

**Coverage**:
- File discovery and parsing
- Performance with large codebases
- Error handling for malformed code
- Real-world violation detection

### 5. Validation Tests

**Purpose**: Cross-check analyzer results against actual code

**Coverage**:
- Violation accuracy validation
- False positive/negative rates
- Remediation effectiveness
- Compliance scoring accuracy

## Installation and Setup

### Prerequisites

- Python 3.8+ 
- Access to `/opt/mem0ai/mem0_mcp` codebase
- pytest and testing dependencies

### Install Dependencies

```bash
cd /opt/mem0ai/mem0_mcp/tests
pip install -r test_requirements.txt
```

### Validate Environment

```bash
python run_compliance_tests.py --validate-env
```

## Running Tests

### Run All Tests

```bash
# Run complete test suite
python run_compliance_tests.py --verbose

# Run without generating report file
python run_compliance_tests.py --no-report
```

### Run Specific Test Suite

```bash
# Run core compliance analysis tests
python run_compliance_tests.py --suite "Core Compliance Analysis"

# Run integration tests only
python run_compliance_tests.py --suite "Actual Codebase Integration"

# Run with pytest directly
pytest test_mcp_compliance_analysis.py -v
```

### Run Individual Test Files

```bash
# Core compliance tests
pytest test_mcp_compliance_analysis.py -v --tb=short

# Data generation tests  
pytest test_data_generator.py -v

# Integration tests
pytest test_integration_actual_codebase.py -v

# Report validation tests
pytest test_compliance_report_validation.py -v
```

## Test Configuration

### Environment Variables

```bash
# Optional: Override MCP codebase path
export MCP_CODEBASE_PATH="/custom/path/to/mem0_mcp"

# Optional: Test data directory
export MCP_TEST_DATA_DIR="/tmp/mcp_test_data"
```

### Test Data Generation

Generate test data with known violations:

```python
from test_data_generator import MCPViolationTestDataGenerator

generator = MCPViolationTestDataGenerator()
test_data_dir = Path("/tmp/mcp_test_violations")
manifest = generator.generate_test_files(test_data_dir)
```

## Expected Test Results

### Success Criteria

- **Overall Success Rate**: ≥ 80%
- **Critical Test Failures**: 0
- **False Positive Rate**: < 20%
- **False Negative Rate**: < 10%
- **Line Number Accuracy**: ≥ 90%
- **Performance**: < 5 seconds per 1000 lines of code

### Test Report Structure

```json
{
  "overall_success": true,
  "total_execution_time": 45.2,
  "suite_results": [
    {
      "suite_name": "Core Compliance Analysis",
      "total_tests": 25,
      "passed_tests": 24,
      "failed_tests": 1,
      "execution_time": 12.3
    }
  ],
  "summary_stats": {
    "success_rate": 92.5,
    "critical_failures": 0
  },
  "recommendations": [
    "Address remaining protocol version detection edge case"
  ]
}
```

## Test Development Guidelines

### Adding New Tests

1. **Follow Test Structure**: Use the established test class patterns
2. **Include Documentation**: Document test purpose and expected outcomes
3. **Use Meaningful Names**: Test names should describe scenario and expectation
4. **Mock External Dependencies**: Use mocks for file system, network, etc.
5. **Validate Results**: Assert both positive and negative test cases

### Test Naming Convention

```python
def test_{feature}_{scenario}_{expected_outcome}():
    """Test {feature} when {scenario} to verify {expected_outcome}"""
```

Example:
```python
def test_jsonrpc_version_detection_with_invalid_version_reports_critical_violation():
    """Test JSON-RPC version detection when version is invalid to verify critical violation is reported"""
```

### Mock Implementation Guidelines

```python
class MockComplianceAnalyzer:
    def analyze_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Mock analyzer that returns predictable violations for testing"""
        # Implementation that simulates real analyzer behavior
        pass
```

## Performance Benchmarks

### Target Performance Metrics

| Codebase Size | Analysis Time | Memory Usage |
|---------------|---------------|---------------|
| 1,000 lines   | < 1 second    | < 50 MB      |
| 10,000 lines  | < 5 seconds   | < 100 MB     |
| 100,000 lines | < 30 seconds  | < 500 MB     |

### Performance Tests

```python
def test_analyzer_performance_with_large_codebase():
    start_time = time.time()
    violations = analyzer.analyze_codebase(large_codebase_path)
    analysis_time = time.time() - start_time
    
    assert analysis_time < performance_threshold
    assert len(violations) > 0  # Should find some violations
```

## Troubleshooting

### Common Issues

1. **Test Environment Issues**
   - Ensure `/opt/mem0ai/mem0_mcp` is accessible
   - Verify all dependencies are installed
   - Check Python version compatibility

2. **Permission Errors**
   - Ensure read access to MCP codebase
   - Verify write access to test data directory
   - Check temporary file permissions

3. **Import Errors**
   - Verify test files are in correct directory
   - Check PYTHONPATH includes test directory
   - Ensure all required modules are installed

### Debug Mode

```bash
# Run with maximum verbosity
pytest test_mcp_compliance_analysis.py -vv --tb=long

# Run single test with debugging
pytest test_mcp_compliance_analysis.py::TestComplianceAnalysisAccuracy::test_jsonrpc_version_detection -vv -s
```

## Contributing

### Test Contribution Guidelines

1. **Add Tests for New Features**: All new compliance rules need corresponding tests
2. **Update Test Data**: Add new violation scenarios to test data generator
3. **Maintain Performance**: Ensure new tests don't significantly slow down suite
4. **Document Changes**: Update README and test documentation

### Code Review Checklist

- [ ] Tests cover both positive and negative cases
- [ ] Test names are descriptive and follow convention
- [ ] Mock objects are used appropriately
- [ ] Performance impact is minimal
- [ ] Documentation is updated

## Test Results and Reporting

Test execution generates comprehensive reports:

- **Console Output**: Real-time test progress and results
- **JSON Report**: Machine-readable test results (`compliance_test_report.json`)
- **Coverage Report**: Code coverage analysis (if enabled)
- **Performance Metrics**: Execution time and resource usage

## Maintenance

### Regular Maintenance Tasks

1. **Update Test Data**: Refresh test violation scenarios
2. **Performance Monitoring**: Track test execution times
3. **Dependency Updates**: Keep testing dependencies current
4. **Coverage Analysis**: Monitor test coverage and identify gaps

### Automated Testing

Integrate with CI/CD pipelines:

```yaml
# Example CI configuration
test_compliance:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: pip install -r tests/test_requirements.txt
    - name: Run compliance tests
      run: python tests/run_compliance_tests.py --verbose
```

This comprehensive test suite ensures the MCP compliance analysis implementation accurately identifies real compliance issues and provides actionable guidance for maintaining MCP 2025-06-18 specification compliance.