"""
Performance tests for Mem0 MCP Server
"""

import asyncio
import json
import time
import pytest
import httpx
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from unittest.mock import patch

from src.server import MCPServer
from src.config.settings import MCPConfig


class TestPerformance:
    """Performance tests for MCP server"""
    
    @pytest.fixture
    def config(self):
        return MCPConfig(
            host="localhost",
            port=8996,
            mem0_base_url="http://mock-mem0:8000",
            mem0_api_version="v1",
            debug=False  # Disable debug for performance tests
        )
    
    @pytest.fixture
    async def server(self, config):
        """Start server for performance tests"""
        server = MCPServer(config)
        await server.initialize()
        
        # Start transport
        transport_task = asyncio.create_task(server.transport.start())
        await asyncio.sleep(0.1)  # Wait for server to start
        
        yield server
        
        # Cleanup
        await server.stop()
        transport_task.cancel()
        try:
            await transport_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_concurrent_initialize_requests(self, server, config):
        """Test concurrent initialize requests performance"""
        num_requests = 50
        base_url = f"http://localhost:{config.port}"
        
        async def make_init_request(client: httpx.AsyncClient, request_id: int):
            start_time = time.time()
            
            response = await client.post(f"{base_url}/message", json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": f"perf-client-{request_id}", "version": "1.0.0"}
                },
                "id": f"init-{request_id}"
            })
            
            end_time = time.time()
            return {
                "status_code": response.status_code,
                "response_time": end_time - start_time,
                "request_id": request_id
            }
        
        # Execute concurrent requests
        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [make_init_request(client, i) for i in range(num_requests)]
            results = await asyncio.gather(*tasks)
        
        # Analyze results
        successful_requests = [r for r in results if r["status_code"] == 200]
        response_times = [r["response_time"] for r in successful_requests]
        
        assert len(successful_requests) == num_requests, "All requests should succeed"
        assert max(response_times) < 2.0, "Max response time should be under 2 seconds"
        assert sum(response_times) / len(response_times) < 0.5, "Average response time should be under 0.5 seconds"
    
    @pytest.mark.asyncio  
    async def test_tool_execution_performance(self, server, config):
        """Test tool execution performance under load"""
        num_requests = 30
        base_url = f"http://localhost:{config.port}"
        
        # Mock HTTP client responses
        with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
            mock_request.return_value = {
                "id": "perf_mem_123",
                "status": "success",
                "message": "Memory added successfully"
            }
            
            async def execute_add_memory_tool(client: httpx.AsyncClient, request_id: int):
                start_time = time.time()
                
                response = await client.post(f"{base_url}/message", json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "add_memory",
                        "arguments": {
                            "messages": [{"role": "user", "content": f"Performance test memory {request_id}"}],
                            "user_id": f"perf_user_{request_id}"
                        }
                    },
                    "id": f"tool-{request_id}"
                })
                
                end_time = time.time()
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "request_id": request_id
                }
            
            # Execute concurrent tool calls
            async with httpx.AsyncClient(timeout=10.0) as client:
                tasks = [execute_add_memory_tool(client, i) for i in range(num_requests)]
                results = await asyncio.gather(*tasks)
            
            # Analyze results
            successful_requests = [r for r in results if r["status_code"] == 200]
            response_times = [r["response_time"] for r in successful_requests]
            
            assert len(successful_requests) == num_requests, "All tool executions should succeed"
            assert max(response_times) < 3.0, "Max tool execution time should be under 3 seconds"
            assert sum(response_times) / len(response_times) < 1.0, "Average tool execution time should be under 1 second"
    
    @pytest.mark.asyncio
    async def test_mixed_workload_performance(self, server, config):
        """Test mixed workload performance"""
        base_url = f"http://localhost:{config.port}"
        
        # Mock responses for different operations
        def mock_response_side_effect(method, endpoint, **kwargs):
            if "memories" in endpoint and method == "POST":
                return {"id": "mem_mixed_123", "status": "success"}
            elif "search" in endpoint:
                return {"results": [{"id": "mem_1", "memory": "Test memory", "score": 0.9}]}
            elif "memories" in endpoint and method == "GET":
                return {"memories": [{"id": "mem_1", "memory": "Test memory"}]}
            else:
                return {"status": "ok"}
        
        with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
            mock_request.side_effect = mock_response_side_effect
            
            async def execute_mixed_request(client: httpx.AsyncClient, request_id: int):
                start_time = time.time()
                
                # Randomly choose operation type
                operation_type = request_id % 4
                
                if operation_type == 0:  # Add memory
                    message = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "add_memory",
                            "arguments": {
                                "messages": [{"role": "user", "content": f"Mixed test {request_id}"}],
                                "user_id": f"mixed_user_{request_id}"
                            }
                        },
                        "id": f"mixed-{request_id}"
                    }
                elif operation_type == 1:  # Search memories
                    message = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "search_memories",
                            "arguments": {
                                "query": f"test query {request_id}",
                                "user_id": f"mixed_user_{request_id}"
                            }
                        },
                        "id": f"mixed-{request_id}"
                    }
                elif operation_type == 2:  # Get memories
                    message = {
                        "jsonrpc": "2.0",
                        "method": "tools/call",
                        "params": {
                            "name": "get_memories",
                            "arguments": {
                                "user_id": f"mixed_user_{request_id}"
                            }
                        },
                        "id": f"mixed-{request_id}"
                    }
                else:  # Tools list
                    message = {
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                        "id": f"mixed-{request_id}"
                    }
                
                response = await client.post(f"{base_url}/message", json=message)
                end_time = time.time()
                
                return {
                    "status_code": response.status_code,
                    "response_time": end_time - start_time,
                    "operation_type": operation_type,
                    "request_id": request_id
                }
            
            # Execute mixed workload
            num_requests = 40
            async with httpx.AsyncClient(timeout=15.0) as client:
                tasks = [execute_mixed_request(client, i) for i in range(num_requests)]
                results = await asyncio.gather(*tasks)
            
            # Analyze results by operation type
            successful_requests = [r for r in results if r["status_code"] == 200]
            
            assert len(successful_requests) == num_requests, "All mixed requests should succeed"
            
            # Group by operation type
            operation_stats = {}
            for result in successful_requests:
                op_type = result["operation_type"]
                if op_type not in operation_stats:
                    operation_stats[op_type] = []
                operation_stats[op_type].append(result["response_time"])
            
            # Verify performance for each operation type
            for op_type, times in operation_stats.items():
                avg_time = sum(times) / len(times)
                max_time = max(times)
                
                assert avg_time < 1.5, f"Average time for operation type {op_type} should be under 1.5s"
                assert max_time < 5.0, f"Max time for operation type {op_type} should be under 5s"
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, server, config):
        """Test memory usage remains stable under continuous load"""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        base_url = f"http://localhost:{config.port}"
        
        with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
            mock_request.return_value = {"id": "mem_stability_123", "status": "success"}
            
            # Run continuous requests for stability test
            num_iterations = 5
            requests_per_iteration = 10
            
            memory_measurements = [initial_memory]
            
            for iteration in range(num_iterations):
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Execute batch of requests
                    tasks = []
                    for i in range(requests_per_iteration):
                        task = client.post(f"{base_url}/message", json={
                            "jsonrpc": "2.0",
                            "method": "tools/call",
                            "params": {
                                "name": "add_memory",
                                "arguments": {
                                    "messages": [{"role": "user", "content": f"Stability test {iteration}-{i}"}],
                                    "user_id": f"stability_user_{iteration}_{i}"
                                }
                            },
                            "id": f"stability-{iteration}-{i}"
                        })
                        tasks.append(task)
                    
                    results = await asyncio.gather(*tasks)
                    
                    # Verify all requests succeeded
                    assert all(r.status_code == 200 for r in results)
                
                # Measure memory after each iteration
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_measurements.append(current_memory)
                
                # Allow some time for garbage collection
                await asyncio.sleep(1)
            
            # Analyze memory usage trend
            final_memory = memory_measurements[-1]
            memory_increase = final_memory - initial_memory
            
            # Memory should not increase by more than 50MB during the test
            assert memory_increase < 50, f"Memory increased too much: {memory_increase:.2f}MB"
            
            # Memory usage should be relatively stable (no continuous growth)
            max_memory = max(memory_measurements)
            min_memory = min(memory_measurements)
            memory_variance = max_memory - min_memory
            
            assert memory_variance < 100, f"Memory usage too variable: {memory_variance:.2f}MB"


class TestThroughputBenchmark:
    """Throughput benchmark tests"""
    
    @pytest.mark.asyncio
    async def test_requests_per_second_benchmark(self):
        """Benchmark requests per second capacity"""
        config = MCPConfig(
            host="localhost",
            port=8995,
            mem0_base_url="http://mock-mem0:8000",
            debug=False
        )
        
        server = MCPServer(config)
        await server.initialize()
        
        # Start server
        transport_task = asyncio.create_task(server.transport.start())
        await asyncio.sleep(0.1)
        
        try:
            base_url = f"http://localhost:{config.port}"
            
            with patch('src.client.mem0_client.Mem0HTTPClient._make_request') as mock_request:
                mock_request.return_value = {"id": "benchmark_123", "status": "success"}
                
                # Run benchmark for 10 seconds
                test_duration = 10  # seconds
                start_time = time.time()
                request_count = 0
                
                async def benchmark_worker(client: httpx.AsyncClient):
                    nonlocal request_count
                    while time.time() - start_time < test_duration:
                        try:
                            response = await client.post(f"{base_url}/message", json={
                                "jsonrpc": "2.0",
                                "method": "tools/call",
                                "params": {
                                    "name": "add_memory",
                                    "arguments": {
                                        "messages": [{"role": "user", "content": "Benchmark test"}],
                                        "user_id": "benchmark_user"
                                    }
                                },
                                "id": f"benchmark-{request_count}"
                            })
                            if response.status_code == 200:
                                request_count += 1
                        except Exception:
                            pass  # Continue benchmarking despite errors
                
                # Run multiple concurrent workers
                num_workers = 10
                async with httpx.AsyncClient(timeout=5.0) as client:
                    workers = [benchmark_worker(client) for _ in range(num_workers)]
                    await asyncio.gather(*workers)
                
                actual_duration = time.time() - start_time
                requests_per_second = request_count / actual_duration
                
                print(f"Benchmark Results:")
                print(f"- Total requests: {request_count}")
                print(f"- Duration: {actual_duration:.2f} seconds")
                print(f"- Requests per second: {requests_per_second:.2f}")
                
                # Baseline expectation: at least 50 RPS
                assert requests_per_second >= 50, f"Throughput too low: {requests_per_second:.2f} RPS"
        
        finally:
            await server.stop()
            transport_task.cancel()
            try:
                await transport_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])