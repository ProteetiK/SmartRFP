from __future__ import annotations

import logging
from typing import Dict, Optional

from backend.rag.chunker import DocumentChunker
from backend.rag.utils import (
    current_timestamp,
    generate_document_hash,
    rfp_namespace,
    KB_NAMESPACE,
)
from backend.rag.vector_store import VectorStore

logger = logging.getLogger("smartrfp.rag")


class DocumentIngestion:

    def __init__(self):
        self.chunker = DocumentChunker()
        self.vector_store = VectorStore()

    def _resolve_namespace(self, rfp_id: str, namespace: Optional[str]) -> str:
        return namespace or rfp_namespace(rfp_id)

    def ingest_document(
        self,
        text: str,
        rfp_id: str,
        filename: str,
        namespace: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        if not text or not text.strip():
            logger.warning("Empty text for rfp_id=%s; nothing ingested.", rfp_id)
            return {
                "status": "skipped",
                "reason": "empty_text",
                "rfp_id": rfp_id,
                "vectors_uploaded": 0,
            }

        ns = self._resolve_namespace(str(rfp_id), namespace)

        metadata = metadata or {}
        metadata.update(
            {
                "rfp_id": str(rfp_id),
                "filename": filename,
                "doc_hash": generate_document_hash(text),
                "ingested_at": current_timestamp(),
            }
        )

        documents = self.chunker.chunk_text(text=text, metadata=metadata)

        total_vectors = self.vector_store.upsert_documents(
            documents=documents,
            namespace=ns,
        )

        stats = self.chunker.statistics(documents)

        return {
            "status": "success",
            "rfp_id": rfp_id,
            "filename": filename,
            "namespace": ns,
            "vectors_uploaded": total_vectors,
            "chunk_statistics": stats,
        }

    def reindex_document(
        self,
        text: str,
        rfp_id: str,
        filename: str,
        namespace: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Delete old vectors, then upload fresh vectors."""
        self.delete_document(rfp_id=rfp_id, namespace=namespace)
        return self.ingest_document(
            text=text,
            rfp_id=rfp_id,
            filename=filename,
            namespace=namespace,
            metadata=metadata,
        )

    def delete_document(
        self,
        rfp_id: str,
        namespace: Optional[str] = None,
    ):
        self.vector_store.delete_rfp(rfp_id=str(rfp_id), namespace=namespace)

    def get_index_statistics(self):
        return self.vector_store.describe()

    # ------------------------------------------------------------------ #
    # Knowledge base (shared, cross-RFP corpus)
    # ------------------------------------------------------------------ #
    def ingest_kb_document(self, kb_id: int, title: str, doc_type: str, content: str) -> Dict:
        if not content or not content.strip():
            return {"status": "skipped", "reason": "empty_text", "kb_id": kb_id, "vectors_uploaded": 0}

        pseudo_id = f"kb-{kb_id}"
        metadata = {
            "kb_id": kb_id,
            "doc_type": doc_type or "reference",
            "source_type": "knowledge_base",
        }
        return self.ingest_document(
            text=content, rfp_id=pseudo_id, filename=title,
            namespace=KB_NAMESPACE, metadata=metadata,
        )

    def delete_kb_document(self, kb_id: int):
        self.vector_store.delete_rfp(rfp_id=f"kb-{kb_id}", namespace=KB_NAMESPACE)