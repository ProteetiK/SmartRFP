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