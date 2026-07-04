from datasets import Dataset
from backend.llm import chat, LLMUnavailable  # production Groq/OpenAI-failover wrapper
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def similarity(a: str, b: str) -> float:
    """
    Compute cosine similarity between two text strings using TF-IDF.
    Returns a score between 0 and 1.
    """
    if not a or not b:
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english")

    X = vectorizer.fit_transform([a, b])

    return float(cosine_similarity(X[0], X[1])[0][0])



def groq_faithfulness(question, answer, contexts):
    """
    LLM-based judge using Groq ONLY for faithfulness.
    Returns score 0-1.
    """

    context_text = "\n".join(contexts)

    system_prompt = (
        "You are a strict evaluator of RAG system faithfulness. "
        "You must check whether the answer is fully supported by the context."
    )

    user_prompt = f"""
Question:
{question}

Answer:
{answer}

Context:
{context_text}

Return ONLY a number between 0 and 1:
- 1 = fully faithful (everything supported)
- 0 = hallucinated or unsupported
"""

    try:
        resp = chat(system_prompt, user_prompt, temperature=0)

        # extract numeric score safely
        score = float(resp.strip().split()[0])
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.0

def run_ragas_eval(dataset_dict, use_llm_faithfulness=True):
    dataset = Dataset.from_list(dataset_dict)

    faithfulness_scores = []
    relevancy_scores = []
    precision_scores = []
    recall_scores = []

    for row in dataset:
        q = row["question"]
        a = row["answer"]
        ctx = row["contexts"]

        context_text = " ".join(ctx)

        # ---------------- FAITHFULNESS (optional Groq LLM judge) ----------
        if use_llm_faithfulness:
            f_score = groq_faithfulness(q, a, ctx)
        else:
            f_score = similarity(a, context_text)

        faithfulness_scores.append(f_score)

        # ---------------- ANSWER RELEVANCY ----------------
        relevancy_scores.append(similarity(q, a))

        # ---------------- CONTEXT PRECISION ----------------
        precision_scores.append(
            sum(similarity(a, c) > 0.3 for c in ctx) / len(ctx) if ctx else 0
        )

        # ---------------- CONTEXT RECALL ----------------
        recall_scores.append(
            sum(similarity(q, c) > 0.3 for c in ctx) / len(ctx) if ctx else 0
        )

    return {
        "faithfulness": sum(faithfulness_scores) / len(faithfulness_scores),
        "answer_relevancy": sum(relevancy_scores) / len(relevancy_scores),
        "context_precision": sum(precision_scores) / len(precision_scores),
        "context_recall": sum(recall_scores) / len(recall_scores),
        "mode": "groq-faithfulness" if use_llm_faithfulness else "heuristic",
    }