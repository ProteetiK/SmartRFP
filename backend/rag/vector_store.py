from __future__ import annotations

import logging
from typing import Dict, List, Optional

from azure.search.documents.models import VectorizedQuery
from langchain_core.documents import Document

from backend.rag.azure_search_client import get_search_client
from backend.rag.embedding import get_embedding_service
from backend.rag.utils import (
    generate_vector_id,
    sanitize_metadata,
    with_retry,
)

logger = logging.getLogger("smartrfp.rag")

UPLOAD_BATCH_SIZE = 100


class VectorStore:
    """
    Azure AI Search-backed vector store.

    This class intentionally keeps the same public interface that the
    previous Pinecone implementation exposed so that the RAG pipeline
    does not need to know which vector database is being used.
    """

    def __init__(self):
        self.embedder = get_embedding_service()
        self.client = get_search_client()

    # ------------------------------------------------------------------ #
    # Upload / Upsert
    # ------------------------------------------------------------------ #

    def upsert_documents(
        self,
        documents: List[Document],
        namespace: str = "default",
    ) -> int:

        if not documents:
            return 0

        texts = [
            document.page_content
            for document in documents
        ]

        embeddings = self.embedder.embed_documents(texts)

        if len(embeddings) != len(documents):
            raise RuntimeError(
                "Number of generated embeddings does not match "
                "number of documents."
            )

        search_documents = []

        for document, embedding in zip(
            documents,
            embeddings,
        ):
            metadata = sanitize_metadata(
                document.metadata
            )

            rfp_id = str(
                metadata.get("rfp_id", "")
            )

            if not rfp_id:
                raise ValueError(
                    "Document is missing required metadata: rfp_id"
                )

            chunk_id = metadata.get(
                "chunk_id",
                0,
            )

            document_id = generate_vector_id(
                rfp_id=rfp_id,
                chunk_id=chunk_id,
            )

            search_document = {
                "id": document_id,

                "rfp_id": rfp_id,

                "chunk_id": int(chunk_id),

                "filename": str(
                    metadata.get("filename", "")
                ),

                "doc_hash": str(
                    metadata.get("doc_hash", "")
                ),

                "ingested_at": str(
                    metadata.get("ingested_at", "")
                ),

                "source_type": str(
                    metadata.get("source_type", "")
                ),

                "kb_id": metadata.get("kb_id"),

                "doc_type": str(
                    metadata.get("doc_type", "")
                ),

                "content": document.page_content,

                "content_vector": embedding,
            }

            search_documents.append(
                search_document
            )

        total = 0

        for start in range(
            0,
            len(search_documents),
            UPLOAD_BATCH_SIZE,
        ):
            batch = search_documents[
                start:start + UPLOAD_BATCH_SIZE
            ]

            self._upload_batch(batch)

            total += len(batch)

        logger.info(
            "Uploaded %d documents to Azure AI Search.",
            total,
        )

        return total

    # ------------------------------------------------------------------ #
    # Upload batch
    # ------------------------------------------------------------------ #

    @with_retry(
        max_attempts=3,
        base_delay=1.0,
    )
    def _upload_batch(
        self,
        batch: List[Dict],
    ):

        results = self.client.upload_documents(
            documents=batch
        )

        failed = [
            result
            for result in results
            if not result.succeeded
        ]

        if failed:
            errors = []

            for result in failed:
                errors.append(
                    getattr(
                        result,
                        "error_message",
                        "Unknown indexing error",
                    )
                )

            raise RuntimeError(
                "Azure AI Search failed to index "
                f"{len(failed)} documents: {errors}"
            )

    # ------------------------------------------------------------------ #
    # Similarity search
    # ------------------------------------------------------------------ #

    @with_retry(
        max_attempts=3,
        base_delay=1.0,
    )
    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
        metadata_filter: Optional[Dict] = None,
    ) -> List[Document]:

        if not query or not query.strip():
            return []

        query_embedding = self.embedder.embed_query(
            query
        )

        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector",
        )

        filter_expression = self._build_filter(
            namespace=namespace,
            metadata_filter=metadata_filter,
        )

        results = self.client.search(
            search_text=None,
            vector_queries=[
                vector_query
            ],
            filter=filter_expression,
            select=[
                "id",
                "rfp_id",
                "chunk_id",
                "filename",
                "doc_hash",
                "ingested_at",
                "source_type",
                "kb_id",
                "doc_type",
                "content",
            ],
            top=top_k,
        )

        documents = []

        for result in results:

            metadata = {
                "rfp_id": result.get(
                    "rfp_id"
                ),

                "chunk_id": result.get(
                    "chunk_id"
                ),

                "filename": result.get(
                    "filename"
                ),

                "doc_hash": result.get(
                    "doc_hash"
                ),

                "ingested_at": result.get(
                    "ingested_at"
                ),

                "source_type": result.get(
                    "source_type"
                ),

                "kb_id": result.get(
                    "kb_id"
                ),

                "doc_type": result.get(
                    "doc_type"
                ),

                "score": result.get(
                    "@search.score",
                    0.0,
                ),
            }

            metadata = {
                key: value
                for key, value in metadata.items()
                if value is not None
            }

            documents.append(
                Document(
                    page_content=result.get(
                        "content",
                        "",
                    ),
                    metadata=metadata,
                )
            )

        logger.info(
            "Azure AI Search returned %d documents "
            "for query.",
            len(documents),
        )

        return documents

    # ------------------------------------------------------------------ #
    # Build Azure Search filter
    # ------------------------------------------------------------------ #

    def _build_filter(
        self,
        namespace: str,
        metadata_filter: Optional[Dict],
    ) -> Optional[str]:

        filters = []

        # -------------------------------------------------------------- #
        # Replace Pinecone namespace
        # -------------------------------------------------------------- #

        if namespace and namespace != "default":

            if namespace.startswith("rfp-"):

                rfp_id = namespace[
                    len("rfp-"):
                ]

                filters.append(
                    "rfp_id eq "
                    f"'{self._escape_filter_value(rfp_id)}'"
                )

            elif namespace == "knowledge-base":

                filters.append(
                    "source_type eq "
                    "'knowledge_base'"
                )

        # -------------------------------------------------------------- #
        # Additional metadata filters
        # -------------------------------------------------------------- #

        if metadata_filter:

            for key, value in metadata_filter.items():

                if value is None:
                    continue

                if isinstance(value, bool):

                    filters.append(
                        f"{key} eq "
                        f"{str(value).lower()}"
                    )

                elif isinstance(value, str):

                    filters.append(
                        f"{key} eq "
                        f"'{self._escape_filter_value(value)}'"
                    )

                else:

                    filters.append(
                        f"{key} eq {value}"
                    )

        if not filters:
            return None

        return " and ".join(filters)

    @staticmethod
    def _escape_filter_value(
        value: str,
    ) -> str:
        return value.replace(
            "'",
            "''",
        )

    # ------------------------------------------------------------------ #
    # Delete RFP
    # ------------------------------------------------------------------ #

    def delete_rfp(
        self,
        rfp_id: str,
        namespace: Optional[str] = None,
    ):

        rfp_id = str(rfp_id)

        filter_expression = (
            "rfp_id eq "
            f"'{self._escape_filter_value(rfp_id)}'"
        )

        results = self.client.search(
            search_text="*",
            filter=filter_expression,
            select=["id"],
        )

        ids = [
            {
                "id": result["id"]
            }
            for result in results
        ]

        if not ids:
            logger.info(
                "No Azure AI Search documents found "
                "for rfp_id=%s.",
                rfp_id,
            )
            return

        for start in range(
            0,
            len(ids),
            UPLOAD_BATCH_SIZE,
        ):

            batch = ids[
                start:start + UPLOAD_BATCH_SIZE
            ]

            delete_results = (
                self.client.delete_documents(
                    documents=batch
                )
            )

            failed = [
                result
                for result in delete_results
                if not result.succeeded
            ]

            if failed:
                raise RuntimeError(
                    "Failed to delete "
                    f"{len(failed)} Azure AI Search "
                    "documents."
                )

        logger.info(
            "Deleted %d Azure AI Search documents "
            "for rfp_id=%s.",
            len(ids),
            rfp_id,
        )

    # ------------------------------------------------------------------ #
    # Delete namespace
    # ------------------------------------------------------------------ #

    def delete_namespace(
        self,
        namespace: str,
    ):

        if namespace.startswith("rfp-"):

            rfp_id = namespace[
                len("rfp-"):
            ]

            self.delete_rfp(
                rfp_id=rfp_id,
                namespace=namespace,
            )

            return

        if namespace == "knowledge-base":

            filter_expression = (
                "source_type eq "
                "'knowledge_base'"
            )

            results = self.client.search(
                search_text="*",
                filter=filter_expression,
                select=["id"],
            )

            ids = [
                {
                    "id": result["id"]
                }
                for result in results
            ]

            for start in range(
                0,
                len(ids),
                UPLOAD_BATCH_SIZE,
            ):

                batch = ids[
                    start:start + UPLOAD_BATCH_SIZE
                ]

                self.client.delete_documents(
                    documents=batch
                )

            logger.info(
                "Deleted %d knowledge-base "
                "documents.",
                len(ids),
            )

            return

        logger.warning(
            "Unknown Azure AI Search namespace: %s",
            namespace,
        )

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #

    def describe(self):

        results = self.client.search(
            search_text="*",
            include_total_count=True,
            top=0,
        )

        return {
            "document_count": (
                results.get_count() or 0
            )
        }
