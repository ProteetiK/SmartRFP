from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import List

from pinecone import Pinecone, ServerlessSpec

from backend.config import settings

logger = logging.getLogger("smartrfp.rag")

INDEX_READY_TIMEOUT_SECONDS = 120
INDEX_READY_POLL_SECONDS = 2


class PineconeManager:
    """Production-ready Pinecone manager."""

    def __init__(self):
        if not settings.PINECONE_API_KEY:
            raise RuntimeError(
                "PINECONE_API_KEY is not set. Add it to your .env before "
                "starting the backend."
            )

        self.api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME
        self.dimension = settings.EMBEDDING_DIMENSION
        self.metric = settings.PINECONE_METRIC
        self.cloud = settings.PINECONE_CLOUD
        self.region = settings.PINECONE_REGION

        self.pc = Pinecone(api_key=self.api_key)

        self._create_index_if_needed()

        self.index = self.pc.Index(self.index_name)
        logger.info("Pinecone index '%s' ready.", self.index_name)

    # ------------------------------------------------------------------ #
    # Index lifecycle
    # ------------------------------------------------------------------ #

    def _existing_index_names(self) -> List[str]:
        indexes = self.pc.list_indexes()
        # pinecone>=3 exposes .names(); fall back to iteration if not present.
        try:
            return list(indexes.names())
        except AttributeError:
            return [idx["name"] for idx in indexes]

    def _create_index_if_needed(self):
        if self.index_name in self._existing_index_names():
            return

        logger.info("Creating Pinecone index '%s'...", self.index_name)

        self.pc.create_index(
            name=self.index_name,
            dimension=self.dimension,
            metric=self.metric,
            spec=ServerlessSpec(
                cloud=self.cloud,
                region=self.region,
            ),
        )

        self._wait_until_ready()
        logger.info("Pinecone index '%s' created.", self.index_name)

    def _wait_until_ready(self):
        deadline = time.time() + INDEX_READY_TIMEOUT_SECONDS

        while time.time() < deadline:
            try:
                desc = self.pc.describe_index(self.index_name)
                ready = desc.get("status", {}).get("ready", False) \
                    if isinstance(desc, dict) else getattr(desc.status, "ready", False)
                if ready:
                    return
            except Exception as exc:  # noqa: BLE001
                logger.debug("describe_index not ready yet: %s", exc)

            time.sleep(INDEX_READY_POLL_SECONDS)

        raise TimeoutError(
            f"Pinecone index '{self.index_name}' did not become ready in "
            f"{INDEX_READY_TIMEOUT_SECONDS}s."
        )

    # ------------------------------------------------------------------ #
    # Accessors
    # ------------------------------------------------------------------ #

    def get_index(self):
        return self.index

    def describe_index(self):
        return self.pc.describe_index(self.index_name)

    # ------------------------------------------------------------------ #
    # Deletion (serverless-safe)
    # ------------------------------------------------------------------ #

    def delete_namespace(self, namespace: str):
        try:
            self.index.delete(delete_all=True, namespace=namespace)
        except Exception as exc:  # noqa: BLE001
            if "not found" in str(exc).lower() or "404" in str(exc):
                logger.info("Namespace '%s' already absent.", namespace)
                return
            raise

    def delete_by_id_prefix(self, prefix: str, namespace: str):
        ids_batch: List[str] = []
        for ids in self.index.list(prefix=prefix, namespace=namespace):
            batch = ids if isinstance(ids, list) else [ids]
            ids_batch.extend(batch)

            if len(ids_batch) >= 1000:
                self.index.delete(ids=ids_batch, namespace=namespace)
                ids_batch = []

        if ids_batch:
            self.index.delete(ids=ids_batch, namespace=namespace)

    # ------------------------------------------------------------------ #
    # Health
    # ------------------------------------------------------------------ #

    def health_check(self) -> dict:
        try:
            stats = self.index.describe_index_stats()
            # v6 returns an object; support both object and dict access.
            total = (
                getattr(stats, "total_vector_count", None)
                if not isinstance(stats, dict)
                else stats.get("total_vector_count")
            )
            return {
                "status": "healthy",
                "index": self.index_name,
                "total_vectors": total or 0,
            }
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": str(exc)}


@lru_cache(maxsize=1)
def get_pinecone_manager() -> PineconeManager:
    return PineconeManager()