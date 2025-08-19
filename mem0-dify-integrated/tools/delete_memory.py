from collections.abc import Generator
from typing import Any
import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class DeleteMem0MemoryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # Get API key from credentials
        api_key = self.runtime.credentials["mem0_api_key"]
        
        # Get API URL from credentials or use default (consistent with provider/mem0.yaml)
        api_url = self.runtime.credentials.get("mem0_api_url", "http://localhost:8000")
        if not api_url or api_url.strip() == "":
            api_url = "http://localhost:8000"
        api_url = api_url.rstrip("/")
        
        # Extract memory ID
        memory_id = tool_parameters["memory_id"]
        
        # Validate memory ID
        if not memory_id or not memory_id.strip():
            yield self.create_json_message({
                "status": "error",
                "error": "Memory ID cannot be empty"
            })
            yield self.create_text_message("Error: Memory ID cannot be empty")
            return
        
        memory_id = memory_id.strip()

        # Async client configuration
        use_async = tool_parameters.get("use_async_client", False)
        timeout_val = 25 if use_async else 15
        
        try:
            # Make HTTP request to delete memory
            response = httpx.delete(
                f"{api_url}/v1/memories/{memory_id}/",
                headers={"Authorization": f"Token {api_key}"},
                timeout=timeout_val  # 删除操作相对简单但需要确保完成
            )
            
            response.raise_for_status()
            
            # Parse response
            try:
                response_data = response.json()
            except:
                # Some delete endpoints might return empty response
                response_data = {"message": "Memory deleted successfully"}
            
            # Success response
            yield self.create_json_message({
                "status": "success",
                "memory_id": memory_id,
                "message": "Memory deleted successfully",
                "response": response_data
            })
            
            yield self.create_text_message(f"Memory deleted successfully.\n\nMemory ID: {memory_id}")
            
        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error: {e.response.status_code}"
            
            # Handle specific error cases
            if e.response.status_code == 404:
                error_message = f"Memory not found: {memory_id}"
            elif e.response.status_code == 403:
                error_message = "Permission denied: Cannot delete this memory"
            elif e.response.status_code == 401:
                error_message = "Authentication failed: Invalid API key"
            else:
                try:
                    error_data = e.response.json()
                    if "detail" in error_data:
                        error_message = f"Error: {error_data['detail']}"
                    elif "message" in error_data:
                        error_message = f"Error: {error_data['message']}"
                except:
                    pass
                    
            yield self.create_json_message({
                "status": "error",
                "memory_id": memory_id,
                "error": error_message,
                "status_code": e.response.status_code
            })
            
            yield self.create_text_message(f"Failed to delete memory: {error_message}\n\nMemory ID: {memory_id}")
            
        except httpx.TimeoutException:
            error_message = "Request timeout: The delete operation took too long"
            yield self.create_json_message({
                "status": "error",
                "memory_id": memory_id,
                "error": error_message
            })
            
            yield self.create_text_message(f"Failed to delete memory: {error_message}\n\nMemory ID: {memory_id}")
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            yield self.create_json_message({
                "status": "error",
                "memory_id": memory_id,
                "error": error_message
            })
            
            yield self.create_text_message(f"Failed to delete memory: {error_message}\n\nMemory ID: {memory_id}")
