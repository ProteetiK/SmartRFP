from statistics import mean

from backend.llm import llm_available

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ragas_eval import run_ragas_eval

CONFIDENCE_MAP = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}

EXPECTED_SECTIONS = {
    "Executive Summary",
    "Company Overview",
    "Understanding of Requirements",
    "Proposed Technical Solution",
    "Implementation Plan",
    "Security",
    "Deliverables",
    "Timeline",
    "Pricing",
    "Conclusion",
}


def similarity(a, b):
    if not a or not b:
        return 0.0

    a = str(a).strip()
    b = str(b).strip()

    if not a or not b:
        return 0.0

    try:
        vect = TfidfVectorizer(stop_words="english")

        X = vect.fit_transform([a, b])

        return float(cosine_similarity(X[0], X[1])[0][0])

    except Exception:
        return 0.0


def evaluate_pipeline(
    requirements,
    sections,
    pricing_lines,
    runtime_seconds,
    rag_agent=None,
):

    # ----------------------------------------------------
    # Proposal Completeness
    # ----------------------------------------------------

    generated = {
        s["section_title"]
        for s in sections
    }

    proposal_completeness = round(
        len(generated & EXPECTED_SECTIONS) / len(EXPECTED_SECTIONS), 2)

    # ----------------------------------------------------
    # Confidence
    # ----------------------------------------------------

    confidence_scores = [
        CONFIDENCE_MAP.get(
            s.get("confidence", "").lower(),
            0.4,
        )
        for s in sections
    ]

    average_confidence = round(
        mean(confidence_scores),
        2,
    ) if confidence_scores else 0

    # ----------------------------------------------------
    # Flags
    # ----------------------------------------------------

    hallucination_flags = sum(
        bool(s.get("flag_type"))
        for s in sections
    )

    # ----------------------------------------------------
    # Context Coverage
    # ----------------------------------------------------

    rag_sections = [
        s
        for s in sections
        if s.get("retrieved_docs")
    ]

    context_coverage = round(
        len(rag_sections) / len(sections),
        2,
    ) if sections else 0

    # ----------------------------------------------------
    # Pricing
    # ----------------------------------------------------

    if pricing_lines:

        fresh = sum(
            not p["stale"]
            for p in pricing_lines
        )

        pricing_freshness = round(
            fresh / len(pricing_lines),
            2,
        )

    else:

        pricing_freshness = 0

    # ----------------------------------------------------
    # Metadata
    # ----------------------------------------------------

    kb_documents = sum(len(sec.get("retrieved_docs", [])) for sec in rag_sections)

    pricing_items = len(pricing_lines)

    llm_demo_mode = not llm_available()

    llm_calls = 5

    # ----------------------------------------------------
    # Hit Rate
    # ----------------------------------------------------

    hits = []

    for sec in rag_sections:

        docs = sec.get("retrieved_docs", [])

        hits.append(
            int(len(docs) > 0)
        )

    hit_rate = round(
        mean(hits),
        2,
    ) if hits else 0

    # ----------------------------------------------------
    # MRR
    # ----------------------------------------------------

    mrr_scores = []

    for sec in rag_sections:

        docs = sec.get("retrieved_docs", [])

        req = sec.get("requirement")

        if not docs or not req:
            continue

        reciprocal_rank = 0

        for rank, doc in enumerate(docs, start=1):

            score = similarity(
                req,
                doc.get("content", "")
            )

            if score >= 0.20:
                reciprocal_rank = 1 / rank
                break

        mrr_scores.append(reciprocal_rank)

    mrr = round(
        mean(mrr_scores),
        2,
    ) if mrr_scores else 0

    # ----------------------------------------------------
    # Chunk Overlap
    # ----------------------------------------------------

    overlap_scores = []

    for sec in rag_sections:

        docs = sec.get("retrieved_docs", [])

        for i in range(len(docs)):

            for j in range(i + 1, len(docs)):

                overlap_scores.append(

                    similarity(
                        docs[i].get("content", ""),
                        docs[j].get("content", ""),
                    )

                )

    chunk_overlap = round(
        mean(overlap_scores),
        2,
    ) if overlap_scores else 0

    # ----------------------------------------------------
    # Build RAGAS Dataset
    # ----------------------------------------------------

    ragas_dataset = []

    if rag_agent:

        for sec in rag_sections:

            requirement = sec.get("requirement")

            docs = sec.get("retrieved_docs", [])

            if not requirement:
                continue

            contexts = [
                d.get("content", "")
                for d in docs
                if d.get("content")
            ]

            if not contexts:
                continue

            ground_truth = rag_agent.get_ground_truth(requirement)

            if not ground_truth:
                continue

            ragas_dataset.append(
                {
                    "question": requirement,
                    "answer": sec.get("content", ""),
                    "contexts": contexts,
                    "ground_truth": ground_truth,
                }
            )

    # ----------------------------------------------------
    # Run RAGAS
    # ----------------------------------------------------

    if ragas_dataset:

        ragas_results = run_ragas_eval(
            ragas_dataset
        )

    else:

        ragas_results = {
            "faithfulness": 0,
            "answer_relevancy": 0,
            "context_precision": 0,
            "context_recall": 0,
        }

    # ----------------------------------------------------
    # Return
    # ----------------------------------------------------

    return {

        "requirements": len(requirements),

        "sections_generated": len(sections),

        "proposal_completeness": proposal_completeness,

        "average_confidence": average_confidence,

        "context_coverage": context_coverage,

        "hallucination_flags": hallucination_flags,

        "pricing_freshness": pricing_freshness,

        "runtime_seconds": round(runtime_seconds, 2),

        "knowledge_documents": kb_documents,

        "pricing_items": pricing_items,

        "llm_calls": llm_calls,

        "demo_mode": llm_demo_mode,

        "mrr": mrr,

        "hit_rate": hit_rate,

        "chunk_overlap": chunk_overlap,

        "faithfulness": ragas_results.get("faithfulness", 0),

        "answer_relevancy": ragas_results.get(
            "answer_relevancy",
            0,
        ),

        "context_precision": ragas_results.get(
            "context_precision",
            0,
        ),

        "context_recall": ragas_results.get(
            "context_recall",
            0,
        ),
    }