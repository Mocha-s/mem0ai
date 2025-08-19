"""
MCP Compliance Analysis Test Runner

Orchestrates and executes the complete test suite for MCP compliance analysis,
providing comprehensive validation of analyzer accuracy and effectiveness.
"""

import pytest
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess
import importlib.util

@dataclass
class TestSuiteResult:
    """Result of running a test suite"""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    execution_time: float
    test_details: List[Dict[str, Any]]
    coverage_info: Optional[Dict[str, Any]] = None

@dataclass
class ComplianceTestReport:
    """Comprehensive test report for compliance analysis"""
    overall_success: bool
    total_execution_time: float
    suite_results: List[TestSuiteResult]
    summary_stats: Dict[str, Any]
    recommendations: List[str]
    timestamp: str

class ComplianceAnalysisTestRunner:
    """Orchestrates comprehensive testing of MCP compliance analysis"""
    
    def __init__(self):
        self.test_directory = Path(__file__).parent
        self.test_suites = [
            {
                "name": "Core Compliance Analysis",
                "module": "test_mcp_compliance_analysis",
                "description": "Tests core compliance analysis functionality",
                "priority": "critical"
            },
            {
                "name": "Violation Test Data Generation",
                "module": "test_data_generator",
                "description": "Tests test data generation and validation framework",
                "priority": "high"
            },
            {
                "name": "Actual Codebase Integration",
                "module": "test_integration_actual_codebase", 
                "description": "Integration tests against actual MCP codebase",
                "priority": "critical"
            },
            {
                "name": "Report Generation Validation",
                "module": "test_compliance_report_validation",
                "description": "Tests compliance report generation and validation",
                "priority": "high"
            }
        ]
        self.results = []
        
    def run_all_tests(self, verbose: bool = True, generate_report: bool = True) -> ComplianceTestReport:
        """Run all test suites and generate comprehensive report"""
        print("Starting MCP Compliance Analysis Test Suite")
        print("=" * 60)
        
        overall_start_time = time.time()
        overall_success = True
        
        for suite_config in self.test_suites:
            suite_result = self._run_test_suite(suite_config, verbose)
            self.results.append(suite_result)
            
            if suite_result.failed_tests > 0:
                overall_success = False
        
        overall_execution_time = time.time() - overall_start_time
        
        # Generate comprehensive report
        test_report = ComplianceTestReport(
            overall_success=overall_success,
            total_execution_time=overall_execution_time,
            suite_results=self.results,
            summary_stats=self._calculate_summary_stats(),
            recommendations=self._generate_recommendations(),
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )
        
        if generate_report:
            self._save_test_report(test_report)
        
        self._print_summary(test_report, verbose)
        
        return test_report
    
    def run_specific_suite(self, suite_name: str, verbose: bool = True) -> Optional[TestSuiteResult]:
        """Run a specific test suite"""
        suite_config = None
        for config in self.test_suites:
            if config["name"] == suite_name or config["module"] == suite_name:
                suite_config = config
                break
        
        if not suite_config:
            print(f"Test suite '{suite_name}' not found")
            available_suites = [config["name"] for config in self.test_suites]
            print(f"Available suites: {', '.join(available_suites)}")
            return None
        
        return self._run_test_suite(suite_config, verbose)
    
    def validate_test_environment(self) -> Dict[str, Any]:
        """Validate test environment setup"""
        validation_result = {
            "environment_ready": True,
            "missing_dependencies": [],
            "file_access_issues": [],
            "python_version": sys.version,
            "pytest_available": False,
            "test_files_present": [],
            "mcp_codebase_accessible": False
        }
        
        # Check pytest availability
        try:
            import pytest
            validation_result["pytest_available"] = True
        except ImportError:
            validation_result["missing_dependencies"].append("pytest")
            validation_result["environment_ready"] = False
        
        # Check required test files
        required_test_files = [
            "test_mcp_compliance_analysis.py",
            "test_data_generator.py", 
            "test_integration_actual_codebase.py",
            "test_compliance_report_validation.py"
        ]
        
        for test_file in required_test_files:
            test_path = self.test_directory / test_file
            if test_path.exists():
                validation_result["test_files_present"].append(test_file)
            else:
                validation_result["file_access_issues"].append(f"Missing test file: {test_file}")
                validation_result["environment_ready"] = False
        
        # Check MCP codebase accessibility
        mcp_root = Path("/opt/mem0ai/mem0_mcp")
        if mcp_root.exists() and (mcp_root / "src").exists():
            validation_result["mcp_codebase_accessible"] = True
        else:
            validation_result["file_access_issues"].append("MCP codebase not accessible at /opt/mem0ai/mem0_mcp")
            validation_result["environment_ready"] = False
        
        # Check other dependencies
        required_modules = ["json", "re", "ast", "pathlib", "time"]
        for module_name in required_modules:
            try:
                importlib.import_module(module_name)
            except ImportError:
                validation_result["missing_dependencies"].append(module_name)
                validation_result["environment_ready"] = False
        
        return validation_result
    
    def _run_test_suite(self, suite_config: Dict[str, Any], verbose: bool) -> TestSuiteResult:
        """Run an individual test suite"""
        suite_name = suite_config["name"]
        module_name = suite_config["module"]
        
        print(f"\nRunning: {suite_name}")
        print("-" * 40)
        
        start_time = time.time()
        
        # Determine test file path
        test_file = self.test_directory / f"{module_name}.py"
        
        if not test_file.exists():
            print(f"❌ Test file not found: {test_file}")
            return TestSuiteResult(
                suite_name=suite_name,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                skipped_tests=0,
                execution_time=0.0,
                test_details=[{"error": f"Test file not found: {test_file}"}]
            )
        
        # Run pytest on the specific file
        pytest_args = [
            str(test_file),
            "-v" if verbose else "-q",
            "--tb=short",
            "--json-report",
            f"--json-report-file=/tmp/pytest_report_{module_name}.json"
        ]
        
        try:
            # Run pytest as subprocess to capture results
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + pytest_args,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per suite
            )
            
            execution_time = time.time() - start_time
            
            # Parse pytest results
            suite_result = self._parse_pytest_results(
                suite_name, result, execution_time, f"/tmp/pytest_report_{module_name}.json"
            )
            
            if verbose:
                print(f"✓ {suite_result.passed_tests} passed, ❌ {suite_result.failed_tests} failed, ⏭️  {suite_result.skipped_tests} skipped")
                if result.returncode != 0 and result.stderr:
                    print(f"Errors: {result.stderr[:500]}")
            
            return suite_result
            
        except subprocess.TimeoutExpired:
            print(f"❌ Test suite timed out after 5 minutes")
            return TestSuiteResult(
                suite_name=suite_name,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                skipped_tests=0,
                execution_time=300.0,
                test_details=[{"error": "Test suite timed out"}]
            )
        
        except Exception as e:
            print(f"❌ Error running test suite: {e}")
            return TestSuiteResult(
                suite_name=suite_name,
                total_tests=0,
                passed_tests=0,
                failed_tests=1,
                skipped_tests=0,
                execution_time=time.time() - start_time,
                test_details=[{"error": str(e)}]
            )
    
    def _parse_pytest_results(self, suite_name: str, result: subprocess.CompletedProcess, 
                             execution_time: float, json_file: str) -> TestSuiteResult:
        """Parse pytest results from JSON report and stdout"""
        test_details = []
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        # Try to parse JSON report if available
        json_path = Path(json_file)
        if json_path.exists():
            try:
                with open(json_path, 'r') as f:
                    pytest_json = json.load(f)
                
                total_tests = pytest_json.get("summary", {}).get("total", 0)
                passed_tests = pytest_json.get("summary", {}).get("passed", 0)
                failed_tests = pytest_json.get("summary", {}).get("failed", 0)
                skipped_tests = pytest_json.get("summary", {}).get("skipped", 0)
                
                # Extract test details
                for test in pytest_json.get("tests", []):
                    test_details.append({
                        "name": test.get("nodeid", ""),
                        "outcome": test.get("outcome", ""),
                        "duration": test.get("duration", 0),
                        "keywords": test.get("keywords", [])
                    })
                
            except (json.JSONDecodeError, FileNotFoundError):
                # Fall back to parsing stdout
                pass
        
        # Fallback: parse stdout for basic statistics
        if total_tests == 0:
            stdout = result.stdout
            
            # Look for pytest summary line
            import re
            summary_match = re.search(r'(\d+) passed.*?(\d+) failed.*?(\d+) skipped', stdout)
            if summary_match:
                passed_tests = int(summary_match.group(1))
                failed_tests = int(summary_match.group(2))
                skipped_tests = int(summary_match.group(3))
                total_tests = passed_tests + failed_tests + skipped_tests
            else:
                # Look for individual patterns
                passed_match = re.search(r'(\d+) passed', stdout)
                failed_match = re.search(r'(\d+) failed', stdout)
                skipped_match = re.search(r'(\d+) skipped', stdout)
                
                passed_tests = int(passed_match.group(1)) if passed_match else 0
                failed_tests = int(failed_match.group(1)) if failed_match else 0
                skipped_tests = int(skipped_match.group(1)) if skipped_match else 0
                total_tests = passed_tests + failed_tests + skipped_tests
            
            # If we still don't have totals and there's output, assume some tests ran
            if total_tests == 0 and result.returncode is not None:
                if result.returncode == 0:
                    total_tests = 1
                    passed_tests = 1
                else:
                    total_tests = 1
                    failed_tests = 1
        
        return TestSuiteResult(
            suite_name=suite_name,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            execution_time=execution_time,
            test_details=test_details
        )
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """Calculate summary statistics across all test suites"""
        total_tests = sum(result.total_tests for result in self.results)
        total_passed = sum(result.passed_tests for result in self.results)
        total_failed = sum(result.failed_tests for result in self.results)
        total_skipped = sum(result.skipped_tests for result in self.results)
        total_time = sum(result.execution_time for result in self.results)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "total_test_suites": len(self.results),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "success_rate": success_rate,
            "total_execution_time": total_time,
            "average_suite_time": total_time / len(self.results) if self.results else 0,
            "critical_failures": len([r for r in self.results if r.failed_tests > 0 and any(s["priority"] == "critical" for s in self.test_suites if s["name"] == r.suite_name)])
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Check for critical test failures
        critical_failures = [r for r in self.results if r.failed_tests > 0]
        if critical_failures:
            recommendations.append("Address critical test failures before deploying compliance analysis")
        
        # Check success rate
        summary = self._calculate_summary_stats()
        if summary["success_rate"] < 80:
            recommendations.append(f"Test success rate ({summary['success_rate']:.1f}%) is below recommended 80% threshold")
        
        # Check performance
        slow_suites = [r for r in self.results if r.execution_time > 30]
        if slow_suites:
            recommendations.append("Optimize slow-running test suites for better development productivity")
        
        # Check skipped tests
        high_skip_rate = summary["total_skipped"] / summary["total_tests"] > 0.2 if summary["total_tests"] > 0 else False
        if high_skip_rate:
            recommendations.append("High skip rate indicates potential environment or dependency issues")
        
        return recommendations
    
    def _save_test_report(self, test_report: ComplianceTestReport):
        """Save comprehensive test report to file"""
        report_file = self.test_directory / "compliance_test_report.json"
        
        try:
            with open(report_file, 'w') as f:
                json.dump(asdict(test_report), f, indent=2, default=str)
            
            print(f"\n📄 Test report saved to: {report_file}")
            
        except Exception as e:
            print(f"❌ Failed to save test report: {e}")
    
    def _print_summary(self, test_report: ComplianceTestReport, verbose: bool):
        """Print test summary to console"""
        print(f"\n{'='*60}")
        print("MCP COMPLIANCE ANALYSIS TEST SUMMARY")
        print(f"{'='*60}")
        
        summary = test_report.summary_stats
        
        print(f"Overall Result: {'✅ SUCCESS' if test_report.overall_success else '❌ FAILURE'}")
        print(f"Total Execution Time: {test_report.total_execution_time:.2f}s")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print()
        
        print("Test Suite Results:")
        print("-" * 40)
        for result in test_report.suite_results:
            status = "✅" if result.failed_tests == 0 else "❌"
            print(f"{status} {result.suite_name}")
            print(f"    Tests: {result.total_tests} total, {result.passed_tests} passed, {result.failed_tests} failed, {result.skipped_tests} skipped")
            print(f"    Time: {result.execution_time:.2f}s")
            if verbose and result.failed_tests > 0:
                print("    Failed tests:")
                for detail in result.test_details:
                    if detail.get("outcome") == "failed":
                        print(f"      - {detail.get('name', 'Unknown test')}")
            print()
        
        if test_report.recommendations:
            print("Recommendations:")
            print("-" * 20)
            for i, rec in enumerate(test_report.recommendations, 1):
                print(f"{i}. {rec}")
            print()

def main():
    """Main entry point for test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Compliance Analysis Test Runner")
    parser.add_argument("--suite", help="Run specific test suite", type=str)
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--validate-env", action="store_true", help="Validate test environment only")
    parser.add_argument("--no-report", action="store_true", help="Don't generate test report file")
    
    args = parser.parse_args()
    
    runner = ComplianceAnalysisTestRunner()
    
    if args.validate_env:
        print("Validating Test Environment")
        print("=" * 30)
        validation = runner.validate_test_environment()
        
        if validation["environment_ready"]:
            print("✅ Test environment is ready")
        else:
            print("❌ Test environment has issues:")
            for issue in validation["missing_dependencies"] + validation["file_access_issues"]:
                print(f"  - {issue}")
        
        return 0 if validation["environment_ready"] else 1
    
    if args.suite:
        result = runner.run_specific_suite(args.suite, args.verbose)
        return 0 if result and result.failed_tests == 0 else 1
    else:
        test_report = runner.run_all_tests(args.verbose, not args.no_report)
        return 0 if test_report.overall_success else 1

if __name__ == "__main__":
    sys.exit(main())