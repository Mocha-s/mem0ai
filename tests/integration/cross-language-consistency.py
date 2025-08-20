"""
Cross-Language API Consistency Tests

This module tests the consistency between Python and TypeScript clients
for the custom instructions functionality, ensuring that:
- Same operations produce same results
- Error handling is consistent
- API response formats match
- Parameter validation logic is identical
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mem0.client.validation import validate_custom_instructions
from mem0.configs.base import MemoryConfig


class CrossLanguageConsistencyTests:
    """Test suite for cross-language API consistency."""

    def __init__(self):
        self.typescript_runner_path = project_root / "tests" / "integration" / "typescript-runner.js"

    def run_typescript_test(self, test_name: str, test_data: dict = None) -> dict:
        """Run a TypeScript test and return the result."""
        try:
            cmd = ["node", str(self.typescript_runner_path), test_name]
            if test_data:
                cmd.append(json.dumps(test_data))
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(project_root / "mem0-ts"),
                timeout=30
            )
            
            if result.returncode != 0:
                raise Exception(f"TypeScript test failed: {result.stderr}")
            
            return json.loads(result.stdout)
        except Exception as e:
            return {"error": str(e)}

    def test_validation_consistency(self):
        """Test that validation logic is consistent between Python and TypeScript."""
        test_cases = [
            {"input": "Valid instruction", "should_pass": True},
            {"input": "", "should_pass": False, "error_contains": "empty"},
            {"input": "   ", "should_pass": False, "error_contains": "empty"},
            {"input": 123, "should_pass": False, "error_contains": "string"},
            {"input": "x" * 10001, "should_pass": False, "error_contains": "too long"},
            {"input": "x" * 10000, "should_pass": True},
        ]

        for i, case in enumerate(test_cases):
            input_display = str(case['input'])[:50] if isinstance(case['input'], str) else str(case['input'])
            print(f"Testing validation case {i + 1}: {input_display}...")

            # Test Python validation
            python_result = self._test_python_validation(case["input"])

            # Test TypeScript validation
            ts_result = self.run_typescript_test("validate_custom_instructions", {
                "input": case["input"]
            })
            
            # Compare results
            if case["should_pass"]:
                assert python_result["success"], f"Python validation should pass for case {i + 1}"
                assert ts_result["success"], f"TypeScript validation should pass for case {i + 1}"
            else:
                assert not python_result["success"], f"Python validation should fail for case {i + 1}"
                assert not ts_result["success"], f"TypeScript validation should fail for case {i + 1}"
                
                # Check error messages contain expected text
                if "error_contains" in case:
                    assert case["error_contains"].lower() in python_result["error"].lower()
                    assert case["error_contains"].lower() in ts_result["error"].lower()

    def _test_python_validation(self, input_value):
        """Test Python validation and return result."""
        try:
            validate_custom_instructions(input_value)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_config_property_consistency(self):
        """Test that MemoryConfig property mapping is consistent."""
        test_cases = [
            {"custom_instructions": "Test prompt"},
            {"custom_instructions": None},
        ]

        for case in test_cases:
            print(f"Testing config property case: {case}")
            
            # Test Python config
            python_result = self._test_python_config_property(case["custom_instructions"])
            
            # Test TypeScript config (simulated)
            ts_result = self.run_typescript_test("test_config_property", case)
            
            # Compare results
            assert python_result["custom_instructions"] == ts_result["custom_instructions"]
            assert python_result["custom_fact_extraction_prompt"] == ts_result["custom_fact_extraction_prompt"]

    def _test_python_config_property(self, custom_instructions):
        """Test Python config property mapping."""
        config = MemoryConfig()
        config.custom_instructions = custom_instructions
        
        return {
            "custom_instructions": config.custom_instructions,
            "custom_fact_extraction_prompt": config.custom_fact_extraction_prompt
        }

    def test_api_response_format_consistency(self):
        """Test that API response formats are consistent."""
        # Mock API responses for testing
        mock_responses = {
            "get_project": {
                "custom_instructions": "Test instructions",
                "custom_categories": []
            },
            "update_project": {
                "message": "Updated custom instructions"
            }
        }

        for api_method, expected_response in mock_responses.items():
            print(f"Testing API response format for {api_method}")
            
            # Test Python response format (mocked)
            python_result = self._test_python_api_response(api_method, expected_response)
            
            # Test TypeScript response format (mocked)
            ts_result = self.run_typescript_test("test_api_response_format", {
                "method": api_method,
                "response": expected_response
            })
            
            # Compare response structures
            assert python_result.keys() == ts_result.keys()
            for key in python_result.keys():
                assert python_result[key] == ts_result[key]

    def _test_python_api_response(self, method, response):
        """Test Python API response format."""
        # This simulates the response format that would be returned
        return response

    def test_error_handling_consistency(self):
        """Test that error handling is consistent between languages."""
        error_scenarios = [
            {
                "scenario": "validation_error",
                "input": "",
                "expected_error_type": "ValueError"
            },
            {
                "scenario": "type_error", 
                "input": 123,
                "expected_error_type": "ValueError"
            }
        ]

        for scenario in error_scenarios:
            print(f"Testing error scenario: {scenario['scenario']}")
            
            # Test Python error handling
            python_error = self._test_python_error_handling(scenario)
            
            # Test TypeScript error handling
            ts_error = self.run_typescript_test("test_error_handling", scenario)
            
            # Compare error handling
            assert python_error["has_error"] == ts_error["has_error"]
            if python_error["has_error"]:
                # Both should have errors with similar characteristics
                assert "error_message" in python_error
                assert "error_message" in ts_error

    def _test_python_error_handling(self, scenario):
        """Test Python error handling."""
        try:
            validate_custom_instructions(scenario["input"])
            return {"has_error": False}
        except Exception as e:
            return {
                "has_error": True,
                "error_message": str(e),
                "error_type": type(e).__name__
            }

    def run_all_tests(self):
        """Run all cross-language consistency tests."""
        print("Starting Cross-Language Consistency Tests...")
        print("=" * 50)
        
        try:
            print("\n1. Testing validation consistency...")
            self.test_validation_consistency()
            print("✓ Validation consistency tests passed")
            
            print("\n2. Testing config property consistency...")
            self.test_config_property_consistency()
            print("✓ Config property consistency tests passed")
            
            print("\n3. Testing API response format consistency...")
            self.test_api_response_format_consistency()
            print("✓ API response format consistency tests passed")
            
            print("\n4. Testing error handling consistency...")
            self.test_error_handling_consistency()
            print("✓ Error handling consistency tests passed")
            
            print("\n" + "=" * 50)
            print("All cross-language consistency tests passed! ✓")
            return True
            
        except Exception as e:
            print(f"\n✗ Test failed: {e}")
            return False


# Pytest-compatible test functions
def test_cross_language_validation_consistency():
    """Pytest version of validation consistency test."""
    tester = CrossLanguageConsistencyTests()
    tester.test_validation_consistency()


def test_cross_language_config_property_consistency():
    """Pytest version of config property consistency test."""
    tester = CrossLanguageConsistencyTests()
    tester.test_config_property_consistency()


def test_cross_language_api_response_format_consistency():
    """Pytest version of API response format consistency test."""
    tester = CrossLanguageConsistencyTests()
    tester.test_api_response_format_consistency()


def test_cross_language_error_handling_consistency():
    """Pytest version of error handling consistency test."""
    tester = CrossLanguageConsistencyTests()
    tester.test_error_handling_consistency()


def main():
    """Main test runner."""
    tester = CrossLanguageConsistencyTests()

    # Check if TypeScript runner exists
    if not tester.typescript_runner_path.exists():
        print(f"Warning: TypeScript runner not found at {tester.typescript_runner_path}")
        print("Some tests may be skipped.")

    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
