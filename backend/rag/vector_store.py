"""
Production Vector Store

Responsibilities
----------------
1. Upsert vectors into Pinecone (batched, retried, metadata-sanitized)
2. Semantic similarity search
3. Delete vectors (serverless-safe: namespace drop or ID-prefix)
4. Metadata filtering
5. Namespace support
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

from langchain_core.documents import Document

from backend.rag.embedding import get_embedding_service
from backend.rag.pinecone_client import get_pinecone_manager
from backend.rag.utils import (
    generate_vector_id,
    rfp_namespace,
    sanitize_metadata,
    with_retry,
)

logger = logging.getLogger("smartrfp.rag")

UPSERT_BATCH_SIZE = 100
# How long to wait for freshly-upserted vectors to become queryable before
# giving up and proceeding anyway (non-fatal — see _wait_until_queryable).
# Pinecone serverless upserts are usually near-instant, but a brief
# propagation delay is possible, especially on a namespace's very first
# write. Without this wait, retrieval immediately after ingestion (exactly
# the upload -> draft-generation flow) could race the index and see 0
# vectors even though the upsert call itself succeeded — this was a real,
# hard-to-reproduce cause of "0 documents retrieved" right after upload.
UPSERT_READY_MAX_WAIT_SECONDS = 3.0
UPSERT_READY_POLL_INTERVAL_SECONDS = 0.5


class VectorStore:

    def __init__(self):
        self.embedder = get_embedding_service()
        self.pinecone = get_pinecone_manager()
        self.index = self.pinecone.get_index()

    # ------------------------------------------------------------------ #
    # UPSERT
    # ------------------------------------------------------------------ #

    def upsert_documents(
        self,
        documents: List[Document],
        namespace: str = "default",
    ) -> int:
        if not documents:
            return 0

        texts = [doc.page_content for doc in documents]
        embeddings = self.embedder.embed_documents(texts)

        vectors = []
        for doc, embedding in zip(documents, embeddings):
            vector_id = generate_vector_id(
                rfp_id=doc.metadata["rfp_id"],
                chunk_id=doc.metadata["chunk_id"],
            )
            metadata = sanitize_metadata(
                {**doc.metadata, "text": doc.page_content}
            )
            vectors.append(
                {"id": vector_id, "values": embedding, "metadata": metadata}
            )

        total = 0
        for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
            batch = vectors[i:i + UPSERT_BATCH_SIZE]
            self._upsert_batch(batch, namespace)
            total += len(batch)

        logger.info("Upserted %d vectors into namespace '%s'.", total, namespace)

        if total > 0:
            self._wait_until_queryable(namespace, expected_min=total)

        return total

    def _wait_until_queryable(self, namespace: str, expected_min: int) -> None:
        """Poll describe_index_stats() until the namespace reports at least
        `expected_min` vectors, or give up after UPSERT_READY_MAX_WAIT_SECONDS.

        Non-fatal by design: if this times out (or the stats call itself
        fails), we log and return anyway rather than blocking ingestion
        indefinitely or turning an eventual-consistency delay into a hard
        failure. Retrieval immediately afterward may still occasionally see
        a partial view, but the common case (near-instant Pinecone
        serverless propagation) is now actually waited for instead of raced.
        """
        deadline = time.monotonic() + UPSERT_READY_MAX_WAIT_SECONDS
        last_seen = 0
        while time.monotonic() < deadline:
            try:
                stats = self.describe()
                namespaces = getattr(stats, "namespaces", None)
                if namespaces is None and isinstance(stats, dict):
                    namespaces = stats.get("namespaces", {})
                ns_stats = (namespaces or {}).get(namespace)
                count = getattr(ns_stats, "vector_count", None) if ns_stats is not None else None
                if count is None and isinstance(ns_stats, dict):
                    count = ns_stats.get("vector_count")
                last_seen = count or 0
                if last_seen >= expected_min:
                    return
            except Exception:  # noqa: BLE001
                logger.debug("describe_index_stats() failed while waiting for "
                            "namespace '%s' to become queryable; will retry.", namespace)
            time.sleep(UPSERT_READY_POLL_INTERVAL_SECONDS)

        logger.warning(
            "Namespace '%s' reported %d/%d vectors after waiting %.1fs — "
            "proceeding anyway (Pinecone propagation may still be in progress; "
            "retrieval immediately after this may see a partial or empty result).",
            namespace, last_seen, expected_min, UPSERT_READY_MAX_WAIT_SECONDS,
        )

    @with_retry(max_attempts=3, base_delay=1.0)
    def _upsert_batch(self, batch: List[Dict], namespace: str):
        self.index.upsert(vectors=batch, namespace=namespace)

    # ------------------------------------------------------------------ #
    # SEARCH
    # ------------------------------------------------------------------ #

    @with_retry(max_attempts=3, base_delay=1.0)
    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
        metadata_filter: Optional[Dict] = None,
    ) -> List[Document]:
        query_embedding = self.embedder.embed_query(query)

        response = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=namespace,
            filter=metadata_filter,
        )

        matches = getattr(response, "matches", None)
        if matches is None and isinstance(response, dict):
            matches = response.get("matches", [])

        documents: List[Document] = []
        for match in matches or []:
            metadata = dict(getattr(match, "metadata", None) or {})
            page_content = metadata.pop("text", "")
            documents.append(
                Document(
                    page_content=page_content,
                    metadata={**metadata, "score": getattr(match, "score", 0.0)},
                )
            )
        return documents

    # ------------------------------------------------------------------ #
    # DELETE
    # ------------------------------------------------------------------ #

    def delete_rfp(self, rfp_id: str, namespace: Optional[str] = None):
        """
        Delete every vector for an RFP.

        Default strategy: drop the RFP's dedicated namespace (serverless-safe,
        single API call). If a shared namespace is passed explicitly, fall back
        to ID-prefix deletion (also serverless-safe).
        """
        if namespace is None:
            self.pinecone.delete_namespace(rfp_namespace(rfp_id))
        else:
            self.pinecone.delete_by_id_prefix(
                prefix=f"{rfp_id}_", namespace=namespace
            )

    def delete_namespace(self, namespace: str):
        self.pinecone.delete_namespace(namespace)

    # ------------------------------------------------------------------ #
    # STATS
    # ------------------------------------------------------------------ #

    def describe(self):
        return self.index.describe_index_stats()