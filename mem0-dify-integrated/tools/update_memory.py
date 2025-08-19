from collections.abc import Generator
from typing import Any
import httpx
import time
import json
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class UpdateMem0MemoryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # Get API key from credentials
        api_key = self.runtime.credentials["mem0_api_key"]
        
        # Get API URL from credentials or use default (consistent with provider/mem0.yaml)

        api_url = self.runtime.credentials.get("mem0_api_url", "http://localhost:8000")

        if not api_url or api_url.strip() == "":

            api_url = "http://localhost:8000"

        api_url = api_url.rstrip("/")
        
        # Extract parameters
        memory_id = tool_parameters["memory_id"]
        new_memory = tool_parameters["new_memory"]
        
        # Validate inputs
        if not memory_id or not memory_id.strip():
            yield self.create_json_message({
                "status": "error",
                "error": "Memory ID cannot be empty"
            })
            yield self.create_text_message("Error: Memory ID cannot be empty")
            return
            
        if not new_memory or not new_memory.strip():
            yield self.create_json_message({
                "status": "error", 
                "error": "New memory content cannot be empty"
            })
            yield self.create_text_message("Error: New memory content cannot be empty")
            return
        
        memory_id = memory_id.strip()
        new_memory = new_memory.strip()
        
        # Prepare payload
        payload = {
            "text": new_memory
        }

        # Async client configuration
        use_async = tool_parameters.get("use_async_client", False)
        timeout_val = 35 if use_async else 25

        # 记录更新操作
        memory_preview = new_memory[:50] + "..." if len(new_memory) > 50 else new_memory        
        # 计时开始
        start_time = time.time()
        
        # Make HTTP request to update memory
        try:
            response = httpx.put(
                f"{api_url}/v1/memories/{memory_id}/",
                json=payload,
                headers={"Authorization": f"Token {api_key}"},
                timeout=timeout_val  # 更新记忆需要重新处理和分析
            )
            
            # 计算请求耗时
            request_time = time.time() - start_time
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract updated memory info
            updated_memory = response_data
            if isinstance(response_data, dict):
                memory_info = {
                    "id": updated_memory.get("id", memory_id),
                    "memory": updated_memory.get("memory", new_memory),
                    "score": updated_memory.get("score", 0.0),
                    "categories": updated_memory.get("categories", []),
                    "created_at": updated_memory.get("created_at", ""),
                    "updated_at": updated_memory.get("updated_at", ""),
                    "metadata": updated_memory.get("metadata", {})
                }
            else:
                memory_info = {
                    "id": memory_id,
                    "memory": new_memory,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # 记录更新结果            
            # 计算总耗时
            total_time = time.time() - start_time                
            yield self.create_json_message({
                "status": "success",
                "memory_id": memory_id,
                "updated_memory": memory_info,
                "original_response": response_data
            })
            
            # Return text format
            text_response = f"Memory updated successfully.\n\n"
            text_response += f"Memory ID: {memory_info['id']}\n"
            text_response += f"Updated Content: {memory_info['memory']}\n"
            text_response += f"Score: {memory_info.get('score', 'N/A')}\n"
            text_response += f"Categories: {', '.join(memory_info.get('categories', []))}\n"
            text_response += f"Updated At: {memory_info.get('updated_at', 'N/A')}"
            
            if memory_info.get('metadata'):
                text_response += f"\nMetadata: {memory_info['metadata']}"
                
            yield self.create_text_message(text_response)
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error: {e.response.status_code}"
            
            # Handle specific error cases
            if e.response.status_code == 404:
                error_message = f"Memory not found: {memory_id}"
            elif e.response.status_code == 403:
                error_message = "Permission denied: Cannot update this memory"
            elif e.response.status_code == 401:
                error_message = "Authentication failed: Invalid API key"
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    if "detail" in error_data:
                        error_message = f"Bad request: {error_data['detail']}"
                except:
                    error_message = "Bad request: Invalid memory content"
            else:
                try:
                    error_data = e.response.json()
                    if "detail" in error_data:
                        error_message = f"Error: {error_data['detail']}"
                except:
                    pass            
            yield self.create_json_message({
                "status": "error",
                "memory_id": memory_id,
                "error": error_message,
                "status_code": e.response.status_code
            })
            
            yield self.create_text_message(f"Failed to update memory: {error_message}\n\nMemory ID: {memory_id}")
            
        except Exception as e:
            error_message = f"Error: {str(e)}"            
            yield self.create_json_message({
                "status": "error",
                "memory_id": memory_id,
                "error": error_message
            })
            
            yield self.create_text_message(f"Failed to update memory: {error_message}\n\nMemory ID: {memory_id}")
