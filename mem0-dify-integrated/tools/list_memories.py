from collections.abc import Generator
from typing import Any, Dict, List
import json
import httpx
import time
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class ListMemoriesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # Get API key from credentials
        api_key = self.runtime.credentials["mem0_api_key"]
        
        # Get API URL from credentials or use default (consistent with provider/mem0.yaml)

        api_url = self.runtime.credentials.get("mem0_api_url", "http://localhost:8000")

        if not api_url or api_url.strip() == "":

            api_url = "http://localhost:8000"

        api_url = api_url.rstrip("/")
        
        # Extract parameters
        user_id = tool_parameters.get("user_id")
        agent_id = tool_parameters.get("agent_id")
        run_id = tool_parameters.get("run_id")
        limit = tool_parameters.get("limit", 50)
        offset = tool_parameters.get("offset", 0)
        filters = tool_parameters.get("filters")
        sort = tool_parameters.get("sort")
        
        # Prepare payload for V2 API
        payload = {}
        
        # V2 API使用filters字段包含所有标识符
        filters_dict = {}
        
        # Add identity parameters to filters
        if user_id:
            filters_dict["user_id"] = user_id
        if agent_id:
            filters_dict["agent_id"] = agent_id
        if run_id:
            filters_dict["run_id"] = run_id
        
        # Add pagination
        payload["limit"] = limit
        payload["offset"] = offset
        
        # Add advanced parameters to filters
        if filters:
            try:
                if isinstance(filters, str):
                    additional_filters = json.loads(filters)
                else:
                    additional_filters = filters
                # 合并用户提供的filters和标识符filters
                filters_dict.update(additional_filters)
            except json.JSONDecodeError:
                yield self.create_json_message({
                    "status": "error",
                    "error": "Invalid filters format. Must be valid JSON."
                })
                yield self.create_text_message("Error: Invalid filters format. Must be valid JSON.")
                return
        
        # 设置filters字段
        if filters_dict:
            payload["filters"] = filters_dict
        
        if sort:
            try:
                if isinstance(sort, str):
                    payload["sort"] = json.loads(sort)
                else:
                    payload["sort"] = sort
            except json.JSONDecodeError:
                yield self.create_json_message({
                    "status": "error", 
                    "error": "Invalid sort format. Must be valid JSON."
                })
                yield self.create_text_message("Error: Invalid sort format. Must be valid JSON.")
                return

        # Selective memory support
        if tool_parameters.get("memory_priority"):
            if "filters" not in payload:
                payload["filters"] = {}
            payload["filters"]["priority"] = tool_parameters["memory_priority"]

        if tool_parameters.get("importance_threshold"):
            if "filters" not in payload:
                payload["filters"] = {}
            payload["filters"]["importance_threshold"] = tool_parameters["importance_threshold"]

        if tool_parameters.get("auto_prune"):
            payload["auto_prune"] = tool_parameters["auto_prune"]

        if tool_parameters.get("memory_capacity_limit"):
            payload["capacity_limit"] = tool_parameters["memory_capacity_limit"]

        # Async client configuration
        use_async = tool_parameters.get("use_async_client", False)
        timeout_val = 30 if use_async else 20

        # 记录请求信息
        identity = user_id or agent_id or run_id or "unknown"        
        # 计时开始
        start_time = time.time()
        
        # Make HTTP request to mem0 V2 API
        try:
            response = httpx.post(
                f"{api_url}/v2/memories/",
                json=payload,
                headers={"Authorization": f"Token {api_key}"},
                timeout=timeout_val  # 批量获取可能需要更多时间
            )
            
            # 计算请求耗时
            request_time = time.time() - start_time
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # V2 API returns: {"memories": [...], "pagination": {...}}
            memories = []
            pagination_info = {}
            
            if isinstance(response_data, dict):
                if "memories" in response_data:
                    memories = response_data["memories"]
                
                if "pagination" in response_data:
                    pagination_info = response_data["pagination"]
            else:
                yield self.create_json_message({
                    "identity": identity,
                    "api_version": "v2",
                    "memories": [],
                    "error": "Unexpected response format"
                })
                yield self.create_text_message(f"Identity: {identity}\n\nUnexpected V2 response format")
                return
            
            # Process results
            processed_memories = []
            for memory in memories:
                if not isinstance(memory, dict):
                    continue
                    
                # 安全处理score字段，可能为None
                score_value = memory.get("score")
                if score_value is None:
                    score_value = 0.0

                item = {
                    "id": memory.get("id", "unknown"),
                    "memory": memory.get("memory", ""),
                    "score": score_value,
                    "categories": memory.get("categories", []),
                    "created_at": memory.get("created_at", ""),
                    "updated_at": memory.get("updated_at", ""),
                    "metadata": memory.get("metadata", {}),
                    "user_id": memory.get("user_id"),
                    "agent_id": memory.get("agent_id"),
                    "run_id": memory.get("run_id")
                }
                processed_memories.append(item)
            
            # 记录结果统计            
            # 计算总耗时
            total_time = time.time() - start_time                
            yield self.create_json_message({
                "identity": identity,
                "api_version": "v2",
                "memories": processed_memories,
                "pagination": pagination_info,
                "total_count": len(processed_memories),
                "request_params": {
                    "limit": limit,
                    "offset": offset,
                    "filters": payload.get("filters"),
                    "sort": payload.get("sort")
                }
            })
            
            # Return text format
            text_response = f"Identity: {identity}\nAPI Version: V2\n\nMemories Retrieved: {len(processed_memories)}\n"
            
            if pagination_info:
                text_response += f"Pagination: {pagination_info}\n"
            
            text_response += "\nMemories:\n"
            if processed_memories:
                for idx, memory in enumerate(processed_memories, 1):
                    text_response += f"\n{idx}. ID: {memory['id']}"
                    text_response += f"\n   Memory: {memory['memory'][:100]}{'...' if len(memory['memory']) > 100 else ''}"
                    # 安全处理score字段，可能为None
                    score_value = memory.get('score')
                    if score_value is not None:
                        text_response += f"\n   Score: {score_value:.2f}"
                    else:
                        text_response += f"\n   Score: N/A"
                    text_response += f"\n   Categories: {', '.join(memory.get('categories', []))}"
                    text_response += f"\n   Created: {memory.get('created_at', 'N/A')}"
                    if memory.get('metadata'):
                        text_response += f"\n   Metadata: {memory['metadata']}"
            else:
                text_response += "\nNo memories found."
                
            yield self.create_text_message(text_response)
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "detail" in error_data:
                    error_message = f"Error: {error_data['detail']}"
            except:
                pass            
            yield self.create_json_message({
                "status": "error",
                "error": error_message,
                "identity": identity,
                "api_version": "v2"
            })
            
            yield self.create_text_message(f"Failed to get memories: {error_message}")
            
        except Exception as e:
            error_message = f"Error: {str(e)}"            
            yield self.create_json_message({
                "status": "error",
                "error": error_message,
                "identity": identity,
                "api_version": "v2"
            })
            
            yield self.create_text_message(f"Failed to get memories: {error_message}")
