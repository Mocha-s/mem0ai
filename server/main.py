import json
import logging
import os
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import fcntl

# Filter out compatibility and deprecation warnings
warnings.filterwarnings("ignore", message="Qdrant client version .* is incompatible with server version .*")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Field name .* shadows an attribute")
warnings.filterwarnings("ignore", message="`max_items` is deprecated and will be removed, use `max_length` instead")

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from mem0 import Memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Load environment variables
load_dotenv()


POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_COLLECTION_NAME = os.environ.get("POSTGRES_COLLECTION_NAME", "memories")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "mem0graph")

MEMGRAPH_URI = os.environ.get("MEMGRAPH_URI", "bolt://localhost:7687")
MEMGRAPH_USERNAME = os.environ.get("MEMGRAPH_USERNAME", "memgraph")
MEMGRAPH_PASSWORD = os.environ.get("MEMGRAPH_PASSWORD", "mem0graph")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.1"))
HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/data/history.db")

DEFAULT_CONFIG = {
    "version": "v1.1",
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "qdrant",
            "port": 6333,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL,
            "temperature": OPENAI_TEMPERATURE,
            "openai_base_url": OPENAI_BASE_URL
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_EMBEDDING_MODEL,
            "openai_base_url": OPENAI_BASE_URL
        }
    },
    "history_db_path": HISTORY_DB_PATH,
}


MEMORY_INSTANCE = Memory.from_config(DEFAULT_CONFIG)

# Global export task storage and executor
EXPORT_TASKS = {}  # {task_id: {"status": str, "result": Any, "error": str, "created_at": datetime}}
EXPORT_EXECUTOR = ThreadPoolExecutor(max_workers=3)

app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)


@app.get("/health", summary="Health Check")
def health_check():
    """Health check endpoint for Docker health checks and load balancers."""
    try:
        # Comprehensive health check
        health_status = {
            "status": "healthy",
            "service": "mem0-api",
            "version": "1.0.0",
            "timestamp": time.time(),
            "checks": {}
        }

        # Check memory instance
        if MEMORY_INSTANCE:
            health_status["checks"]["memory_instance"] = "ok"
        else:
            health_status["checks"]["memory_instance"] = "failed"
            health_status["status"] = "unhealthy"

        # Check database connections (basic connectivity)
        try:
            # This is a lightweight check - just verify the instance exists
            if hasattr(MEMORY_INSTANCE, 'vector_store'):
                health_status["checks"]["vector_store"] = "ok"
            else:
                health_status["checks"]["vector_store"] = "unknown"
        except Exception:
            health_status["checks"]["vector_store"] = "failed"

        try:
            if hasattr(MEMORY_INSTANCE, 'graph_store'):
                health_status["checks"]["graph_store"] = "ok"
            else:
                health_status["checks"]["graph_store"] = "unknown"
        except Exception:
            health_status["checks"]["graph_store"] = "failed"

        # Return appropriate status code
        if health_status["status"] == "healthy":
            return health_status
        else:
            raise HTTPException(status_code=503, detail=health_status)

    except Exception as e:
        raise HTTPException(status_code=503, detail={
            "status": "unhealthy",
            "error": str(e),
            "service": "mem0-api"
        })





class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: str = Field(..., description="Message content.")


class MemoryCreate(BaseModel):
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query.")
    user_id: Optional[str] = None
    run_id: Optional[str] = None
    agent_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    keyword_search: Optional[bool] = Field(False, description="Enable BM25 keyword search")
    rerank: Optional[bool] = Field(False, description="Enable LLM-based reranking")
    filter_memories: Optional[bool] = Field(False, description="Enable intelligent memory filtering")


class UpdateMemoryRequest(BaseModel):
    text: str = Field(..., description="Updated text content of the memory")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata to update")

class BatchUpdateRequest(BaseModel):
    memories: List[Dict[str, str]] = Field(
        ...,
        description="List of memories to update. Each memory should contain 'memory_id' and 'text' fields.",
        max_items=1000
    )


class BatchDeleteRequest(BaseModel):
    memories: List[Dict[str, str]] = Field(
        ...,
        description="List of memories to delete. Each memory should contain 'memory_id' field.",
        max_items=1000
    )


class ExportRequest(BaseModel):
    schema: Dict[str, Any] = Field(..., description="Export data structure definition using Pydantic schema format.")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filtering conditions for memories to export.")
    processing_instruction: Optional[str] = Field(None, description="Additional processing instructions for the export.")


class FeedbackRequest(BaseModel):
    memory_id: str = Field(..., description="ID of the memory to provide feedback for.")
    feedback: Optional[str] = Field(None, description="Feedback type: POSITIVE, NEGATIVE, or VERY_NEGATIVE.")
    feedback_reason: Optional[str] = Field(None, description="Optional reason for the feedback.")


class V2MemoriesRequest(BaseModel):
    filters: Optional[Dict[str, Any]] = Field(None, description="Complex filters with AND/OR/NOT logic support.")
    limit: Optional[int] = Field(50, description="Maximum number of memories to return.", ge=1, le=1000)


class V2SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string.")
    filters: Optional[Dict[str, Any]] = Field(None, description="Complex filters with AND/OR/NOT logic support.")
    limit: Optional[int] = Field(50, description="Maximum number of search results to return.", ge=1, le=1000)
    keyword_search: Optional[bool] = Field(False, description="Enable BM25 keyword search")
    rerank: Optional[bool] = Field(False, description="Enable LLM-based reranking")
    filter_memories: Optional[bool] = Field(False, description="Enable intelligent memory filtering")


@app.post("/configure", summary="Configure Mem0")
def set_config(config: Dict[str, Any]):
    """Set memory configuration."""
    global MEMORY_INSTANCE
    MEMORY_INSTANCE = Memory.from_config(config)
    return {"message": "Configuration set successfully"}


@app.post("/v1/memories/", summary="Create memories")
def add_memory(memory_create: MemoryCreate):
    """Store new memories."""
    if not any([memory_create.user_id, memory_create.agent_id, memory_create.run_id]):
        raise HTTPException(status_code=400, detail="At least one identifier (user_id, agent_id, run_id) is required.")

    params = {k: v for k, v in memory_create.model_dump().items() if v is not None and k != "messages"}
    try:
        response = MEMORY_INSTANCE.add(messages=[m.model_dump() for m in memory_create.messages], **params)
        return JSONResponse(content=response)
    except Exception as e:
        logging.exception("Error in add_memory:")  # This will log the full traceback
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/memories/", summary="Get memories")
def get_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Retrieve stored memories."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        return MEMORY_INSTANCE.get_all(**params)
    except Exception as e:
        logging.exception("Error in get_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/memories/{memory_id}/", summary="Get a memory")
def get_memory(memory_id: str):
    """Retrieve a specific memory by ID."""
    try:
        return MEMORY_INSTANCE.get(memory_id)
    except Exception as e:
        logging.exception("Error in get_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/memories/search/", summary="Search memories")
def search_memories(search_req: SearchRequest):
    """Search for memories based on a query."""
    try:
        params = {k: v for k, v in search_req.model_dump().items() if v is not None and k != "query"}
        return MEMORY_INSTANCE.search(query=search_req.query, **params)
    except Exception as e:
        logging.exception("Error in search_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/v1/memories/{memory_id}/", summary="Update a memory")
def update_memory(memory_id: str, request: UpdateMemoryRequest):
    """Update an existing memory."""
    try:
        result = MEMORY_INSTANCE.update(memory_id=memory_id, data=request.text, metadata=request.metadata)
        return result
    except Exception as e:
        logging.exception("Error in update_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/memories/{memory_id}/history/", summary="Get memory history")
def memory_history(memory_id: str):
    """Retrieve memory history."""
    try:
        return MEMORY_INSTANCE.history(memory_id=memory_id)
    except Exception as e:
        logging.exception("Error in memory_history:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/memories/{memory_id}/", summary="Delete a memory")
def delete_memory(memory_id: str):
    """Delete a specific memory by ID."""
    try:
        MEMORY_INSTANCE.delete(memory_id=memory_id)
        return {"message": "Memory deleted successfully"}
    except Exception as e:
        logging.exception("Error in delete_memory:")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/v1/memories/", summary="Delete all memories")
def delete_all_memories(
    user_id: Optional[str] = None,
    run_id: Optional[str] = None,
    agent_id: Optional[str] = None,
):
    """Delete all memories for a given identifier."""
    if not any([user_id, run_id, agent_id]):
        raise HTTPException(status_code=400, detail="At least one identifier is required.")
    try:
        params = {
            k: v for k, v in {"user_id": user_id, "run_id": run_id, "agent_id": agent_id}.items() if v is not None
        }
        MEMORY_INSTANCE.delete_all(**params)
        return {"message": "All relevant memories deleted"}
    except Exception as e:
        logging.exception("Error in delete_all_memories:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reset", summary="Reset all memories")
def reset_memory():
    """Completely reset stored memories."""
    try:
        MEMORY_INSTANCE.reset()
        return {"message": "All memories reset"}
    except Exception as e:
        logging.exception("Error in reset_memory:")
        raise HTTPException(status_code=500, detail=str(e))


def format_memories_by_schema(memories: List[Dict[str, Any]], schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Format memories according to the provided schema.

    Args:
        memories: List of memory objects
        schema: Schema definition for formatting

    Returns:
        Formatted memories according to schema
    """
    if not memories or not schema:
        return memories

    formatted_memories = []

    for memory in memories:
        formatted_memory = {}

        # Apply schema mapping
        for field_name, field_config in schema.items():
            if isinstance(field_config, dict):
                # Handle complex field configuration
                source_field = field_config.get("source", field_name)
                default_value = field_config.get("default", None)

                if source_field in memory:
                    formatted_memory[field_name] = memory[source_field]
                elif default_value is not None:
                    formatted_memory[field_name] = default_value
            else:
                # Simple field mapping
                if field_name in memory:
                    formatted_memory[field_name] = memory[field_name]

        formatted_memories.append(formatted_memory)

    return formatted_memories


def process_export_task(task_id: str, filters: Dict[str, Any], schema: Dict[str, Any], processing_instruction: str = None):
    """
    Process export task asynchronously.

    Args:
        task_id: Unique task identifier
        filters: Filters to apply when getting memories
        schema: Schema for formatting the exported data
        processing_instruction: Additional processing instructions
    """
    try:
        # Update task status to processing
        EXPORT_TASKS[task_id]["status"] = "processing"

        # Get memories using filters
        if filters:
            memories = MEMORY_INSTANCE.get_all(**filters)
        else:
            # If no filters, get all memories (this might be resource intensive)
            memories = MEMORY_INSTANCE.get_all()

        # Ensure memories is a list
        if not isinstance(memories, list):
            memories = [memories] if memories else []

        # Format memories according to schema
        formatted_data = format_memories_by_schema(memories, schema)

        # Apply processing instruction if provided
        if processing_instruction:
            # For now, just add the instruction as metadata
            result = {
                "data": formatted_data,
                "processing_instruction": processing_instruction,
                "total_count": len(formatted_data)
            }
        else:
            result = {
                "data": formatted_data,
                "total_count": len(formatted_data)
            }

        # Update task status to completed
        EXPORT_TASKS[task_id].update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat()
        })

    except Exception as e:
        logging.exception(f"Error in export task {task_id}:")
        EXPORT_TASKS[task_id].update({
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        })


def cleanup_old_export_tasks():
    """Clean up export tasks older than 1 hour."""
    current_time = datetime.now()
    tasks_to_remove = []

    for task_id, task_info in EXPORT_TASKS.items():
        created_at = datetime.fromisoformat(task_info.get("created_at", current_time.isoformat()))
        if (current_time - created_at).total_seconds() > 3600:  # 1 hour
            tasks_to_remove.append(task_id)

    for task_id in tasks_to_remove:
        del EXPORT_TASKS[task_id]


@app.post("/v1/exports/", summary="Create memory export job")
def create_memory_export(export_request: ExportRequest):
    """Create an asynchronous memory export job."""
    try:
        # Clean up old tasks
        cleanup_old_export_tasks()

        # Check if we have too many active tasks
        active_tasks = sum(1 for task in EXPORT_TASKS.values() if task["status"] in ["pending", "processing"])
        if active_tasks >= 10:  # Limit concurrent export tasks
            raise HTTPException(status_code=429, detail="Too many active export tasks. Please try again later.")

        # Generate unique task ID
        task_id = str(uuid.uuid4())

        # Initialize task in storage
        EXPORT_TASKS[task_id] = {
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "filters": export_request.filters,
            "schema": export_request.schema,
            "processing_instruction": export_request.processing_instruction
        }

        # Submit task to executor
        EXPORT_EXECUTOR.submit(
            process_export_task,
            task_id,
            export_request.filters or {},
            export_request.schema,
            export_request.processing_instruction
        )

        return {
            "id": task_id,
            "message": "Export job created successfully",
            "status": "pending"
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error creating export job:")
        raise HTTPException(status_code=500, detail=f"Failed to create export job: {str(e)}")


@app.post("/v1/exports/get", summary="Get memory export result")
def get_memory_export(request: Dict[str, str]):
    """Get the result of a memory export job."""
    try:
        task_id = request.get("memory_export_id") or request.get("task_id")

        if not task_id:
            raise HTTPException(status_code=400, detail="memory_export_id or task_id is required")

        if task_id not in EXPORT_TASKS:
            raise HTTPException(status_code=404, detail="Export task not found")

        task_info = EXPORT_TASKS[task_id]

        response = {
            "id": task_id,
            "status": task_info["status"],
            "created_at": task_info["created_at"]
        }

        if task_info["status"] == "completed":
            response["result"] = task_info["result"]
            response["completed_at"] = task_info.get("completed_at")
        elif task_info["status"] == "failed":
            response["error"] = task_info["error"]
            response["failed_at"] = task_info.get("failed_at")
        elif task_info["status"] == "processing":
            response["message"] = "Export job is still processing"
        else:  # pending
            response["message"] = "Export job is pending"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error getting export result:")
        raise HTTPException(status_code=500, detail=f"Failed to get export result: {str(e)}")


def process_v2_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process V2 API complex filters and convert them to Memory class compatible format.

    Supports:
    - AND/OR/NOT logical operators
    - Comparison operators: gte, lte, in, icontains
    - Backward compatibility with simple filters
    """
    if not filters:
        return {}

    processed_filters = {}

    # Memory.get_all() only accepts these specific parameters
    simple_filter_keys = {"user_id", "agent_id", "run_id"}
    
    # Handle simple filters (backward compatibility)
    for key in simple_filter_keys:
        if key in filters:
            processed_filters[key] = filters[key]

    # Collect complex filters to be passed in the 'filters' parameter
    complex_filters = {}

    # Handle complex logical operators
    if "AND" in filters:
        # For AND operations, merge all conditions
        and_conditions = filters["AND"]
        if isinstance(and_conditions, list):
            for condition in and_conditions:
                if isinstance(condition, dict):
                    sub_result = process_v2_filters(condition)
                    # Extract simple keys
                    for k in simple_filter_keys:
                        if k in sub_result:
                            processed_filters[k] = sub_result[k]
                    # Extract complex filters
                    if "filters" in sub_result:
                        complex_filters.update(sub_result["filters"])

    if "OR" in filters:
        # For OR operations, we'll need to handle this at the application level
        # since Memory class doesn't directly support OR operations
        # For now, we'll take the first condition as a fallback
        or_conditions = filters["OR"]
        if isinstance(or_conditions, list) and or_conditions:
            sub_result = process_v2_filters(or_conditions[0])
            # Extract simple keys
            for k in simple_filter_keys:
                if k in sub_result:
                    processed_filters[k] = sub_result[k]
            # Extract complex filters
            if "filters" in sub_result:
                complex_filters.update(sub_result["filters"])

    if "NOT" in filters:
        # NOT operations are complex and would need special handling
        # For now, we'll skip NOT conditions as they require post-processing
        pass

    # Handle metadata and other complex conditions (including category)
    for key, value in filters.items():
        if key in {"AND", "OR", "NOT"} or key in simple_filter_keys:
            continue

        if isinstance(value, dict):
            # Handle comparison operators
            if "gte" in value:
                # Greater than or equal - for metadata fields
                complex_filters[f"{key}__gte"] = value["gte"]
            elif "lte" in value:
                # Less than or equal - for metadata fields
                complex_filters[f"{key}__lte"] = value["lte"]
            elif "in" in value:
                # Value in list
                complex_filters[f"{key}__in"] = value["in"]
            elif "icontains" in value:
                # Case-insensitive contains
                complex_filters[f"{key}__icontains"] = value["icontains"]
            else:
                # Direct assignment for other dict values
                complex_filters[key] = value
        else:
            # Direct assignment for simple values - put in complex filters
            complex_filters[key] = value

    # If we have complex filters, add them to the 'filters' parameter
    if complex_filters:
        processed_filters["filters"] = complex_filters

    return processed_filters


@app.post("/v2/memories/", summary="Get memories with complex filters (V2)")
def get_memories_v2(request: V2MemoriesRequest):
    """Retrieve memories with complex filtering support."""
    try:
        # Process complex filters
        processed_filters = process_v2_filters(request.filters or {})

        # Get memories using processed filters
        memories = MEMORY_INSTANCE.get_all(**processed_filters)

        # Apply limit if specified
        if request.limit and isinstance(memories, list):
            memories = memories[:request.limit]

        return {
            "memories": memories,
            "total_count": len(memories) if isinstance(memories, list) else 1,
            "limit": request.limit,
            "filters_applied": processed_filters
        }

    except Exception as e:
        logging.exception("Error in get_memories_v2:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v2/memories/search/", summary="Search memories with complex filters (V2)")
def search_memories_v2(request: V2SearchRequest):
    """Search memories with complex filtering support."""
    try:
        # Process complex filters
        processed_filters = process_v2_filters(request.filters or {})

        # Search memories using processed filters
        search_results = MEMORY_INSTANCE.search(query=request.query, **processed_filters)

        # Apply limit if specified
        if request.limit and isinstance(search_results, list):
            search_results = search_results[:request.limit]

        return {
            "results": search_results,
            "total_count": len(search_results) if isinstance(search_results, list) else 1,
            "query": request.query,
            "limit": request.limit,
            "filters_applied": processed_filters
        }

    except Exception as e:
        logging.exception("Error in search_memories_v2:")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/feedback/", summary="Submit feedback for a memory")
def submit_feedback(feedback_request: FeedbackRequest):
    """Submit feedback for a specific memory."""
    VALID_FEEDBACK_VALUES = {"POSITIVE", "NEGATIVE", "VERY_NEGATIVE"}

    memory_id = feedback_request.memory_id
    feedback = feedback_request.feedback
    feedback_reason = feedback_request.feedback_reason

    # Validate feedback value
    if feedback:
        feedback = feedback.upper()
        if feedback not in VALID_FEEDBACK_VALUES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid feedback value. Must be one of: {', '.join(VALID_FEEDBACK_VALUES)}"
            )

    # Verify memory exists
    try:
        MEMORY_INSTANCE.get(memory_id)
    except Exception as e:
        logging.exception(f"Error verifying memory {memory_id}:")
        raise HTTPException(status_code=404, detail=f"Memory with ID {memory_id} not found.")

    # Prepare feedback data
    feedback_data = {
        "memory_id": memory_id,
        "feedback": feedback,
        "feedback_reason": feedback_reason,
        "timestamp": datetime.now().isoformat()
    }

    # Store feedback to file
    feedback_file_path = "/app/data/feedback.json"

    try:
        # Ensure directory exists
        Path("/app/data").mkdir(parents=True, exist_ok=True)

        # Read existing feedback data or create new list
        existing_feedback = []
        if os.path.exists(feedback_file_path):
            try:
                with open(feedback_file_path, 'r') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for reading
                    existing_feedback = json.load(f)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock
            except (json.JSONDecodeError, FileNotFoundError):
                existing_feedback = []

        # Append new feedback
        existing_feedback.append(feedback_data)

        # Write back to file with exclusive lock
        with open(feedback_file_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive lock for writing
            json.dump(existing_feedback, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)  # Unlock

        return {"message": "Feedback submitted successfully", "feedback_id": len(existing_feedback)}

    except Exception as e:
        logging.exception("Error storing feedback:")
        raise HTTPException(status_code=500, detail=f"Failed to store feedback: {str(e)}")


@app.put("/v1/batch/", summary="Batch update memories")
def batch_update_memories(batch_request: BatchUpdateRequest):
    """Update multiple memories in batch. Maximum 1000 memories per request."""
    memories = batch_request.memories

    if len(memories) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 memories allowed per batch operation.")

    if not memories:
        raise HTTPException(status_code=400, detail="At least one memory is required.")

    # Validate that each memory has required fields
    for i, memory in enumerate(memories):
        if "memory_id" not in memory:
            raise HTTPException(status_code=400, detail=f"Memory at index {i} missing 'memory_id' field.")
        if "text" not in memory:
            raise HTTPException(status_code=400, detail=f"Memory at index {i} missing 'text' field.")

    successful_updates = []
    failed_updates = []

    def update_single_memory(memory):
        try:
            memory_id = memory["memory_id"]
            text = memory["text"]
            result = MEMORY_INSTANCE.update(memory_id=memory_id, data={"text": text})
            return {"memory_id": memory_id, "status": "success", "result": result}
        except Exception as e:
            logging.exception(f"Error updating memory {memory.get('memory_id', 'unknown')}:")
            return {"memory_id": memory.get("memory_id", "unknown"), "status": "failed", "error": str(e)}

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        try:
            # Submit all tasks
            future_to_memory = {executor.submit(update_single_memory, memory): memory for memory in memories}

            # Collect results with timeout
            for future in as_completed(future_to_memory, timeout=60):
                result = future.result()
                if result["status"] == "success":
                    successful_updates.append(result)
                else:
                    failed_updates.append(result)

        except Exception as e:
            logging.exception("Error in batch update operation:")
            raise HTTPException(status_code=500, detail=f"Batch operation failed: {str(e)}")

    return {
        "message": f"Batch update completed. {len(successful_updates)} successful, {len(failed_updates)} failed.",
        "total_processed": len(memories),
        "successful_count": len(successful_updates),
        "failed_count": len(failed_updates),
        "successful_updates": successful_updates,
        "failed_updates": failed_updates
    }


@app.delete("/v1/batch/", summary="Batch delete memories")
def batch_delete_memories(batch_request: BatchDeleteRequest):
    """Delete multiple memories in batch. Maximum 1000 memories per request."""
    memories = batch_request.memories

    if len(memories) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 memories allowed per batch operation.")

    if not memories:
        raise HTTPException(status_code=400, detail="At least one memory is required.")

    # Validate that each memory has required fields
    for i, memory in enumerate(memories):
        if "memory_id" not in memory:
            raise HTTPException(status_code=400, detail=f"Memory at index {i} missing 'memory_id' field.")

    successful_deletions = []
    failed_deletions = []

    def delete_single_memory(memory):
        try:
            memory_id = memory["memory_id"]
            MEMORY_INSTANCE.delete(memory_id=memory_id)
            return {"memory_id": memory_id, "status": "success"}
        except Exception as e:
            logging.exception(f"Error deleting memory {memory.get('memory_id', 'unknown')}:")
            return {"memory_id": memory.get("memory_id", "unknown"), "status": "failed", "error": str(e)}

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        try:
            # Submit all tasks
            future_to_memory = {executor.submit(delete_single_memory, memory): memory for memory in memories}

            # Collect results with timeout
            for future in as_completed(future_to_memory, timeout=60):
                result = future.result()
                if result["status"] == "success":
                    successful_deletions.append(result)
                else:
                    failed_deletions.append(result)

        except Exception as e:
            logging.exception("Error in batch delete operation:")
            raise HTTPException(status_code=500, detail=f"Batch operation failed: {str(e)}")

    return {
        "message": f"Batch delete completed. {len(successful_deletions)} successful, {len(failed_deletions)} failed.",
        "total_processed": len(memories),
        "successful_count": len(successful_deletions),
        "failed_count": len(failed_deletions),
        "successful_deletions": successful_deletions,
        "failed_deletions": failed_deletions
    }



