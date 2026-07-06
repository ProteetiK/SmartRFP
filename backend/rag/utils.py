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
    return f"{rfp_id}_{chunk_id}"


def rfp_namespace(rfp_id: str | int) -> str:
    return f"rfp-{rfp_id}"

KB_NAMESPACE = "knowledge-base"


# ---------------------------------------------------------------------------
# Hashing / timestamps
# ---------------------------------------------------------------------------

def generate_document_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Metadata handling
# ---------------------------------------------------------------------------

def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    clean: Dict[str, Any] = {}

    for key, value in metadata.items():
        if value is None:
            continue

        if isinstance(value, (str, int, float, bool)):
            clean[key] = value

        elif isinstance(value, list):
            clean[key] = [str(v) for v in value if v is not None]

        else:
            clean[key] = str(value)

    return clean


def build_metadata(
    rfp_id: str,
    filename: str,
    chunk_id: int,
    extra: Optional[Dict] = None,
) -> Dict:
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