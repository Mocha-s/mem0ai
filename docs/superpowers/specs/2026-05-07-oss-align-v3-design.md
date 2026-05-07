# OSS REST Server: Align with Platform V3 API

- **Date:** 2026-05-07
- **Branch:** `feat/oss-align-platform-v2`
- **Status:** Approved (pending user review of this spec)
- **Type:** Breaking change — hard switch

## Goal

Bring the self-hosted FastAPI server's memory contract into alignment with the
hosted-platform V3 API documented at `docs.mem0.ai/api-reference/memory/{add,get,search}-memories`.
Clients writing against `api.mem0.ai/v3/...` should be able to point at the OSS
server with only a base-URL change.

## Non-goals

- Aligning internal infrastructure (no new queue, no new search engine).
- Implementing platform-side features outside the three referenced endpoints
  (e.g. `POST /v1/feedback/` collection-wide endpoint, batch operations).
- Redesigning auth, projects, entities, or configuration routes.
- Implementing event retention/cleanup as a server-side cron — left as ops
  documentation.

## Decisions (settled in brainstorming)

| Axis | Decision |
|---|---|
| Scope | Full V3 contract: paths, async + `event_id`, hybrid retrieval semantics |
| Backwards compat | Hard cut — old `/memories*` paths return 404 |
| Async runtime | FastAPI `BackgroundTasks` + new Postgres `events` table |
| Worker recovery | App startup sweep marks stale `PENDING` events as `FAILED` |
| Event polling path | `GET /v1/event/{event_id}/` (mirror platform exactly) |
| BM25 / hybrid retrieval | Reuse existing SDK implementation (`mem0/utils/scoring.py` + `mem0/vector_stores/pgvector.py keyword_search`) |
| Pagination | Postgres OFFSET/LIMIT via SDK extension; precise `count` via new `count_total=True` flag |

## §1 Routes

Hard switch — old paths are removed, no deprecation header / no 410.

| Old | New | Notes |
|---|---|---|
| `POST /memories` | `POST /v3/memories/add/` | Now async; returns `event_id` |
| `POST /memories/list` | `POST /v3/memories/` | Paginated envelope; `filters` required |
| `POST /memories/search` | `POST /v3/memories/search/` | `filters` required; new defaults |
| `GET /memories/{id}` | `GET /v3/memories/{id}/` | unchanged behavior |
| `PUT /memories/{id}` | `PUT /v3/memories/{id}/` | unchanged behavior |
| `DELETE /memories/{id}` | `DELETE /v3/memories/{id}/` | unchanged behavior |
| `POST /memories/delete` | `POST /v3/memories/delete/` | unchanged behavior |
| `GET /memories/{id}/history` | `GET /v3/memories/{id}/history/` | unchanged behavior |
| `POST /memories/{id}/feedback` | `POST /v3/memories/{id}/feedback/` | unchanged behavior |
| — | `GET /v1/event/{event_id}/` | New: poll async add status |

Out of scope (unchanged paths): `/configure*`, `/auth/*`, `/api-keys*`,
`/entities*`, `/projects*`, `/requests*`, `/reset`, `/generate-instructions`.

All new V3 routes carry a trailing slash to match platform exactly.
`redirect_slashes=False` is already set in `server/main.py:156`.

### New helpers (server/main.py)

Three small helpers shared across the new routes:

- `_has_entity_scope_top_level(req: MemoryCreate) -> bool` — used by add. Checks
  `req.user_id`, `req.agent_id`, `req.run_id`, or `req.app_id` is set.
- `_require_entity_scope(filters: Dict[str, Any]) -> None` — used by list /
  search / batch-delete. Mirrors `_filter_has_entity_scope` from
  `mem0/memory/main.py`. Walks `AND`/`OR` (rejects `NOT`-only-scoped) and
  raises `HTTPException(400, ...)` if no positively-scoped entity ID is found.
- `_build_page_url(request: Request, page: int, page_size: int) -> str` — used
  by list. Returns the absolute URL for the requested page using
  `request.url_for(...)` + querystring rebuild.

## §2 Events table + async dispatch

### Schema

New SQLAlchemy model in `server/models.py`:

```python
class Event(Base):
    __tablename__ = "events"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=_new_uuid)
    status: Mapped[str] = mapped_column(String(16), index=True)  # PENDING|SUCCEEDED|FAILED
    payload: Mapped[dict] = mapped_column(_JsonType)
    result: Mapped[dict | None] = mapped_column(_JsonType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
```

### Migration

`server/alembic/versions/008_create_events.py` — `op.create_table` for `events`.
Add Postgres-only partial index `(status) WHERE status='PENDING'` via
`postgresql_where` keyword (Alembic skips on SQLite test runs).

### Dispatcher

```python
@app.post("/v3/memories/add/", status_code=200)
def add_memory_v3(req: MemoryCreate, bg: BackgroundTasks, _auth=Depends(verify_auth)):
    if not _has_entity_scope_top_level(req):
        raise HTTPException(400, "At least one entity ID is required.")
    with SessionLocal() as s:
        event = Event(status="PENDING", payload=req.model_dump(exclude_none=True))
        s.add(event); s.commit(); s.refresh(event)
        event_id = event.id
    bg.add_task(_run_add_event, event_id)
    return {
        "message": "Memory processing has been queued for background execution",
        "status": "PENDING",
        "event_id": str(event_id),
    }


def _run_add_event(event_id: uuid.UUID) -> None:
    with SessionLocal() as s:
        ev = s.get(Event, event_id)
        if ev is None or ev.status != "PENDING":
            return
        try:
            payload = ev.payload
            messages = payload.pop("messages", [])
            result = get_memory_instance().add(messages=messages, **payload)
            ev.result = result
            ev.status = "SUCCEEDED"
        except Exception as exc:
            ev.error = str(exc)
            ev.status = "FAILED"
        finally:
            s.commit()
```

`_run_add_event` opens its own `SessionLocal()` because the request session is
already closed when BackgroundTasks fires.

### Polling endpoint

```python
@app.get("/v1/event/{event_id}/")
def get_event(event_id: uuid.UUID, _auth=Depends(verify_auth)):
    with SessionLocal() as s:
        ev = s.get(Event, event_id)
        if ev is None:
            raise HTTPException(404, "event not found")
        return {
            "event_id": str(ev.id),
            "status": ev.status,
            "result": ev.result,
            "error": ev.error,
            "created_at": ev.created_at,
            "updated_at": ev.updated_at,
        }
```

### Startup sweep

```python
@app.on_event("startup")
def _sweep_stale_events() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    with SessionLocal() as s:
        stale = s.execute(
            select(Event).where(Event.status == "PENDING", Event.created_at < cutoff)
        ).scalars().all()
        for ev in stale:
            ev.status = "FAILED"
            ev.error = "server restarted before completion"
        s.commit()
```

Runs once per process boot. The 5-minute cutoff is the same window the platform
documents for typical add latency; events younger than that are left alone in
case the worker is mid-flight on a parallel run (defensive — in OSS single-pod
deploys this is theoretical).

## §3 Pagination envelope

`POST /v3/memories/` returns `{count, next, previous, results}`:

```python
class ListBody(BaseModel):
    filters: Dict[str, Any] = Field(..., description="Required; must include at least one entity ID")

@app.post("/v3/memories/")
def list_memories_v3(
    body: ListBody,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    _auth=Depends(verify_auth),
):
    _require_entity_scope(body.filters)
    offset = (page - 1) * page_size
    page_data = get_memory_instance().get_all(
        filters=body.filters,
        top_k=page_size,
        offset=offset,
        count_total=True,
    )
    count = page_data.get("count")
    results = page_data.get("results", [])
    return {
        "count": count,
        "next": _build_page_url(request, page + 1, page_size) if (count is not None and offset + len(results) < count) else None,
        "previous": _build_page_url(request, page - 1, page_size) if page > 1 else None,
        "results": results,
    }
```

### SDK extensions required

- `mem0/memory/main.py Memory.get_all(...)` — accept `offset: int = 0` and
  `count_total: bool = False`. When `count_total=True`, include a `count` key in
  the returned dict (precise total of matching memories ignoring pagination).
- `mem0/vector_stores/base.py` — extend `list()` signature with `offset` and
  `count_total`. Default impls in non-pgvector backends ignore these and return
  `count=None` to signal "unsupported".
- `mem0/vector_stores/pgvector.py` — wire `OFFSET` into the existing list query
  and run a parallel `SELECT count(*)` when requested.

When the active vector store doesn't implement `count_total`, server returns
`count=null` in the envelope. `next`/`previous` then fall back to "has more =
returned `page_size` rows" heuristic.

## §4 Search defaults + filter validation

```python
class SearchBody(BaseModel):
    query: str = Field(..., min_length=1)
    filters: Dict[str, Any] = Field(..., description="Required; must include at least one entity ID")
    top_k: int = Field(10, ge=1, le=1000)
    threshold: float = Field(0.1, ge=0.0, le=1.0)
    rerank: bool = Field(False)
    use_criteria: Optional[bool] = None
    criteria: Optional[list] = None

@app.post("/v3/memories/search/")
def search_memories_v3(body: SearchBody, _auth=Depends(verify_auth)):
    _require_entity_scope(body.filters)
    return get_memory_instance().search(
        query=body.query,
        filters=body.filters,
        top_k=body.top_k,
        threshold=body.threshold,
        rerank=body.rerank,
        use_criteria=body.use_criteria,
        criteria=body.criteria,
    )
```

`_require_entity_scope` is a server-local helper that mirrors
`_filter_has_entity_scope` in `mem0/memory/main.py`. The SDK already raises
`ValueError` for missing entity scope; the server-local check produces a clean
HTTP 400 instead of a 500-via-exception-handler.

Hybrid retrieval (semantic + BM25 + entity boost) is fully delegated to the SDK
and active for any vector store that implements `keyword_search` (today:
pgvector). Other backends gracefully degrade to semantic-only.

## §5 Migration & breaking-change docs

1. **`MIGRATION_GUIDE_v1.0.md`** — append `## V3 API Migration` section:
   - Path mapping table (old → new)
   - Async add example: `POST` → poll `event_id` → resolve
   - List pagination example (`page` / `page_size`)
   - Search filter requirement
   - Removed endpoints (404)
2. **`docs/open-source/features/rest-api.mdx`** — rewrite endpoint table to
   match `server/main.py` after this change. Replace the line-21 Warning
   ("OSS does not use /v1/ prefix") with a note that V3 paths and the
   `/v1/event/` polling endpoint are now shared with the platform.
3. **`docs/openapi.json`** — auto-regenerated by FastAPI on next server boot.
   No manual edit required, but commit the regenerated file.
4. **CHANGELOG / commit subject** — use `feat(server)!:` to flag the breaking
   change. PR description must include the migration cheatsheet.

## §6 Tests

Existing convention: server tests live under `tests/` with prefix `test_server_*.py`
(see `tests/test_server_v2_endpoints.py`, `tests/test_server_auth.py`,
`tests/test_server_project.py`, `tests/test_server_params.py`).

| Layer | File | Coverage |
|---|---|---|
| Unit | `tests/test_server_events_table.py` | Event model CRUD, status transitions, startup sweep |
| Unit | `tests/test_server_pagination_envelope.py` | next/previous URL builder, count math, page bounds |
| Integration | `tests/test_server_v3_routes.py` | Each V3 path: 200 happy, 401, 400 (empty filters / no entity ID) |
| Integration | `tests/test_server_v3_async_add.py` | `POST add` → poll `event_id` → SUCCEEDED; missing event → 404; FAILED carries `error` |
| Integration | `tests/test_server_v3_hybrid_search.py` | `POST search` returns categories + combined score for pgvector backend |
| Integration | `tests/test_server_v3_breaking.py` | Old `/memories*` paths return 404 (no accidental aliases) |
| Migration | `tests/test_server_migration_008.py` | `alembic upgrade head` creates `events`; `downgrade -1` drops it; runs on both SQLite and Postgres in CI |
| SDK regression | existing `tests/memory/` | Unchanged — SDK behavior must not regress |

`BackgroundTasks` in `TestClient` runs synchronously, so async-add tests can
poll immediately without sleep. The hybrid-search test must use a pgvector
fixture (Compose-up Postgres) — skip on the default SQLite test config.

## File touch list

### server/

- `main.py` — replace 9 memory routes, add `/v1/event/{event_id}/`, add startup hook
- `models.py` — add `Event` model
- `alembic/versions/008_create_events.py` — new migration

### mem0/ (SDK)

- `mem0/memory/main.py` — `Memory.get_all` accepts `offset`, `count_total`
- `mem0/vector_stores/base.py` — extend `list()` signature
- `mem0/vector_stores/pgvector.py` — implement `offset` + `count_total`

### docs/

- `MIGRATION_GUIDE_v1.0.md` — V3 migration section
- `docs/open-source/features/rest-api.mdx` — rewrite endpoint table
- `docs/openapi.json` — regenerated

### tests/

- 7 new test files under `tests/` with `test_server_*.py` prefix (see §6 table)

## Risks

| Risk | Mitigation |
|---|---|
| BackgroundTasks executes after response — exceptions are silent | `_run_add_event` catches all exceptions and writes `error` to events table; logs via existing `logging` setup |
| Process crash mid-task leaves PENDING events forever | Startup sweep marks stale (>5 min) PENDING as FAILED |
| `count_total=True` slow on large tables | Documented as "do not enable on hot paths"; only used for the paginated list endpoint, not search |
| SQLite tests cannot exercise partial index | Alembic conditional on dialect; partial index applies only on Postgres |
| Existing OSS clients break on hard cut | Documented in MIGRATION_GUIDE; PR title carries `!` |
| `event_id` accumulates without cleanup | Documented as ops responsibility (cron `DELETE FROM events WHERE created_at < now() - 30 days`) |

## Out of scope (explicit)

- Webhook / push notifications when events complete
- Distributed worker / multi-pod horizontal scaling
- Hybrid retrieval for non-pgvector backends (graceful degradation only)
- Per-event retry policy
- `categories` field synthesis (already produced by SDK when category extraction is configured)
- `custom_instructions` as top-level add field (currently OSS uses `prompt`; renaming is a separate follow-up)
