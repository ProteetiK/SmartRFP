from __future__ import annotations

import logging
from typing import Dict, List, Optional

from azure.search.documents.models import VectorizedQuery
from langchain_core.documents import Document

from backend.rag.embedding import get_embedding_service
from backend.rag.azure_search_client import get_search_client
from backend.rag.utils import (
    generate_vector_id,
    sanitize_metadata,
    with_retry,
)

logger = logging.getLogger("smartrfp.rag")

UPLOAD_BATCH_SIZE = 100


class VectorStore:

    def __init__(self):
        self.embedder = get_embedding_service()
        self.client = get_search_client()

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

        texts = [
            doc.page_content
            for doc in documents
        ]

        embeddings = self.embedder.embed_documents(texts)

        search_documents = []

        for doc, embedding in zip(documents, embeddings):

            rfp_id = str(
                doc.metadata["rfp_id"]
            )

            chunk_id = str(
                doc.metadata["chunk_id"]
            )

            document_id = generate_vector_id(
                rfp_id=rfp_id,
                chunk_id=chunk_id,
            )

            metadata = sanitize_metadata(
                {
                    **doc.metadata,
                    "text": doc.page_content,
                }
            )

            search_documents.append(
                {
                    "id": document_id,
                    "rfp_id": rfp_id,
                    "chunk_id": chunk_id,
                    "content": doc.page_content,
                    "content_vector": embedding,
                    **metadata,
                }
            )

        total = 0

        for i in range(
            0,
            len(search_documents),
            UPLOAD_BATCH_SIZE,
        ):
            batch = search_documents[
                i:i + UPLOAD_BATCH_SIZE
            ]

            self._upload_batch(batch)

            total += len(batch)

        logger.info(
            "Uploaded %d documents to Azure AI Search index.",
            total,
        )

        return total

    # ------------------------------------------------------------------ #
    # UPLOAD
    # ------------------------------------------------------------------ #

    @with_retry(
        max_attempts=3,
        base_delay=1.0,
    )
    def _upload_batch(
        self,
        batch: List[Dict],
    ):

        result = self.client.upload_documents(
            documents=batch
        )

        failed = [
            item
            for item in result
            if not item.succeeded
        ]

        if failed:
            raise RuntimeError(
                f"Azure AI Search failed to index "
                f"{len(failed)} documents."
            )

    # ------------------------------------------------------------------ #
    # SEARCH
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

        query_embedding = (
            self.embedder.embed_query(query)
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
                "content",
            ],
            top=top_k,
        )

        documents = []

        for result in results:

            metadata = {
                "rfp_id": result.get("rfp_id"),
                "chunk_id": result.get("chunk_id"),
                "score": result.get("@search.score", 0.0),
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

        return documents

    # ------------------------------------------------------------------ #
    # FILTER
    # ------------------------------------------------------------------ #

    def _build_filter(
        self,
        namespace: str,
        metadata_filter: Optional[Dict],
    ) -> Optional[str]:

        filters = []

        if namespace and namespace != "default":

            # Existing SmartRFP namespace:
            # rfp_namespace(123) -> e.g. "rfp_123"

            if namespace.startswith("rfp_"):
                rfp_id = namespace.replace(
                    "rfp_",
                    "",
                    1,
                )

                filters.append(
                    f"rfp_id eq '{rfp_id}'"
                )

        if metadata_filter:

            for key, value in metadata_filter.items():

                if isinstance(value, str):
                    filters.append(
                        f"{key} eq '{value}'"
                    )
                elif isinstance(value, bool):
                    filters.append(
                        f"{key} eq "
                        f"{str(value).lower()}"
                    )
                else:
                    filters.append(
                        f"{key} eq {value}"
                    )

        if not filters:
            return None

        return " and ".join(filters)

    # ------------------------------------------------------------------ #
    # DELETE RFP
    # ------------------------------------------------------------------ #

    def delete_rfp(
        self,
        rfp_id: str,
        namespace: Optional[str] = None,
    ):

        rfp_id = str(rfp_id)

        results = self.client.search(
            search_text="*",
            filter=f"rfp_id eq '{rfp_id}'",
            select=["id"],
        )

        ids = [
            {
                "id": result["id"]
            }
            for result in results
        ]

        if ids:
            self.client.delete_documents(
                documents=ids
            )

        logger.info(
            "Deleted RFP %s from Azure AI Search.",
            rfp_id,
        )

    # ------------------------------------------------------------------ #
    # DELETE NAMESPACE
    # ------------------------------------------------------------------ #

    def delete_namespace(
        self,
        namespace: str,
    ):

        if namespace.startswith("rfp_"):

            rfp_id = namespace.replace(
                "rfp_",
                "",
                1,
            )

            self.delete_rfp(rfp_id)

    # ------------------------------------------------------------------ #
    # STATS
    # ------------------------------------------------------------------ #

    def describe(self):

        results = self.client.search(
            search_text="*",
            include_total_count=True,
            top=0,
        )

        return {
            "document_count":
                results.get_count() or 0
        }
