"""
Utility functions for SmartRFP RAG
"""

from __future__ import annotations

import functools
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("smartrfp.rag")


# ---------------------------------------------------------------------------
# IDs / namespaces
# ---------------------------------------------------------------------------

def generate_vector_id(
    rfp_id: str,
    chunk_id: int,
) -> str:
    """
    Deterministic vector id.

    IMPORTANT: the trailing separator lets us delete every chunk of an RFP
    by ID *prefix* on serverless indexes (which do not support delete-by-metadata).

    Example
    -------
    rfp_id=1, chunk_id=0 -> "1_0"
    rfp_id=1, chunk_id=1 -> "1_1"
    """
    return f"{rfp_id}_{chunk_id}"


def rfp_namespace(rfp_id: str | int) -> str:
    """
    Per-RFP namespace. Isolates each RFP's vectors so retrieval is scoped and
    deletion is a single (serverless-safe) namespace drop.
    """
    return f"rfp-{rfp_id}"


# Shared organizational knowledge base (security policies, past-proposal
# boilerplate, certifications, etc.) — a single namespace searched ALONGSIDE
# each RFP's own namespace during retrieval (see agents/rag_agent.py). Before
# this existed, /kb documents were stored in Postgres for display only and
# were never actually searchable by the RAG pipeline — proposals were
# grounded solely in the just-uploaded RFP text, not any persistent corpus.
KB_NAMESPACE = "knowledge-base"


# ---------------------------------------------------------------------------
# Hashing / timestamps
# ---------------------------------------------------------------------------

def generate_document_hash(text: str) -> str:
    """SHA256 of the document. Useful for skip-if-unchanged reindexing."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_timestamp() -> str:
    """UTC ISO-8601 timestamp (timezone-aware)."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Metadata handling
# ---------------------------------------------------------------------------

def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pinecone metadata values may ONLY be str, int, float, bool, or list[str].
    None values are rejected and will fail the whole upsert. This coerces /
    drops anything that would be rejected so a single bad field never kills
    an ingestion batch.
    """
    clean: Dict[str, Any] = {}

    for key, value in metadata.items():
        if value is None:
            # Pinecone rejects null metadata -> drop the key entirely.
            continue

        if isinstance(value, (str, int, float, bool)):
            clean[key] = value

        elif isinstance(value, list):
            # Only list[str] is allowed.
            clean[key] = [str(v) for v in value if v is not None]

        else:
            # Fallback: stringify unknown types (datetime, UUID, etc.).
            clean[key] = str(value)

    return clean


def build_metadata(
    rfp_id: str,
    filename: str,
    chunk_id: int,
    extra: Optional[Dict] = None,
) -> Dict:
    """Standard metadata used across Pinecone."""
    metadata = {
        "rfp_id": str(rfp_id),
        "filename": filename,
        "chunk_id": chunk_id,
        "created_at": current_timestamp(),
    }
    if extra:
        metadata.update(extra)
    return sanitize_metadata(metadata)


def truncate_text(text: str, max_chars: int = 300) -> str:
    """Truncate long text for logging."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


# ---------------------------------------------------------------------------
# Retry helper (no extra dependency)
# ---------------------------------------------------------------------------

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """
    Exponential-backoff retry decorator for transient Pinecone / network errors.
    Keeps ingestion and retrieval resilient in production without pulling in
    an external retry library.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__, attempt, exc,
                        )
                        raise
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                        func.__name__, attempt, max_attempts, exc, delay,
                    )
                    time.sleep(delay)

        return wrapper

    return decorator