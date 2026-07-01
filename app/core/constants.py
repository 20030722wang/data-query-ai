"""Centralized enterprise constants — no hardcoded magic values scattered across files.

All timeout, limit, batch-size, and threshold values should be referenced from
this module so they can be tuned from a single place.
"""

# ── SQL ──────────────────────────────────────────────────────────────────────

SQL_MAX_RESULT_ROWS: int = 10_000
SQL_READ_ONLY_PREFIXES = frozenset({"SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC", "WITH"})
SQL_MAX_CORRECTION_ATTEMPTS: int = 3

# ── LLM ──────────────────────────────────────────────────────────────────────

LLM_REQUEST_TIMEOUT: float = 45.0  # seconds per individual LLM call

# ── Graph ────────────────────────────────────────────────────────────────────

GRAPH_EXECUTION_TIMEOUT: float = 120.0  # seconds — cumulative for full pipeline

# ── Retrieval ────────────────────────────────────────────────────────────────

QDRANT_SEARCH_LIMIT: int = 20
QDRANT_SCORE_THRESHOLD: float = 0.6
ES_SEARCH_LIMIT: int = 20
ES_SCORE_THRESHOLD: float = 0.6

# ── Embedding ────────────────────────────────────────────────────────────────

EMBEDDING_BATCH_SIZE: int = 20

# ── Database ─────────────────────────────────────────────────────────────────

DB_DEFAULT_POOL_SIZE: int = 10
DB_DEFAULT_MAX_OVERFLOW: int = 20

# ── Column value sync ────────────────────────────────────────────────────────

COLUMN_VALUE_SYNC_LIMIT: int = 1_000_000

# ── Retry ────────────────────────────────────────────────────────────────────

RETRY_MAX_ATTEMPTS: int = 3
RETRY_BASE_DELAY: float = 0.5  # seconds
RETRY_MAX_DELAY: float = 10.0  # seconds

# ── Query ────────────────────────────────────────────────────────────────────

QUERY_MAX_LENGTH: int = 1000
QUERY_MIN_LENGTH: int = 1
