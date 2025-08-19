from collections.abc import Generator
from typing import Any
import httpx
import time
import json
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class AddMultimodalMemoryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # Get API key from credentials
        api_key = self.runtime.credentials["mem0_api_key"]
        
        # Get API URL from credentials or use default (consistent with provider/mem0.yaml)

        api_url = self.runtime.credentials.get("mem0_api_url", "http://localhost:8000")

        if not api_url or api_url.strip() == "":

            api_url = "http://localhost:8000"

        api_url = api_url.rstrip("/")
        
        # Extract new user-friendly parameters
        content_type = tool_parameters.get("content_type")
        content_text = tool_parameters.get("content_text")
        content_url = tool_parameters.get("content_url")
        context_description = tool_parameters.get("context_description")
        user_id = tool_parameters.get("user_id")
        agent_id = tool_parameters.get("agent_id")
        run_id = tool_parameters.get("run_id")
        metadata = tool_parameters.get("metadata")
        
        # Validate required parameters
        if not content_type:
            yield self.create_json_message({
                "status": "error",
                "error": "Content type must be specified"
            })
            yield self.create_text_message("Error: Content type must be specified")
            return
        
        # Validate content based on type
        if content_type == "text":
            if not content_text or not content_text.strip():
                yield self.create_json_message({
                    "status": "error",
                    "error": "Text content is required when content_type is 'text'"
                })
                yield self.create_text_message("Error: Text content is required when content_type is 'text'")
                return
        elif content_type in ["image", "document", "pdf"]:
            if not content_url or not content_url.strip():
                yield self.create_json_message({
                    "status": "error",
                    "error": f"Content URL is required when content_type is '{content_type}'"
                })
                yield self.create_text_message(f"Error: Content URL is required when content_type is '{content_type}'")
                return
        else:
            yield self.create_json_message({
                "status": "error",
                "error": "Invalid content_type. Must be 'text', 'image', 'document', or 'pdf'"
            })
            yield self.create_text_message("Error: Invalid content_type. Must be 'text', 'image', 'document', or 'pdf'")
            return
        
        # Construct appropriate message format based on content type
        if content_type == "text":
            # Simple text message
            message_content = content_text.strip()
            if context_description:
                message_content = f"{context_description.strip()}\n\n{message_content}"
            parsed_messages = [{"role": "user", "content": message_content}]
        
        elif content_type == "image":
            # Image URL format
            message_content = {
                "type": "image_url",
                "image_url": {"url": content_url.strip()}
            }
            if context_description:
                # Add context as a separate text message
                parsed_messages = [
                    {"role": "user", "content": context_description.strip()},
                    {"role": "user", "content": message_content}
                ]
            else:
                parsed_messages = [{"role": "user", "content": message_content}]
        
        elif content_type == "document":
            # MDX/Document URL format
            message_content = {
                "type": "mdx_url",
                "mdx_url": {"url": content_url.strip()}
            }
            if context_description:
                parsed_messages = [
                    {"role": "user", "content": context_description.strip()},
                    {"role": "user", "content": message_content}
                ]
            else:
                parsed_messages = [{"role": "user", "content": message_content}]
        
        elif content_type == "pdf":
            # PDF URL format
            message_content = {
                "type": "pdf_url",
                "pdf_url": {"url": content_url.strip()}
            }
            if context_description:
                parsed_messages = [
                    {"role": "user", "content": context_description.strip()},
                    {"role": "user", "content": message_content}
                ]
            else:
                parsed_messages = [{"role": "user", "content": message_content}]
        
        # Prepare payload
        payload = {
            "messages": parsed_messages
        }
        
        # Add identity parameters
        if user_id:
            payload["user_id"] = user_id
        if agent_id:
            payload["agent_id"] = agent_id
        if run_id:
            payload["run_id"] = run_id
        
        # Add metadata if provided
        if metadata:
            try:
                if isinstance(metadata, str):
                    payload["metadata"] = json.loads(metadata)
                else:
                    payload["metadata"] = metadata
            except json.JSONDecodeError:
                yield self.create_json_message({
                    "status": "error",
                    "error": "Invalid metadata format. Must be valid JSON."
                })
                yield self.create_text_message("Error: Invalid metadata format. Must be valid JSON.")
                return

        # Custom instructions support
        if tool_parameters.get("custom_instructions"):
            payload["custom_instructions"] = tool_parameters["custom_instructions"]

        if tool_parameters.get("custom_categories"):
            try:
                if isinstance(tool_parameters["custom_categories"], str):
                    payload["custom_categories"] = json.loads(tool_parameters["custom_categories"])
                else:
                    payload["custom_categories"] = tool_parameters["custom_categories"]
            except json.JSONDecodeError:
                yield self.create_json_message({
                    "status": "error",
                    "error": "Invalid custom_categories format. Must be valid JSON."
                })
                yield self.create_text_message("Error: Invalid custom_categories format. Must be valid JSON.")
                return

        # Async client configuration
        use_async = tool_parameters.get("use_async_client", False)
        if use_async:
            payload["async_processing"] = True

        # Selective memory parameters
        if tool_parameters.get("memory_priority"):
            payload["priority"] = tool_parameters["memory_priority"]

        if tool_parameters.get("auto_prune"):
            payload["auto_prune"] = tool_parameters["auto_prune"]

        # 记录添加操作
        identity = user_id or agent_id or run_id or "unknown"
        content_preview = ""
        if content_type == "text":
            content_preview = (content_text[:50] + "...") if len(content_text) > 50 else content_text
        else:
            content_preview = f"{content_type.upper()}: {content_url[:50]}{'...' if len(content_url) > 50 else ''}"        
        # 计时开始
        start_time = time.time()
        
        # Make HTTP request to add multimodal memory
        try:
            response = httpx.post(
                f"{api_url}/v1/memories/",
                json=payload,
                headers={"Authorization": f"Token {api_key}"},
                timeout=30  # 多模态处理需要更长时间
            )
            
            # 计算请求耗时
            request_time = time.time() - start_time
            response.raise_for_status()
            
            # Parse response
            response_data = response.json()
            
            # Extract memory information
            if isinstance(response_data, dict):
                if "results" in response_data:
                    # V1 API format
                    memories = response_data["results"]
                elif "memories" in response_data:
                    # V2 API format
                    memories = response_data["memories"]
                else:
                    # Single memory format
                    memories = [response_data]
            else:
                memories = response_data if isinstance(response_data, list) else [response_data]
            
            # Process memories
            processed_memories = []
            for memory in memories:
                if isinstance(memory, dict):
                    item = {
                        "id": memory.get("id", "unknown"),
                        "memory": memory.get("memory", ""),
                        "score": memory.get("score", 0.0),
                        "categories": memory.get("categories", []),
                        "created_at": memory.get("created_at", ""),
                        "metadata": memory.get("metadata", {}),
                        "user_id": memory.get("user_id"),
                        "agent_id": memory.get("agent_id"),
                        "run_id": memory.get("run_id")
                    }
                    processed_memories.append(item)
            
            # 记录添加结果
            # 计算总耗时
            total_time = time.time() - start_time
            yield self.create_json_message({
                "status": "success",
                "content_type": content_type,
                "identity": identity,
                "memories_created": len(processed_memories),
                "memories": processed_memories,
                "original_messages": parsed_messages,
                "metadata": payload.get("metadata"),
                "content_preview": content_preview
            })
            
            # Return text format
            text_response = f"Multimodal memory added successfully.\n\n"
            text_response += f"Content Type: {content_type.upper()}\n"
            text_response += f"Identity: {identity}\n"
            text_response += f"Memories Created: {len(processed_memories)}\n"
            text_response += f"Processing Time: {total_time:.3f}s\n"
            text_response += f"Content Preview: {content_preview}\n\n"
            
            if processed_memories:
                text_response += "Created Memories:\n"
                for idx, memory in enumerate(processed_memories, 1):
                    text_response += f"\n{idx}. ID: {memory['id']}"
                    text_response += f"\n   Memory: {memory['memory'][:100]}{'...' if len(memory['memory']) > 100 else ''}"
                    text_response += f"\n   Score: {memory['score']:.2f}"
                    text_response += f"\n   Categories: {', '.join(memory.get('categories', []))}"
                
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
                "identity": identity
            })
            
            yield self.create_text_message(f"Failed to add multimodal memory: {error_message}")
            
        except Exception as e:
            error_message = f"Error: {str(e)}"            
            yield self.create_json_message({
                "status": "error",
                "error": error_message,
                "identity": identity
            })
            
            yield self.create_text_message(f"Failed to add multimodal memory: {error_message}")
