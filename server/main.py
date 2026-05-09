import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func, select

from auth import ADMIN_API_KEY, AUTH_DISABLED, JWT_SECRET, verify_auth
from errors import (
    UpstreamError,
    install_request_id_logging,
    new_request_id,
    request_id_var,
    upstream_error,
    upstream_error_handler,
)
from rate_limit import limiter
from db import SessionLocal
from models import Event, RequestLog, User
import telemetry
from routers import auth as auth_router
from routers import api_keys as api_keys_router
from routers import entities as entities_router
from routers import projects as projects_router
from routers import requests as requests_router
from schemas import MessageResponse
from server_state import (
    ProjectFieldsRejected,
    get_current_config,
    get_memory_instance,
    initialize_state,
    set_session_factory,
    update_config,
)

load_dotenv()

install_request_id_logging()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - [%(request_id)s] %(message)s")

MIN_KEY_LENGTH = 16
SENSITIVE_CONFIG_KEYS = {
    "admin_api_key",
    "api_key",
    "authorization",
    "jwt_secret",
    "password",
    "password_hash",
    "secret",
    "token",
}
SKIPPED_REQUEST_LOG_PATHS = {"/api/health", "/docs", "/redoc", "/openapi.json"}
SKIPPED_REQUEST_LOG_PREFIXES = ("/requests",)

BUNDLED_LLM_PROVIDERS = ("openai", "anthropic", "gemini")
BUNDLED_EMBEDDER_PROVIDERS = ("openai", "gemini")


def _warn_if_unconfigured() -> None:
    """Pre-auth deployments upgrading into this build will 401 everywhere until
    an admin key or admin user exists. Surface the fix before the support tickets."""
    try:
        with SessionLocal() as session:
            if session.scalar(select(func.count(User.id))) > 0:
                return
    except Exception:
        return

    logging.warning(
        "\n%s\n"
        "  Auth is enabled by default and this server has no admin configured.\n"
        "  Protected endpoints will return 401 until you either:\n"
        "    1. Set ADMIN_API_KEY=<long-random-value>  (fastest, no client changes)\n"
        "    2. Register an admin at http://<host>:3000/setup\n"
        "    3. Set AUTH_DISABLED=true                 (local development only)\n"
        "  Docs: https://docs.mem0.ai/open-source/features/rest-api#authentication\n"
        "%s",
        "=" * 72,
        "=" * 72,
    )


if not AUTH_DISABLED and not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET is required. Set it in .env (generate with `openssl rand -base64 48`) "
        "or set AUTH_DISABLED=true for local development only."
    )

if AUTH_DISABLED:
    logging.warning("AUTH_DISABLED is enabled. Protected endpoints are open for local development only.")
elif ADMIN_API_KEY and len(ADMIN_API_KEY) < MIN_KEY_LENGTH:
    logging.warning(
        "ADMIN_API_KEY is shorter than %d characters - consider using a longer key for production.",
        MIN_KEY_LENGTH,
    )
elif not ADMIN_API_KEY:
    _warn_if_unconfigured()

telemetry.log_status()

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_COLLECTION_NAME = os.environ.get("POSTGRES_COLLECTION_NAME", "memories")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/history/history.db")
DEFAULT_LLM_MODEL = os.environ.get("MEM0_DEFAULT_LLM_MODEL", "gpt-4.1-nano-2025-04-14")
DEFAULT_EMBEDDER_MODEL = os.environ.get("MEM0_DEFAULT_EMBEDDER_MODEL", "text-embedding-3-small")

DEFAULT_CONFIG = {
    "version": "v1.1",
    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": POSTGRES_HOST,
            "port": int(POSTGRES_PORT),
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "collection_name": POSTGRES_COLLECTION_NAME,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {"api_key": OPENAI_API_KEY, "temperature": 0.2, "model": DEFAULT_LLM_MODEL},
    },
    "embedder": {"provider": "openai", "config": {"api_key": OPENAI_API_KEY, "model": DEFAULT_EMBEDDER_MODEL}},
    "history_db_path": HISTORY_DB_PATH,
}


set_session_factory(SessionLocal)
initialize_state(DEFAULT_CONFIG)


app = FastAPI(
    title="Mem0 REST APIs",
    description=(
        "A REST API for managing and searching memories for your AI Agents and Apps.\n\n"
        "## Authentication\n"
        "Supports Bearer JWT tokens, per-user API keys via `X-API-Key` header, "
        "or the legacy `ADMIN_API_KEY` environment variable. Set `AUTH_DISABLED=true` for local development only."
    ),
    version="1.0.0",
    redirect_slashes=False,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(UpstreamError, upstream_error_handler)
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[DASHBOARD_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(api_keys_router.router)
app.include_router(entities_router.router)
app.include_router(projects_router.router)
app.include_router(requests_router.router)


class Message(BaseModel):
    role: str = Field(..., description="Role of the message (user or assistant).")
    content: Union[str, Dict[str, Any], List[Any]] = Field(
        ...,
        description=(
            "Message content. Plain string for normal messages, or a dict "
            "(``{type: image_url|mdx_url|pdf_url, ...}``) for multimodal "
            "payloads. See docs/platform/features/multimodal-support.mdx."
        ),
    )
    name: Optional[str] = Field(
        None,
        description=(
            "Optional speaker name for group-chat scenarios. When set, the "
            "speaker's memories are partitioned: ``user`` names land as "
            "``user_id`` and ``assistant``/``agent`` names land as "
            "``agent_id``. See docs/platform/features/group-chat.mdx."
        ),
    )


class MemoryCreate(BaseModel):
    messages: List[Message] = Field(..., description="List of messages to store.")
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    run_id: Optional[str] = None
    app_id: Optional[str] = Field(None, description="Application identifier for tenant/app scoping.")
    metadata: Optional[Dict[str, Any]] = None
    infer: Optional[bool] = Field(None, description="Whether to extract facts from messages. Defaults to True.")
    timestamp: Optional[int] = Field(
        None,
        description=(
            "Optional Unix timestamp (seconds since epoch) to backdate the "
            "created_at of memories produced by this call. Use for historical "
            "imports. See docs/platform/features/timestamp.mdx."
        ),
    )
    memory_type: Optional[str] = Field(None, description="Type of memory to store (e.g. 'core').")
    prompt: Optional[str] = Field(None, description="Custom prompt to use for fact extraction.")


class MemoryUpdate(BaseModel):
    text: str = Field(..., description="New content to update the memory with.")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata to update.")


class ListBody(BaseModel):
    """Body for `POST /memories/list` — v2 filter dict + pagination."""
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="v2 filter dict (AND/OR/NOT, eq/ne/in/nin/gt/gte/lt/lte/contains/icontains, '*'). "
        "Empty means list all (admin operation, may be capped by top_k).",
    )
    top_k: Optional[int] = Field(None, description="Maximum number of results to return.")


class SearchBody(BaseModel):
    """Body for `POST /memories/search` — v2 filter dict + reranking."""
    query: str = Field(..., description="Search query.")
    filters: Optional[Dict[str, Any]] = Field(None, description="v2 filter dict.")
    top_k: Optional[int] = Field(None, description="Maximum number of results to return.")
    threshold: Optional[float] = Field(None, description="Minimum similarity score for results.")
    rerank: Optional[bool] = Field(
        None, description="Apply reranker if configured. Defaults to False."
    )
    use_criteria: Optional[bool] = Field(
        None,
        description=(
            "Whether to apply criteria-based scoring. Defaults to None — auto-enabled when "
            "project criteria are configured. Pass false to opt out for this call."
        ),
    )
    criteria: Optional[list] = Field(
        None,
        description=(
            "Per-call override of project-level criteria. List of "
            "{name, description, weight?} dicts."
        ),
    )


class DeleteBody(BaseModel):
    """Body for `POST /memories/delete` — bulk delete by v2 filter dict."""
    filters: Dict[str, Any] = Field(
        ..., description="v2 filter dict scoping the memories to delete. Required."
    )


class GenerateInstructionsRequest(BaseModel):
    use_case: str = Field(..., description="Description of what the user will use Mem0 for.")


class FeedbackBody(BaseModel):
    """Body for ``POST /memories/{memory_id}/feedback``.

    Mirrors the platform feedback contract. Pass ``feedback=None`` and
    ``feedback_reason=None`` to clear existing feedback for the memory.
    """
    feedback: Optional[str] = Field(
        None,
        description="One of POSITIVE, NEGATIVE, VERY_NEGATIVE (case-insensitive), or None to clear.",
    )
    feedback_reason: Optional[str] = Field(
        None, description="Optional explanation for the feedback."
    )


def _redact_config(value: Any, key: str | None = None) -> Any:
    if isinstance(value, dict):
        return {item_key: _redact_config(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_config(item_value, key) for item_value in value]
    if key is not None and key.lower() in SENSITIVE_CONFIG_KEYS:
        return "[redacted]" if value else value
    return value


def _validate_bundled_providers(config: Dict[str, Any]) -> None:
    llm = config.get("llm")
    if isinstance(llm, dict) and (provider := llm.get("provider")) and provider not in BUNDLED_LLM_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"LLM provider '{provider}' is not bundled in this image. "
                f"Bundled providers: {', '.join(BUNDLED_LLM_PROVIDERS)}. "
                "To use another provider, install its Python package, rebuild the container, "
                "and extend BUNDLED_LLM_PROVIDERS in server/main.py."
            ),
        )

    embedder = config.get("embedder")
    if (
        isinstance(embedder, dict)
        and (provider := embedder.get("provider"))
        and provider not in BUNDLED_EMBEDDER_PROVIDERS
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Embedder provider '{provider}' is not bundled in this image. "
                f"Bundled providers: {', '.join(BUNDLED_EMBEDDER_PROVIDERS)}. "
                "To use another provider, install its Python package, rebuild the container, "
                "and extend BUNDLED_EMBEDDER_PROVIDERS in server/main.py."
            ),
        )


def _should_log_request(request: Request) -> bool:
    if request.method == "OPTIONS":
        return False
    path = request.url.path
    if path in SKIPPED_REQUEST_LOG_PATHS:
        return False
    return not path.startswith(SKIPPED_REQUEST_LOG_PREFIXES)


def _persist_request_log(method: str, path: str, status_code: int, latency_ms: float, auth_type: str) -> None:
    session = SessionLocal()

    try:
        session.add(
            RequestLog(
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=latency_ms,
                auth_type=auth_type,
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        logging.exception("Failed to persist request log")
    finally:
        session.close()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request.state.auth_type = getattr(request.state, "auth_type", "none")
    rid = new_request_id()
    token = request_id_var.set(rid)
    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = rid
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        request_id_var.reset(token)
        if _should_log_request(request):
            asyncio.get_running_loop().run_in_executor(
                None,
                _persist_request_log,
                request.method,
                request.url.path,
                status_code,
                round((time.perf_counter() - start) * 1000, 2),
                getattr(request.state, "auth_type", "none"),
            )


@app.get("/configure", summary="Get current Mem0 configuration")
def get_config(_auth=Depends(verify_auth)):
    return _redact_config(get_current_config())


@app.get("/configure/providers", summary="List bundled LLM and embedder providers")
def list_bundled_providers(_auth=Depends(verify_auth)):
    return {"llm": list(BUNDLED_LLM_PROVIDERS), "embedder": list(BUNDLED_EMBEDDER_PROVIDERS)}


@app.post("/configure", summary="Configure Mem0")
def set_config(config: Dict[str, Any], _auth=Depends(verify_auth)):
    """Set memory configuration.

    Project-scoped fields (``retrieval_criteria``, ``custom_instructions``,
    ``custom_categories``, ``multilingual``, ``decay``) are rejected here —
    use ``PATCH /project`` instead.
    """
    _validate_bundled_providers(config)
    try:
        update_config(config)
    except ProjectFieldsRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": "Configuration set successfully"}


@app.post("/generate-instructions", summary="Generate custom instructions from a use case")
def generate_instructions(req: GenerateInstructionsRequest, _auth=Depends(verify_auth)):
    """Generate custom instructions and a contextual test message tailored to a use case."""
    try:
        llm = get_memory_instance().llm
        prompt = (
            "You are configuring a memory system. Given the use case below, produce two things:\n"
            "1. INSTRUCTIONS: A short paragraph of custom instructions telling the memory extraction system "
            "what kinds of facts, preferences, and context to prioritize. Be specific to the use case.\n"
            "2. TEST_MESSAGE: A single realistic sentence a user in this use case would say, suitable for "
            "testing that the memory system works.\n\n"
            "Respond in exactly this format (no markdown, no extra text):\n"
            "INSTRUCTIONS: <your instructions>\n"
            f"TEST_MESSAGE: <your test message>\n\nUse case: {req.use_case}"
        )
        response = llm.generate_response([{"role": "user", "content": prompt}])
        instructions = response
        test_message = "I like to hike on weekends."
        if "INSTRUCTIONS:" in response and "TEST_MESSAGE:" in response:
            parts = response.split("TEST_MESSAGE:")
            instructions = parts[0].replace("INSTRUCTIONS:", "").strip()
            test_message = parts[1].strip()
        return {"custom_instructions": instructions, "test_message": test_message}
    except Exception:
        raise upstream_error()


@app.post("/v3/memories/add/", summary="Add memories (async, returns event_id)")
def add_memory_v3(
    memory_create: MemoryCreate,
    background_tasks: BackgroundTasks,
    _auth=Depends(verify_auth),
):
    """Queue a memory add for background extraction. Returns ``event_id``
    that clients poll via ``GET /v1/event/{event_id}/`` until status is
    SUCCEEDED or FAILED."""
    if not _has_entity_scope_top_level(memory_create):
        raise HTTPException(
            status_code=400,
            detail="At least one identifier (user_id, agent_id, run_id, app_id) is required.",
        )

    payload = memory_create.model_dump(exclude_none=True)
    with SessionLocal() as s:
        ev = Event(status="PENDING", payload=payload)
        s.add(ev)
        s.commit()
        s.refresh(ev)
        event_id = ev.id

    background_tasks.add_task(_run_add_event, event_id)
    return {
        "message": "Memory processing has been queued for background execution",
        "status": "PENDING",
        "event_id": str(event_id),
    }


def _run_add_event(event_id: uuid.UUID) -> None:
    """Background worker. Runs after the HTTP response is sent. Owns its own
    DB session because the request session is already closed."""
    with SessionLocal() as s:
        ev = s.get(Event, event_id)
        if ev is None or ev.status != "PENDING":
            return
        try:
            payload = dict(ev.payload)            # don't mutate the JSON column
            messages = payload.pop("messages", [])
            result = get_memory_instance().add(messages=messages, **payload)
            ev.result = result
            ev.status = "SUCCEEDED"
        except Exception as exc:
            logging.exception("V3 add background task failed for event %s", event_id)
            ev.error = str(exc)
            ev.status = "FAILED"
        finally:
            s.commit()


ALL_MEMORIES_LIMIT = 1000
_RESERVED_PAYLOAD_KEYS = {"data", "user_id", "agent_id", "run_id", "app_id", "hash", "created_at", "updated_at"}


def _serialize_memory(row: Any) -> Dict[str, Any]:
    payload = getattr(row, "payload", None) or {}
    return {
        "id": getattr(row, "id", None),
        "memory": payload.get("data"),
        "user_id": payload.get("user_id"),
        "agent_id": payload.get("agent_id"),
        "run_id": payload.get("run_id"),
        "app_id": payload.get("app_id"),
        "hash": payload.get("hash"),
        "metadata": {k: v for k, v in payload.items() if k not in _RESERVED_PAYLOAD_KEYS},
        "created_at": payload.get("created_at"),
        "updated_at": payload.get("updated_at"),
    }


def _flatten_vector_store_list_result(result: Any) -> list:
    """Adapter for vector_store.list() returns.

    Vector-store backends differ on the return shape. Today we may receive:
      - ``{"results": [...], "count": N}`` (new dict shape, pgvector after V3)
      - ``{"results": [[OutputData, ...]], "count": N}`` (pgvector wraps once
        more to preserve legacy ``[0]`` indexing)
      - ``[[OutputData, ...]]`` (legacy nested list)
      - ``(rows, ...)`` (legacy tuple, e.g. some test mocks)
      - ``[OutputData, ...]`` (legacy flat list)

    Returns a flat list of ``OutputData`` rows in every case.

    Used by ``_list_all_memories`` and ``routers.entities._iter_payloads`` so
    we don't maintain two parallel copies of the shape-sniffing logic.
    """
    if isinstance(result, dict) and "results" in result:
        rows = result["results"]
        if isinstance(rows, list) and rows and isinstance(rows[0], list):
            return rows[0]
        return rows or []
    if isinstance(result, tuple) and result:
        result = result[0]
    if isinstance(result, list) and result and isinstance(result[0], list):
        return result[0]
    return result or []


_ENTITY_KEYS = ("user_id", "agent_id", "run_id", "app_id")


def _has_entity_scope_top_level(req: "MemoryCreate") -> bool:
    """True iff the create request carries at least one entity ID at the top level."""
    return any(getattr(req, k, None) for k in _ENTITY_KEYS)


def _require_entity_scope(filters: Dict[str, Any]) -> None:
    """Raise 400 unless ``filters`` contains at least one positively-scoped
    entity ID. Mirrors mem0/memory/main.py:_filter_has_entity_scope but
    surfaces an HTTP 400 with a clear message instead of a 500."""

    def _walk(node: Any) -> bool:
        if isinstance(node, dict):
            for k, v in node.items():
                if k in _ENTITY_KEYS and v not in (None, "", []):
                    return True
                if k in ("AND", "OR") and isinstance(v, list):
                    if any(_walk(x) for x in v):
                        return True
        elif isinstance(node, list):
            return any(_walk(x) for x in node)
        return False

    if not filters or not _walk(filters):
        raise HTTPException(
            status_code=400,
            detail=(
                "filters must contain at least one of: user_id, agent_id, run_id, app_id. "
                "Example: filters={'user_id': 'u1'}"
            ),
        )


def _build_page_url(request: Request, page: int, page_size: int) -> str:
    """Absolute URL for the given page using the current request's host + path."""
    base = str(request.base_url).rstrip("/")
    qs = urlencode({"page": page, "page_size": page_size})
    return f"{base}{request.url.path}?{qs}"


def _list_all_memories(limit: int = ALL_MEMORIES_LIMIT) -> Dict[str, Any]:
    results = get_memory_instance().vector_store.list(top_k=limit)
    rows = _flatten_vector_store_list_result(results)
    return {"results": [_serialize_memory(row) for row in rows]}


@app.post("/memories/list", summary="List memories with v2 filters")
def list_memories(body: ListBody, _auth=Depends(verify_auth)):
    """
    List memories matching a v2 filter dict.

    Empty filters list everything (capped by `top_k`, defaulting to 1000) — useful
    for admin workflows. For scoped queries, pass an entity-id filter or wildcards
    (e.g. ``{"user_id": "*"}`` to list across all users).
    """
    try:
        filters = body.filters or {}
        limit = body.top_k or ALL_MEMORIES_LIMIT
        if not filters:
            return _list_all_memories(limit)
        return get_memory_instance().get_all(filters=filters, top_k=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise upstream_error()


@app.get("/memories/{memory_id}", summary="Get a memory")
def get_memory(memory_id: str, _auth=Depends(verify_auth)):
    """Retrieve a specific memory by ID."""
    try:
        return get_memory_instance().get(memory_id)
    except Exception:
        raise upstream_error()


@app.post("/memories/search", summary="Search memories")
def search_memories(body: SearchBody, _auth=Depends(verify_auth)):
    """
    Semantic + keyword search with v2 filter dict.

    Pass ``rerank=true`` to apply the configured reranker — this is a no-op when
    no reranker is configured in the active memory config.
    """
    try:
        kwargs: Dict[str, Any] = {}
        if body.filters is not None:
            kwargs["filters"] = body.filters
        if body.top_k is not None:
            kwargs["top_k"] = body.top_k
        if body.threshold is not None:
            kwargs["threshold"] = body.threshold
        if body.rerank is not None:
            kwargs["rerank"] = body.rerank
        if body.use_criteria is not None:
            kwargs["use_criteria"] = body.use_criteria
        if body.criteria is not None:
            kwargs["criteria"] = body.criteria
        return get_memory_instance().search(query=body.query, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise upstream_error()


@app.put("/memories/{memory_id}", summary="Update a memory")
def update_memory(memory_id: str, updated_memory: MemoryUpdate, _auth=Depends(verify_auth)):
    """Update an existing memory."""
    try:
        return get_memory_instance().update(
            memory_id=memory_id, data=updated_memory.text, metadata=updated_memory.metadata
        )
    except Exception:
        raise upstream_error()


@app.get("/memories/{memory_id}/history", summary="Get memory history")
def memory_history(memory_id: str, _auth=Depends(verify_auth)):
    """Retrieve memory history."""
    try:
        return get_memory_instance().history(memory_id=memory_id)
    except Exception:
        raise upstream_error()


@app.post(
    "/memories/{memory_id}/feedback",
    summary="Record feedback on a memory",
    response_model=MessageResponse,
)
def memory_feedback(memory_id: str, body: FeedbackBody, _auth=Depends(verify_auth)):
    """Record POSITIVE / NEGATIVE / VERY_NEGATIVE feedback on a memory.

    Mirrors the platform ``POST /v1/feedback/`` contract. The feedback is
    stored on the memory's payload and surfaces in subsequent
    ``GET /memories/{memory_id}`` responses under ``metadata``.

    Pass ``feedback=null`` and ``feedback_reason=null`` to clear existing
    feedback for this memory.
    """
    try:
        get_memory_instance().feedback(
            memory_id=memory_id,
            feedback=body.feedback,
            feedback_reason=body.feedback_reason,
        )
        return MessageResponse(message="Feedback recorded successfully")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise upstream_error()


@app.delete("/memories/{memory_id}", summary="Delete a memory", response_model=MessageResponse)
def delete_memory(memory_id: str, _auth=Depends(verify_auth)):
    """Delete a specific memory by ID."""
    try:
        get_memory_instance().delete(memory_id=memory_id)
        return MessageResponse(message="Memory deleted successfully")
    except Exception:
        raise upstream_error()


@app.post("/memories/delete", summary="Delete memories matching v2 filters", response_model=MessageResponse)
def delete_memories_by_filter(body: DeleteBody, _auth=Depends(verify_auth)):
    """Delete all memories matching a v2 filter dict.

    The filter must scope the operation — an empty filter is rejected to
    prevent accidental project-wide wipes (use ``POST /reset`` for that).
    """
    if not body.filters:
        raise HTTPException(
            status_code=400,
            detail="filters are required. Use POST /reset to wipe everything.",
        )
    try:
        get_memory_instance().delete_all(filters=body.filters)
        return MessageResponse(message="All relevant memories deleted")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise upstream_error()


@app.post("/reset", summary="Reset all memories")
def reset_memory(_auth=Depends(verify_auth)):
    """Completely reset stored memories."""
    try:
        get_memory_instance().reset()
        return {"message": "All memories reset"}
    except Exception:
        raise upstream_error()


@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)
def home():
    """Redirect to the OpenAPI documentation."""
    return RedirectResponse(url="/docs")
