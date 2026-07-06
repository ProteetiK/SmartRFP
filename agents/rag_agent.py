from __future__ import annotations

from typing import Dict, List, Optional, Union

from backend.llm import chat
from backend.rag.prompt_builder import PromptBuilder
from backend.rag.retriever import Retriever
from backend.rag.utils import KB_NAMESPACE, rfp_namespace
from metrics import RAG_EMPTY, RAG_QUERIES, RAG_RESULTS


def _doc_to_dict(doc) -> Dict:
    meta = doc.metadata or {}
    return {
        "title": meta.get("filename") or meta.get("title") or "Untitled",
        "doc_type": meta.get("doc_type") or meta.get("source_type") or "rfp_content",
        "content": doc.page_content or "",
        "score": meta.get("score", 0.0),
    }


class RAGAgent:

    def __init__(self, rfp_id: Optional[Union[str, int]] = None, top_k: Optional[int] = None):
        self.rfp_id = rfp_id
        self.retriever = Retriever(top_k=top_k)
        self._namespaces = [KB_NAMESPACE]
        if rfp_id is not None:
            self._namespaces = [rfp_namespace(rfp_id), KB_NAMESPACE]

    # ------------------------------------------------------------------ #
    # Retrieval -- used by draft_generator.py for every grounded section
    # ------------------------------------------------------------------ #
    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[Dict]:
        RAG_QUERIES.inc()
        try:
            if top_k:
                original = self.retriever.top_k
                self.retriever.top_k = top_k
                try:
                    docs = self.retriever.retrieve_multi(query, namespaces=self._namespaces)
                finally:
                    self.retriever.top_k = original
            else:
                docs = self.retriever.retrieve_multi(query, namespaces=self._namespaces)
        except Exception:
            # Pinecone hiccup / embedding model not loaded / index missing --
            # degrade to "no grounding found" rather than failing the draft.
            docs = []

        RAG_RESULTS.observe(len(docs))
        if not docs:
            RAG_EMPTY.inc()
        return [_doc_to_dict(d) for d in docs]

    # ------------------------------------------------------------------ #
    # Ground-truth proxy -- used by evaluation.py to build the RAGAS dataset
    # ------------------------------------------------------------------ #
    def get_ground_truth(self, requirement: str) -> Optional[str]:
        docs = self.retrieve(requirement, top_k=3)
        if not docs:
            return None
        return "\n".join(d["content"] for d in docs if d.get("content"))[:2000] or None

    def answer(self, question: str, namespace: Optional[str] = None) -> str:
        ns = namespace or (self._namespaces[0] if self._namespaces else KB_NAMESPACE)
        documents = self.retriever.retrieve(query=question, namespace=ns)
        context = self.retriever.build_context(documents)
        prompt = PromptBuilder.build_rag_prompt(query=question, context=context)
        return chat(
            system_prompt="You are an expert proposal assistant.",
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=1500,
        )