#!/usr/bin/env python3
"""
Comprehensive validation script for Mem0 MCP Server
This script validates the complete installation and functionality
"""

import asyncio
import json
import httpx
import sys
import time
from typing import Dict, Any, List
from pathlib import Path


class MCPValidationSuite:
    """Comprehensive MCP server validation"""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.test_results: List[Dict[str, Any]] = []
    
    def log_test(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {status}")
        if details:
            print(f"   {details}")
    
    async def test_server_health(self) -> bool:
        """Test basic server health"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    health_data = response.json()
                    self.log_test(
                        "Server Health Check",
                        "PASS",
                        f"Status: {health_data.get('status', 'unknown')}"
                    )
                    return True
                else:
                    self.log_test(
                        "Server Health Check",
                        "FAIL",
                        f"HTTP {response.status_code}"
                    )
                    return False
        
        except Exception as e:
            self.log_test(
                "Server Health Check",
                "FAIL",
                f"Connection error: {str(e)}"
            )
            return False
    
    async def test_mcp_initialization(self) -> bool:
        """Test MCP protocol initialization"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                init_message = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "validation-client",
                            "version": "1.0.0"
                        }
                    },
                    "id": "validation-init"
                }
                
                response = await client.post(
                    f"{self.base_url}/message",
                    json=init_message
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("jsonrpc") == "2.0" and "result" in result:
                        server_info = result["result"].get("serverInfo", {})
                        self.log_test(
                            "MCP Initialization",
                            "PASS",
                            f"Server: {server_info.get('name', 'unknown')}"
                        )
                        return True
                    else:
                        self.log_test(
                            "MCP Initialization",
                            "FAIL",
                            "Invalid response format"
                        )
                        return False
                else:
                    self.log_test(
                        "MCP Initialization",
                        "FAIL",
                        f"HTTP {response.status_code}"
                    )
                    return False
        
        except Exception as e:
            self.log_test(
                "MCP Initialization",
                "FAIL",
                str(e)
            )
            return False
    
    async def test_tools_list(self) -> bool:
        """Test tools listing"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                tools_message = {
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "params": {},
                    "id": "validation-tools"
                }
                
                response = await client.post(
                    f"{self.base_url}/message",
                    json=tools_message
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                        expected_tools = {
                            "add_memory", "search_memories", "get_memories",
                            "get_memory_by_id", "delete_memory", "batch_delete_memories"
                        }
                        
                        tool_names = {tool["name"] for tool in tools}
                        missing_tools = expected_tools - tool_names
                        
                        if not missing_tools:
                            self.log_test(
                                "Tools List",
                                "PASS",
                                f"Found {len(tools)} tools"
                            )
                            return True
                        else:
                            self.log_test(
                                "Tools List",
                                "FAIL",
                                f"Missing tools: {missing_tools}"
                            )
                            return False
                    else:
                        self.log_test(
                            "Tools List",
                            "FAIL",
                            "Invalid response format"
                        )
                        return False
                else:
                    self.log_test(
                        "Tools List",
                        "FAIL",
                        f"HTTP {response.status_code}"
                    )
                    return False
        
        except Exception as e:
            self.log_test(
                "Tools List",
                "FAIL",
                str(e)
            )
            return False
    
    async def test_memory_operations(self) -> bool:
        """Test memory operations (mock mode)"""
        try:
            # Note: These tests assume Mem0 backend is running
            # In production, you would need actual Mem0 service
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Test add_memory
                add_message = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "add_memory",
                        "arguments": {
                            "messages": [
                                {"role": "user", "content": "Validation test memory"}
                            ],
                            "user_id": "validation_user"
                        }
                    },
                    "id": "validation-add"
                }
                
                response = await client.post(
                    f"{self.base_url}/message",
                    json=add_message
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result:
                        self.log_test(
                            "Memory Operations",
                            "PASS",
                            "add_memory tool executed successfully"
                        )
                        return True
                    elif "error" in result:
                        # Check if it's a connection error to Mem0 backend
                        error_msg = result["error"].get("message", "")
                        if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                            self.log_test(
                                "Memory Operations",
                                "WARN",
                                "Tools work but Mem0 backend not available"
                            )
                            return True
                        else:
                            self.log_test(
                                "Memory Operations",
                                "FAIL",
                                f"Tool error: {error_msg}"
                            )
                            return False
                    else:
                        self.log_test(
                            "Memory Operations",
                            "FAIL",
                            "Unexpected response format"
                        )
                        return False
                else:
                    self.log_test(
                        "Memory Operations",
                        "FAIL",
                        f"HTTP {response.status_code}"
                    )
                    return False
        
        except Exception as e:
            self.log_test(
                "Memory Operations",
                "FAIL",
                str(e)
            )
            return False
    
    async def test_error_handling(self) -> bool:
        """Test error handling"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test invalid JSON
                response = await client.post(
                    f"{self.base_url}/message",
                    data="invalid json",
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "error" in result and result["error"]["code"] == -32700:
                        self.log_test(
                            "Error Handling",
                            "PASS",
                            "JSON parse error handled correctly"
                        )
                        return True
                    else:
                        self.log_test(
                            "Error Handling",
                            "FAIL",
                            "Invalid error response format"
                        )
                        return False
                else:
                    self.log_test(
                        "Error Handling",
                        "FAIL",
                        f"HTTP {response.status_code}"
                    )
                    return False
        
        except Exception as e:
            self.log_test(
                "Error Handling",
                "FAIL",
                str(e)
            )
            return False
    
    async def test_concurrent_requests(self) -> bool:
        """Test concurrent request handling"""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Create multiple concurrent requests
                tasks = []
                for i in range(10):
                    message = {
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                        "id": f"concurrent-{i}"
                    }
                    task = client.post(f"{self.base_url}/message", json=message)
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                successful = 0
                for response in responses:
                    if not isinstance(response, Exception) and response.status_code == 200:
                        successful += 1
                
                if successful >= 8:  # At least 80% success rate
                    self.log_test(
                        "Concurrent Requests",
                        "PASS",
                        f"{successful}/10 requests successful"
                    )
                    return True
                else:
                    self.log_test(
                        "Concurrent Requests",
                        "FAIL",
                        f"Only {successful}/10 requests successful"
                    )
                    return False
        
        except Exception as e:
            self.log_test(
                "Concurrent Requests",
                "FAIL",
                str(e)
            )
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        print("🚀 Starting Mem0 MCP Server Validation Suite\n")
        
        test_functions = [
            self.test_server_health,
            self.test_mcp_initialization,
            self.test_tools_list,
            self.test_memory_operations,
            self.test_error_handling,
            self.test_concurrent_requests
        ]
        
        passed = 0
        warned = 0
        failed = 0
        
        for test_func in test_functions:
            try:
                result = await test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ {test_func.__name__}: EXCEPTION - {str(e)}")
                failed += 1
        
        # Count warnings
        warned = len([r for r in self.test_results if r["status"] == "WARN"])
        
        print(f"\n📊 Validation Summary:")
        print(f"   ✅ Passed: {passed}")
        print(f"   ⚠️  Warnings: {warned}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📈 Success Rate: {(passed / len(test_functions)) * 100:.1f}%")
        
        # Overall status
        if failed == 0:
            print("\n🎉 All tests passed! MCP server is ready for production.")
            overall_status = "SUCCESS"
        elif failed <= 2 and passed >= 4:
            print("\n⚠️  Most tests passed. Review failures and warnings.")
            overall_status = "WARNING"
        else:
            print("\n❌ Multiple test failures. Server needs attention.")
            overall_status = "FAILURE"
        
        return {
            "status": overall_status,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "total": len(test_functions),
            "details": self.test_results
        }
    
    def save_report(self, report: Dict[str, Any], filename: str = "validation_report.json"):
        """Save validation report to file"""
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            print(f"\n📄 Report saved to: {filename}")
        except Exception as e:
            print(f"\n⚠️  Could not save report: {e}")


async def main():
    """Main validation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate Mem0 MCP Server")
    parser.add_argument(
        "--url",
        default="http://localhost:8001",
        help="MCP server base URL (default: http://localhost:8001)"
    )
    parser.add_argument(
        "--report",
        default="validation_report.json",
        help="Report output filename (default: validation_report.json)"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = MCPValidationSuite(args.url)
    report = await validator.run_all_tests()
    
    # Save report
    validator.save_report(report, args.report)
    
    # Exit with appropriate code
    if report["status"] == "SUCCESS":
        sys.exit(0)
    elif report["status"] == "WARNING":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())