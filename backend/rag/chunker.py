"""
Production Document Chunker for SmartRFP

Responsibilities
----------------
1. Split extracted document text into semantic chunks
2. Preserve metadata
3. Support configurable chunk size & overlap
4. Return LangChain Document objects
"""

from typing import List, Dict, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentChunker:
    """
    Splits documents into overlapping chunks for RAG retrieval.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                ".",
                " ",
                "",
            ],
        )

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict] = None,
    ) -> List[Document]:
        """
        Convert raw text into LangChain Documents.

        Parameters
        ----------
        text : str
            Full extracted text.

        metadata : dict
            Document metadata.

        Returns
        -------
        List[Document]
        """

        metadata = metadata or {}

        chunks = self.text_splitter.split_text(text)

        documents = []

        for idx, chunk in enumerate(chunks):

            chunk_metadata = metadata.copy()

            chunk_metadata.update(
                {
                    "chunk_id": idx,
                    "chunk_size": len(chunk),
                }
            )

            documents.append(
                Document(
                    page_content=chunk,
                    metadata=chunk_metadata,
                )
            )

        return documents

    def chunk_documents(
        self,
        documents: List[Document],
    ) -> List[Document]:
        """
        Split LangChain Documents into smaller chunks.
        """

        return self.text_splitter.split_documents(documents)

    @staticmethod
    def statistics(chunks: List[Document]) -> Dict:
        """
        Return useful chunk statistics.
        """

        if not chunks:
            return {
                "total_chunks": 0,
                "average_chunk_size": 0,
            }

        sizes = [
            len(doc.page_content)
            for doc in chunks
        ]

        return {
            "total_chunks": len(chunks),
            "average_chunk_size": int(sum(sizes) / len(sizes)),
            "largest_chunk": max(sizes),
            "smallest_chunk": min(sizes),
        }