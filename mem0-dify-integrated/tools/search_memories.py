from collections.abc import Generator
from typing import Any
import json
import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class SearchMemoriesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        # Get API key from credentials (may be empty for local deployment)
        api_key = self.runtime.credentials.get("mem0_api_key", "")

        # Get API URL from credentials or use default (consistent with provider/mem0.yaml)
        api_url = self.runtime.credentials.get("mem0_api_url", "http://localhost:8000")

        if not api_url or api_url.strip() == "":
            api_url = "http://localhost:8000"

        api_url = api_url.rstrip("/")

        # Get required parameters
        query = tool_parameters.get("query", "")
        user_id = tool_parameters.get("user_id", "")

        # Validate required parameters
        if not query:
            yield self.create_json_message({
                "status": "error",
                "error": "Query is required"
            })
            yield self.create_text_message("Error: Query is required.")
            return
        if not user_id:
            yield self.create_json_message({
                "status": "error",
                "error": "User ID is required"
            })
            yield self.create_text_message("Error: User ID is required.")
            return

        # Prepare V2 payload for search - 身份标识符作为顶级字段
        payload = {
            "query": query
        }

        # Add identity parameters as top-level fields (NOT in filters)
        if user_id:
            payload["user_id"] = user_id
        if tool_parameters.get("agent_id"):
            payload["agent_id"] = tool_parameters["agent_id"]
        if tool_parameters.get("run_id"):
            payload["run_id"] = tool_parameters["run_id"]

        # Initialize filters dict for actual filtering conditions
        filters_dict = {}

        # Handle pagination (V2 format)
        limit = tool_parameters.get("limit", 10)
        if limit and 1 <= limit <= 100:
            payload["limit"] = limit

        # Handle similarity threshold - 放入filters中作为过滤条件
        similarity_threshold = tool_parameters.get("similarity_threshold")
        if similarity_threshold is not None:
            # 确保similarity_threshold是字符串格式
            if isinstance(similarity_threshold, (int, float)):
                filters_dict["similarity_threshold"] = str(similarity_threshold)
            else:
                filters_dict["similarity_threshold"] = similarity_threshold

        # Handle advanced filters - 合并到filters_dict中
        if tool_parameters.get("filters"):
            try:
                additional_filters = json.loads(tool_parameters["filters"])
                # 合并额外的filters到filters_dict
                filters_dict.update(additional_filters)
            except json.JSONDecodeError as e:
                error_message = f"Invalid JSON in filters: {str(e)}"
                yield self.create_json_message({
                    "status": "error",
                    "error": error_message
                })
                yield self.create_text_message(f"Failed to retrieve memory: {error_message}")
                return

        # Criteria-based retrieval support - 添加到filters_dict
        # 修复：正确处理空字符串参数和类型检查
        score_range = tool_parameters.get("score_range")
        if score_range and isinstance(score_range, str) and score_range.strip():
            filters_dict["score_range"] = score_range

        date_range = tool_parameters.get("date_range")
        if date_range and isinstance(date_range, str) and date_range.strip():
            filters_dict["date_range"] = date_range

        category_filter = tool_parameters.get("category_filter")
        if category_filter and isinstance(category_filter, str) and category_filter.strip():
            filters_dict["categories"] = category_filter

        # 将filters_dict添加到payload中（如果不为空）
        if filters_dict:
            payload["filters"] = filters_dict

        # Graph memory support - 作为顶级字段
        # 修复：正确处理空字符串、"False"字符串和布尔值
        enable_graph = tool_parameters.get("enable_graph")
        if enable_graph is not None:
            # 处理布尔值类型
            if isinstance(enable_graph, bool):
                if enable_graph:  # True
                    payload["enable_graph"] = enable_graph
            # 处理字符串类型
            elif isinstance(enable_graph, str):
                if enable_graph.strip() and enable_graph.lower() not in ["false", "0", "no", "off"]:
                    payload["enable_graph"] = enable_graph

        graph_entities = tool_parameters.get("graph_entities")
        if graph_entities and isinstance(graph_entities, str) and graph_entities.strip():
            payload["graph_entities"] = graph_entities

        relationship_filter = tool_parameters.get("relationship_filter")
        if relationship_filter and isinstance(relationship_filter, str) and relationship_filter.strip():
            payload["relationship_filter"] = relationship_filter

        # Make HTTP request to mem0 V2 API
        try:
            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Add authorization header only if API key is provided
            if api_key and api_key.strip():
                headers["Authorization"] = f"Token {api_key}"

            response = httpx.post(
                f"{api_url}/v2/memories/search/",
                json=payload,
                headers=headers,
                timeout=20  # v2检索可能需要更多时间
            )

            response.raise_for_status()
            response_data = response.json()

            # Debug: Log response structure for troubleshooting
            debug_info = {
                "status_code": response.status_code,
                "response_keys": list(response_data.keys()) if isinstance(response_data, dict) else "not_dict",
                "api_url": f"{api_url}/v2/memories/search/",
                "payload": payload
            }

            # V2 API实际返回格式: {"results": {"results": [...], "relations": []}, "total_count": N, ...}
            memories = []
            relations = []
            pagination_info = {}

            if isinstance(response_data, dict):
                # 处理V2 API的实际响应格式
                if "results" in response_data and isinstance(response_data["results"], dict):
                    if "results" in response_data["results"]:
                        memories = response_data["results"]["results"]
                        debug_info["memories_found"] = len(memories)

                    # 处理关系图谱数据 - 这是关键修复！
                    if "relations" in response_data["results"]:
                        relations = response_data["results"]["relations"]
                        debug_info["relations_found"] = len(relations)

                # 构建分页信息
                if "total_count" in response_data:
                    pagination_info["total_count"] = response_data["total_count"]
                if "limit" in response_data:
                    pagination_info["limit"] = response_data["limit"]

                # 兼容旧格式（如果API格式发生变化）
                elif "memories" in response_data:
                    memories = response_data["memories"]
                    debug_info["memories_found"] = len(memories)
                    debug_info["format"] = "legacy"
                    if "pagination" in response_data:
                        pagination_info = response_data["pagination"]
            else:
                yield self.create_json_message({
                    "query": query,
                    "api_version": "v2",
                    "memories": [],
                    "error": "Unexpected response format",
                    "debug": debug_info
                })
                yield self.create_text_message(f"Query: {query}\n\nUnexpected V2 response format. Debug: {debug_info}")
                return

            # Process V2 memories
            processed_memories = []
            for memory in memories:
                if not isinstance(memory, dict):
                    continue

                # 安全处理score字段，可能为None
                score_value = memory.get("score")
                if score_value is None:
                    score_value = 0.0

                memory_item = {
                    "id": memory.get("id", "unknown"),
                    "memory": memory.get("memory", ""),
                    "score": score_value,
                    "categories": memory.get("categories", []),
                    "created_at": memory.get("created_at", ""),
                    "updated_at": memory.get("updated_at", ""),
                    "metadata": memory.get("metadata", {}),
                    "user_id": memory.get("user_id", ""),
                    "agent_id": memory.get("agent_id", ""),
                    "run_id": memory.get("run_id", "")
                }
                processed_memories.append(memory_item)

            # Process relations data - 关键修复！
            processed_relations = []
            for relation in relations:
                if not isinstance(relation, dict):
                    continue

                # 将关系转换为可读的记忆格式
                relation_memory = {
                    "id": f"relation_{len(processed_relations)}",
                    "memory": f"{relation.get('source', 'Unknown')} {relation.get('relationship', 'relates to')} {relation.get('destination', 'Unknown')}",
                    "score": 1.0,  # 关系数据默认高分
                    "categories": ["relationship", "graph"],
                    "created_at": "",
                    "updated_at": "",
                    "metadata": {
                        "type": "relation",
                        "source": relation.get("source", ""),
                        "relationship": relation.get("relationship", ""),
                        "destination": relation.get("destination", ""),
                        "original_relation": relation
                    },
                    "user_id": relation.get("source", ""),
                    "agent_id": "",
                    "run_id": ""
                }
                processed_relations.append(relation_memory)

            # 合并记忆和关系数据
            all_results = processed_memories + processed_relations
            debug_info["total_results"] = len(all_results)
            debug_info["memory_results"] = len(processed_memories)
            debug_info["relation_results"] = len(processed_relations)

            # Return JSON format
            yield self.create_json_message({
                "query": query,
                "api_version": "v2",
                "memories": all_results,  # 包含记忆和关系数据
                "memory_results": processed_memories,  # 仅记忆数据
                "relation_results": processed_relations,  # 仅关系数据
                "pagination": pagination_info,
                "total_found": len(all_results),  # 总数包含记忆和关系
                "debug": debug_info
            })

            # Return text format
            text_response = f"Query: {query} (V2 API)\n\n"

            if all_results:
                text_response += f"Found {len(all_results)} results ({len(processed_memories)} memories, {len(processed_relations)} relations):\n\n"

                # 显示记忆结果
                if processed_memories:
                    text_response += "📝 Memories:\n"
                    for idx, memory in enumerate(processed_memories[:5], 1):  # 限制显示前5条记忆
                        text_response += f"{idx}. {memory['memory']}\n"
                        score_value = memory.get('score')
                        if score_value is not None:
                            text_response += f"   Score: {score_value:.3f}\n"
                        if memory.get('categories'):
                            text_response += f"   Categories: {', '.join(memory['categories'])}\n"
                        text_response += "\n"

                # 显示关系结果
                if processed_relations:
                    text_response += "🔗 Relations:\n"
                    for idx, relation in enumerate(processed_relations[:5], 1):  # 限制显示前5条关系
                        text_response += f"{idx}. {relation['memory']}\n"
                        text_response += f"   Type: Relationship\n"
                        metadata = relation.get('metadata', {})
                        if metadata.get('source') and metadata.get('destination'):
                            text_response += f"   Connection: {metadata['source']} → {metadata['destination']}\n"
                        text_response += "\n"

                if len(all_results) > 10:
                    text_response += f"... and {len(all_results) - 10} more results\n"
            else:
                text_response += "No memories or relations found for this query."

            if pagination_info:
                text_response += f"\n\nPagination: {pagination_info}"

            yield self.create_text_message(text_response)

        except httpx.HTTPStatusError as e:
            error_message = f"HTTP error: {e.response.status_code}"
            try:
                error_data = e.response.json()
                if "detail" in error_data:
                    error_message = f"Error: {error_data['detail']}"
                elif "error" in error_data:
                    error_message = f"Error: {error_data['error']}"
            except:
                pass

            yield self.create_json_message({
                "status": "error",
                "api_version": "v2",
                "error": error_message
            })

            yield self.create_text_message(f"Failed to retrieve memory (V2): {error_message}")

        except Exception as e:
            error_message = f"Error: {str(e)}"

            yield self.create_json_message({
                "status": "error",
                "api_version": "v2",
                "error": error_message
            })

            yield self.create_text_message(f"Failed to retrieve memory (V2): {error_message}")
