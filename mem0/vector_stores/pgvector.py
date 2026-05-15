import json
import logging
import re
from contextlib import contextmanager
from typing import Any, List, Optional, Tuple

from pydantic import BaseModel

# Try to import psycopg (psycopg3) first, then fall back to psycopg2
try:
    from psycopg import sql
    from psycopg.types.json import Json
    from psycopg_pool import ConnectionPool
    PSYCOPG_VERSION = 3
    logger = logging.getLogger(__name__)
    logger.info("Using psycopg (psycopg3) with ConnectionPool for PostgreSQL connections")
except ImportError:
    try:
        from psycopg2 import sql
        from psycopg2.extras import Json, execute_values
        from psycopg2.pool import ThreadedConnectionPool as ConnectionPool
        PSYCOPG_VERSION = 2
        logger = logging.getLogger(__name__)
        logger.info("Using psycopg2 with ThreadedConnectionPool for PostgreSQL connections")
    except ImportError:
        raise ImportError(
            "Neither 'psycopg' nor 'psycopg2' library is available. "
            "Please install one of them using 'pip install psycopg[pool]' or 'pip install psycopg2'"
        )

from mem0.vector_stores.base import VectorStoreBase

logger = logging.getLogger(__name__)


class OutputData(BaseModel):
    id: Optional[str]
    score: Optional[float]
    payload: Optional[dict]


class PGVector(VectorStoreBase):
    def __init__(
        self,
        dbname,
        collection_name,
        embedding_model_dims,
        user,
        password,
        host,
        port,
        diskann,
        hnsw,
        minconn=1,
        maxconn=5,
        sslmode=None,
        connection_string=None,
        connection_pool=None,
    ):
        """
        Initialize the PGVector database.

        Args:
            dbname (str): Database name
            collection_name (str): Collection name
            embedding_model_dims (int): Dimension of the embedding vector
            user (str): Database user
            password (str): Database password
            host (str, optional): Database host
            port (int, optional): Database port
            diskann (bool, optional): Use DiskANN for faster search
            hnsw (bool, optional): Use HNSW for faster search
            minconn (int): Minimum number of connections to keep in the connection pool
            maxconn (int): Maximum number of connections allowed in the connection pool
            sslmode (str, optional): SSL mode for PostgreSQL connection (e.g., 'require', 'prefer', 'disable')
            connection_string (str, optional): PostgreSQL connection string (overrides individual connection parameters)
            connection_pool (Any, optional): psycopg2 connection pool object (overrides connection string and individual parameters)
        """
        self.collection_name = collection_name
        self.use_diskann = diskann
        self.use_hnsw = hnsw
        self.embedding_model_dims = embedding_model_dims
        self.connection_pool = None

        # Connection setup with priority: connection_pool > connection_string > individual parameters
        if connection_pool is not None:
            # Use provided connection pool
            self.connection_pool = connection_pool
        elif connection_string:
            if sslmode:
                # Append sslmode to connection string if provided
                if 'sslmode=' in connection_string:
                    # Replace existing sslmode
                    import re
                    connection_string = re.sub(r'sslmode=[^ ]*', f'sslmode={sslmode}', connection_string)
                else:
                    # Add sslmode to connection string
                    connection_string = f"{connection_string} sslmode={sslmode}"
        else:
            connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
            if sslmode:
                connection_string = f"{connection_string} sslmode={sslmode}"
        
        if self.connection_pool is None:
            if PSYCOPG_VERSION == 3:
                # psycopg3 ConnectionPool. `check=ConnectionPool.check_connection`
                # pings each connection before handing it out, so connections
                # killed server-side (postgres restart, AdminShutdown, idle timeout)
                # are replaced transparently instead of failing one in-flight query
                # with `psycopg.errors.AdminShutdown: terminating connection`.
                self.connection_pool = ConnectionPool(
                    conninfo=connection_string,
                    min_size=minconn,
                    max_size=maxconn,
                    open=True,
                    check=ConnectionPool.check_connection,
                )
            else:
                # psycopg2 ThreadedConnectionPool — no check hook available;
                # callers will see one failed query after a postgres restart.
                self.connection_pool = ConnectionPool(minconn=minconn, maxconn=maxconn, dsn=connection_string)

        collections = self.list_cols()
        if collection_name not in collections:
            self.create_col()

    @contextmanager
    def _get_cursor(self, commit: bool = False):
        """
        Unified context manager to get a cursor from the appropriate pool.
        Auto-commits or rolls back based on exception, and returns the connection to the pool.
        """
        if PSYCOPG_VERSION == 3:
            # psycopg3 auto-manages commit/rollback and pool return
            with self.connection_pool.connection() as conn:
                with conn.cursor() as cur:
                    try:
                        yield cur
                        if commit:
                            conn.commit()
                    except Exception:
                        conn.rollback()
                        logger.error("Error in cursor context (psycopg3)", exc_info=True)
                        raise
        else:
            # psycopg2 manual getconn/putconn
            conn = self.connection_pool.getconn()
            cur = conn.cursor()
            try:
                yield cur
                if commit:
                    conn.commit()
            except Exception as exc:
                conn.rollback()
                logger.error(f"Error occurred: {exc}")
                raise exc
            finally:
                cur.close()
                self.connection_pool.putconn(conn)

    def _col(self) -> "sql.Identifier":
        """Return a safely-quoted SQL identifier for the collection table."""
        return sql.Identifier(self.collection_name)

    def create_col(self) -> None:
        """
        Create a new collection (table in PostgreSQL).
        Will also initialize vector search index if specified.
        """
        with self._get_cursor(commit=True) as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    id UUID PRIMARY KEY,
                    vector vector({}),
                    payload JSONB
                );
                """).format(self._col(), sql.Literal(self.embedding_model_dims))
            )
            if self.use_diskann and self.embedding_model_dims < 2000:
                cur.execute("SELECT * FROM pg_extension WHERE extname = 'vectorscale'")
                if cur.fetchone():
                    # Create DiskANN index if extension is installed for faster search
                    cur.execute(
                        sql.SQL("""
                        CREATE INDEX IF NOT EXISTS {} ON {}
                        USING diskann (vector);
                        """).format(
                            sql.Identifier(f"{self.collection_name}_diskann_idx"),
                            self._col(),
                        )
                    )
            elif self.use_hnsw:
                cur.execute(
                    sql.SQL("""
                    CREATE INDEX IF NOT EXISTS {} ON {}
                    USING hnsw (vector vector_cosine_ops)
                    """).format(
                        sql.Identifier(f"{self.collection_name}_hnsw_idx"),
                        self._col(),
                    )
                )
            cur.execute(
                sql.SQL("""
                CREATE INDEX IF NOT EXISTS {} ON {}
                USING gin(to_tsvector('simple', payload->>'text_lemmatized'));
                """).format(
                    sql.Identifier(f"{self.collection_name}_text_lemmatized_idx"),
                    self._col(),
                )
            )

    def insert(self, vectors: list[list[float]], payloads=None, ids=None) -> None:
        logger.info(f"Inserting {len(vectors)} vectors into collection {self.collection_name}")
        json_payloads = [json.dumps(payload) for payload in payloads]

        data = [(id, vector, payload) for id, vector, payload in zip(ids, vectors, json_payloads)]
        if PSYCOPG_VERSION == 3:
            with self._get_cursor(commit=True) as cur:
                cur.executemany(
                    sql.SQL("INSERT INTO {} (id, vector, payload) VALUES (%s, %s, %s)").format(self._col()),
                    data,
                )
        else:
            with self._get_cursor(commit=True) as cur:
                execute_values(
                    cur,
                    sql.SQL("INSERT INTO {} (id, vector, payload) VALUES %s").format(self._col()),
                    data,
                )

    # ISO 8601 datetime detection — when both sides look like timestamps we cast
    # to timestamptz so range comparisons sort by time, not lexicographically.
    _ISO_DATETIME_RE = re.compile(
        r"^\d{4}-\d{2}-\d{2}"
        r"([T ]\d{2}:\d{2}(:\d{2})?"
        r"(\.\d+)?"
        r"(Z|[+-]\d{2}:?\d{2})?"
        r")?$"
    )

    _COMPARISON_OPS = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<="}
    _LOGICAL_KEYS = {"AND": "AND", "OR": "OR", "NOT": "NOT", "$and": "AND", "$or": "OR", "$not": "NOT"}

    def _build_filter_sql(self, filters: Optional[dict]) -> Optional[Tuple[sql.Composable, list]]:
        """
        Translate v2 filter dict into a SQL clause body (without the leading keyword).

        Supports:
        - Logical operators: AND/OR/NOT (and the $and/$or/$not aliases that
          Memory._process_metadata_filters emits).
        - Comparison operators per field: eq, ne, gt, gte, lt, lte, in, nin,
          contains, icontains.
        - Wildcard ``"*"`` — non-null check via ``payload->>%s IS NOT NULL``.
        - Special field ``memory_ids`` — routed to the table's ``id`` column
          rather than payload.
        - Special field ``metadata`` — its sub-keys are addressed as top-level
          payload keys (OSS stores metadata flat in the payload, not nested).

        Returns ``(clause, params)`` where ``clause`` is the body alone (callers
        prepend ``WHERE`` or ``AND``), or ``None`` when the filter dict produced
        no clause — letting callers skip emitting any filter SQL.
        """
        if not filters:
            return None
        body, params = self._compile_node(filters)
        if body is None:
            return None
        return body, params

    def _compile_node(self, node: dict) -> Tuple[Optional[sql.Composable], list]:
        """Compile a filter dict node into (clause, params). Returns (None, []) when empty."""
        clauses: List[sql.Composable] = []
        params: list = []
        # Track logical keys we've already handled so we don't double-process
        # both AND/$and forms when both happen to be present.
        seen_logical: set[str] = set()
        for key, value in node.items():
            normalized = self._LOGICAL_KEYS.get(key)
            if normalized is not None:
                if normalized in seen_logical:
                    continue
                seen_logical.add(normalized)
                logical_clause, logical_params = self._compile_logical(normalized, value)
                if logical_clause is not None:
                    clauses.append(logical_clause)
                    params.extend(logical_params)
            else:
                leaf_clause, leaf_params = self._compile_leaf(key, value)
                if leaf_clause is not None:
                    clauses.append(leaf_clause)
                    params.extend(leaf_params)
        if not clauses:
            return None, []
        if len(clauses) == 1:
            return clauses[0], params
        return sql.SQL("(") + sql.SQL(" AND ").join(clauses) + sql.SQL(")"), params

    def _compile_logical(self, op: str, value: Any) -> Tuple[Optional[sql.Composable], list]:
        if not isinstance(value, list):
            raise ValueError(f"{op} filter value must be a list of filter dicts, got {type(value).__name__}")
        sub_clauses: List[sql.Composable] = []
        sub_params: list = []
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValueError(f"{op} filter list item at index {i} must be a dict, got {type(item).__name__}")
            child_clause, child_params = self._compile_node(item)
            if child_clause is not None:
                sub_clauses.append(child_clause)
                sub_params.extend(child_params)
        if not sub_clauses:
            return None, []
        joiner = sql.SQL(" AND ") if op in ("AND", "NOT") else sql.SQL(" OR ")
        joined = joiner.join(sub_clauses)
        if op == "NOT":
            return sql.SQL("NOT (") + joined + sql.SQL(")"), sub_params
        return sql.SQL("(") + joined + sql.SQL(")"), sub_params

    def _compile_leaf(self, key: str, value: Any) -> Tuple[Optional[sql.Composable], list]:
        # memory_ids → table id column, not payload
        if key == "memory_ids":
            ids = value.get("in") if isinstance(value, dict) else value
            if not isinstance(ids, (list, tuple)):
                raise ValueError("memory_ids filter requires a list (raw or via {'in': [...]})")
            return sql.SQL("id::text = ANY(%s)"), [[str(x) for x in ids]]

        # metadata special key — sub-fields live at payload top-level in OSS
        if key == "metadata" and isinstance(value, dict):
            sub_node = dict(value)  # treat metadata sub-dict as another node
            return self._compile_node(sub_node)

        # wildcard: any non-null value present
        if value == "*":
            return sql.SQL("payload->>%s IS NOT NULL"), [key]

        # raw list shorthand: {field: [a, b]} → IN
        if isinstance(value, list):
            if not value:
                # An empty IN list cannot match anything; emit a false predicate.
                return sql.SQL("FALSE"), []
            return sql.SQL("payload->>%s = ANY(%s)"), [key, [str(x) for x in value]]

        # simple equality
        if not isinstance(value, dict):
            return sql.SQL("payload->>%s = %s"), [key, str(value)]

        # operator dict
        op_clauses: List[sql.Composable] = []
        op_params: list = []
        for op, op_val in value.items():
            clause, p = self._compile_operator(key, op, op_val)
            op_clauses.append(clause)
            op_params.extend(p)
        if len(op_clauses) == 1:
            return op_clauses[0], op_params
        return sql.SQL("(") + sql.SQL(" AND ").join(op_clauses) + sql.SQL(")"), op_params

    def _compile_operator(self, key: str, op: str, op_val: Any) -> Tuple[sql.Composable, list]:
        if op == "eq":
            return sql.SQL("payload->>%s = %s"), [key, str(op_val)]
        if op == "ne":
            # ne should match rows where the field differs OR is missing/null,
            # mirroring how the Platform handles "not equal" against absent fields.
            return (
                sql.SQL("(payload->>%s IS DISTINCT FROM %s)"),
                [key, str(op_val)],
            )
        if op == "in":
            if not isinstance(op_val, (list, tuple)):
                raise ValueError(f"'in' on field '{key}' requires a list, got {type(op_val).__name__}")
            if not op_val:
                return sql.SQL("FALSE"), []
            return sql.SQL("payload->>%s = ANY(%s)"), [key, [str(x) for x in op_val]]
        if op == "nin":
            if not isinstance(op_val, (list, tuple)):
                raise ValueError(f"'nin' on field '{key}' requires a list, got {type(op_val).__name__}")
            if not op_val:
                return sql.SQL("TRUE"), []
            return (
                sql.SQL("(payload->>%s IS NULL OR payload->>%s <> ALL(%s))"),
                [key, key, [str(x) for x in op_val]],
            )
        if op in self._COMPARISON_OPS:
            sym = self._COMPARISON_OPS[op]
            # Numeric comparison if value is numeric; timestamptz if it parses as ISO datetime.
            if isinstance(op_val, bool):
                # bool is subclass of int but we shouldn't compare like numbers
                return (
                    sql.SQL("payload->>%s ") + sql.SQL(sym) + sql.SQL(" %s"),
                    [key, str(op_val)],
                )
            if isinstance(op_val, (int, float)):
                return (
                    sql.SQL("(payload->>%s)::numeric ") + sql.SQL(sym) + sql.SQL(" %s::numeric"),
                    [key, str(op_val)],
                )
            if isinstance(op_val, str) and self._ISO_DATETIME_RE.match(op_val):
                return (
                    sql.SQL("(payload->>%s)::timestamptz ") + sql.SQL(sym) + sql.SQL(" %s::timestamptz"),
                    [key, op_val],
                )
            return (
                sql.SQL("payload->>%s ") + sql.SQL(sym) + sql.SQL(" %s"),
                [key, str(op_val)],
            )
        if op == "contains":
            return sql.SQL("payload->>%s LIKE %s"), [key, f"%{op_val}%"]
        if op == "icontains":
            return sql.SQL("payload->>%s ILIKE %s"), [key, f"%{op_val}%"]
        raise ValueError(f"Unsupported metadata filter operator: {op}")

    def search(
        self,
        query: str,
        vectors: list[float],
        top_k: Optional[int] = 5,
        filters: Optional[dict] = None,
    ) -> List[OutputData]:
        """
        Search for similar vectors.

        Args:
            query (str): Query.
            vectors (List[float]): Query vector.
            top_k (int, optional): Number of results to return. Defaults to 5.
            filters (Dict, optional): Filters to apply to the search. Defaults to None.

        Returns:
            list: Search results.
        """
        compiled = self._build_filter_sql(filters)
        if compiled is not None:
            filter_body, filter_params = compiled
            filter_clause = sql.SQL("WHERE ") + filter_body
        else:
            filter_params = []
            filter_clause = sql.SQL("")

        with self._get_cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT id, vector <=> %s::vector AS distance, payload
                FROM {}
                {}
                ORDER BY distance
                LIMIT %s
                """).format(self._col(), filter_clause),
                (vectors, *filter_params, top_k),
            )

            results = cur.fetchall()
        # `<=>` returns cosine *distance* (lower = more similar). Convert to a
        # similarity in [0, 1] so downstream scorers can sort descending and
        # combine with BM25/entity boosts (which are already similarities).
        return [
            OutputData(id=str(r[0]), score=max(0.0, 1.0 - float(r[1])), payload=r[2])
            for r in results
        ]

    def keyword_search(self, query, top_k=5, filters=None):
        """
        Search using PostgreSQL full-text search on lemmatized text.

        Args:
            query (str): The search query text.
            top_k (int, optional): Number of results to return. Defaults to 5.
            filters (dict, optional): Filters to apply to the search. Defaults to None.

        Returns:
            List[OutputData]: Search results ranked by text relevance.
        """
        compiled = self._build_filter_sql(filters)
        if compiled is not None:
            filter_body, filter_params = compiled
            # keyword_search already has a WHERE clause for the FTS predicate, so
            # we tack the filter body on with an AND prefix.
            filter_clause = sql.SQL("AND ") + filter_body
        else:
            filter_params = []
            filter_clause = sql.SQL("")

        try:
            with self._get_cursor() as cur:
                cur.execute(
                    sql.SQL("""
                    SELECT id, ts_rank_cd(to_tsvector('simple', payload->>'text_lemmatized'), plainto_tsquery('simple', %s)) AS score, payload
                    FROM {}
                    WHERE to_tsvector('simple', payload->>'text_lemmatized') @@ plainto_tsquery('simple', %s)
                    {}
                    ORDER BY score DESC
                    LIMIT %s
                    """).format(self._col(), filter_clause),
                    (query, query, *filter_params, top_k),
                )

                results = cur.fetchall()
            return [OutputData(id=str(r[0]), score=float(r[1]), payload=r[2]) for r in results]
        except Exception as e:
            logger.debug(f"Keyword search failed: {e}")
            return None

    def delete(self, vector_id: str) -> None:
        """
        Delete a vector by ID.

        Args:
            vector_id (str): ID of the vector to delete.
        """
        with self._get_cursor(commit=True) as cur:
            cur.execute(sql.SQL("DELETE FROM {} WHERE id = %s").format(self._col()), (vector_id,))

    def update(
        self,
        vector_id: str,
        vector: Optional[list[float]] = None,
        payload: Optional[dict] = None,
    ) -> None:
        """
        Update a vector and its payload.

        Args:
            vector_id (str): ID of the vector to update.
            vector (List[float], optional): Updated vector.
            payload (Dict, optional): Updated payload.
        """
        with self._get_cursor(commit=True) as cur:
            if vector:
               cur.execute(
                    sql.SQL("UPDATE {} SET vector = %s WHERE id = %s").format(self._col()),
                    (vector, vector_id),
                )
            if payload:
                # Handle JSON serialization based on psycopg version
                if PSYCOPG_VERSION == 3:
                    # psycopg3 uses psycopg.types.json.Json
                    cur.execute(
                        sql.SQL("UPDATE {} SET payload = %s WHERE id = %s").format(self._col()),
                        (Json(payload), vector_id),
                    )
                else:
                    # psycopg2 uses psycopg2.extras.Json
                    cur.execute(
                        sql.SQL("UPDATE {} SET payload = %s WHERE id = %s").format(self._col()),
                        (Json(payload), vector_id),
                    )


    def get(self, vector_id: str) -> OutputData:
        """
        Retrieve a vector by ID.

        Args:
            vector_id (str): ID of the vector to retrieve.

        Returns:
            OutputData: Retrieved vector.
        """
        with self._get_cursor() as cur:
            cur.execute(
                sql.SQL("SELECT id, vector, payload FROM {} WHERE id = %s").format(self._col()),
                (vector_id,),
            )
            result = cur.fetchone()
            if not result:
                return None
            return OutputData(id=str(result[0]), score=None, payload=result[2])

    def list_cols(self) -> List[str]:
        """
        List all collections.

        Returns:
            List[str]: List of collection names.
        """
        with self._get_cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            return [row[0] for row in cur.fetchall()]

    def delete_col(self) -> None:
        """Delete a collection."""
        with self._get_cursor(commit=True) as cur:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(self._col()))

    def col_info(self) -> dict[str, Any]:
        """
        Get information about a collection.

        Returns:
            Dict[str, Any]: Collection information.
        """
        with self._get_cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT
                    table_name,
                    (SELECT COUNT(*) FROM {}) as row_count,
                    (SELECT pg_size_pretty(pg_total_relation_size({}::regclass))) as total_size
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            """).format(self._col(), sql.Literal(self.collection_name)),
                (self.collection_name,),
            )
            result = cur.fetchone()
        return {"name": result[0], "count": result[1], "size": result[2]}

    def list(
        self,
        filters: Optional[dict] = None,
        top_k: Optional[int] = 100,
        *,
        offset: int = 0,
        count_total: bool = False,
    ) -> dict:
        """List vectors with optional pagination + total count.

        Returns:
            {"results": [[OutputData, ...]], "count": int | None}
        """
        compiled = self._build_filter_sql(filters)
        if compiled is not None:
            filter_body, filter_params = compiled
            filter_clause = sql.SQL("WHERE ") + filter_body
        else:
            filter_params = []
            filter_clause = sql.SQL("")

        with self._get_cursor() as cur:
            cur.execute(
                sql.SQL("""
                SELECT id, vector, payload
                FROM {}
                {}
                LIMIT %s OFFSET %s
                """).format(self._col(), filter_clause),
                (*filter_params, top_k, offset),
            )
            rows = cur.fetchall()

            count = None
            if count_total:
                cur.execute(
                    sql.SQL("SELECT count(*) FROM {} {}").format(self._col(), filter_clause),
                    tuple(filter_params),
                )
                count_row = cur.fetchone()
                count = int(count_row[0]) if count_row else 0

        output = [OutputData(id=str(r[0]), score=None, payload=r[2]) for r in rows]
        return {"results": [output], "count": count}

    def __del__(self) -> None:
        """
        Close the database connection pool when the object is deleted.
        """
        try:
            # Close pool appropriately
            if PSYCOPG_VERSION == 3:
                self.connection_pool.close()
            else:
                self.connection_pool.closeall()
        except Exception:
            pass

    def reset(self) -> None:
        """Reset the index by deleting and recreating it."""
        logger.warning(f"Resetting index {self.collection_name}...")
        self.delete_col()
        self.create_col()
