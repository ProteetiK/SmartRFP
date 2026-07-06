"""
Retriever for SmartRFP

Responsibilities
----------------
1. Retrieve relevant chunks from Pinecone
2. Apply score threshold
3. Build context for the LLM
4. Support metadata filtering + per-RFP namespaces
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from langchain_core.documents import Document

from backend.config import settings
from backend.rag.utils import rfp_namespace
from backend.rag.vector_store import VectorStore

logger = logging.getLogger("smartrfp.rag")


class Retriever:

    def __init__(
        self,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ):
        self.vector_store = VectorStore()
        self.top_k = top_k or settings.RAG_TOP_K
        # Configurable via RAG_SCORE_THRESHOLD (settings.py) instead of
        # hardcoded, so it can be tuned per-deployment/embedding-model
        # without a code change.
        self.score_threshold = (
            score_threshold if score_threshold is not None else settings.RAG_SCORE_THRESHOLD
        )

    def retrieve(
        self,
        query: str,
        namespace: str = "default",
        metadata_filter: Optional[Dict] = None,
    ) -> List[Document]:
        documents = self.vector_store.similarity_search(
            query=query,
            top_k=self.top_k,
            namespace=namespace,
            metadata_filter=metadata_filter,
        )
        filtered = self._apply_threshold(documents, context=f"namespace '{namespace}'")
        return filtered

    def retrieve_multi(
        self,
        query: str,
        namespaces: List[str],
        metadata_filter: Optional[Dict] = None,
    ) -> List[Document]:
        """Query several namespaces with the same embedding and merge into a
        single ranked, threshold-filtered result set capped at top_k overall.

        Used to search an RFP's own namespace AND the shared knowledge-base
        namespace together, so retrieval draws on both the just-uploaded
        document and the persistent organizational corpus instead of only
        ever seeing the current RFP in isolation.
        """
        all_docs: List[Document] = []
        for ns in namespaces:
            all_docs.extend(self.vector_store.similarity_search(
                query=query, top_k=self.top_k, namespace=ns, metadata_filter=metadata_filter,
            ))
        all_docs.sort(key=lambda d: d.metadata.get("score", 0), reverse=True)
        filtered = self._apply_threshold(all_docs, context=f"namespaces {namespaces}")
        return filtered[: self.top_k]

    def _apply_threshold(self, documents: List[Document], context: str) -> List[Document]:
        filtered = [
            doc for doc in documents
            if doc.metadata.get("score", 0) >= self.score_threshold
        ]
        if documents and not filtered:
            # Distinguishes "genuinely nothing indexed" from "results exist
            # but all scored below threshold" — the latter usually means the
            # query text is a poor semantic match for the indexed content
            # (e.g. too generic/broad), not that ingestion failed.
            top_scores = sorted((d.metadata.get("score", 0) for d in documents), reverse=True)[:3]
            logger.info(
                "Retriever: %s returned %d result(s) but none met "
                "score_threshold=%.2f (top raw scores: %s). Consider lowering "
                "RAG_SCORE_THRESHOLD or using a more specific query.",
                context, len(documents), self.score_threshold, top_scores,
            )
        return filtered

    def retrieve_for_rfp(
        self,
        query: str,
        rfp_id: str | int,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Document]:
        """Convenience: retrieve strictly within one RFP's namespace."""
        return self.retrieve(
            query=query,
            namespace=rfp_namespace(rfp_id),
            metadata_filter=metadata_filter,
        )

    def build_context(self, documents: List[Document]) -> str:
        if not documents:
            return ""

        context_parts = []
        for idx, doc in enumerate(documents, start=1):
            filename = doc.metadata.get("filename", "Unknown")
            chunk_id = doc.metadata.get("chunk_id", "N/A")
            score = round(doc.metadata.get("score", 0), 4)
            context_parts.append(
                f"------------------------------\n"
                f"Context {idx}\n"
                f"Source   : {filename}\n"
                f"Chunk ID : {chunk_id}\n"
                f"Score    : {score}\n\n"
                f"{doc.page_content}\n"
            )
        return "\n".join(context_parts)

    def retrieve_context(
        self,
        query: str,
        namespace: str = "default",
        metadata_filter: Optional[Dict] = None,
    ) -> str:
        documents = self.retrieve(
            query=query,
            namespace=namespace,
            metadata_filter=metadata_filter,
        )
        return self.build_context(documents)