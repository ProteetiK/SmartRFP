from concurrent.futures import ThreadPoolExecutor
import time

from agents.extractor import extract_requirements
from agents.rag_agent import RAGAgent
from agents.pricing_agent import fetch_pricing
from agents.draft_generator import generate_draft
from backend import crud
from backend.config import settings
from backend.rag.ingestion import DocumentIngestion

from langsmith import traceable, trace
from langsmith.run_helpers import get_current_run_tree
from evaluation import evaluate_pipeline

from metrics import (
    PIPELINE_RUNS,
    PIPELINE_FAILURES,
    PIPELINE_RUNTIME,
    REQUIREMENTS_EXTRACTED,
    SECTIONS_GENERATED,
    HALLUCINATION_FLAGS,
    STAGE_LATENCY,
    EVAL_SCORE,
    EVAL_BELOW_THRESHOLD,
)

import logging

logger = logging.getLogger("smartrfp.pipeline")
logger.setLevel(logging.INFO)


class Repository:
    def __init__(self, session):
        if session is None:
            raise ValueError("Repository requires a SQLAlchemy session (PostgreSQL). "
                              "The SQLite fallback has been removed.")
        self.session = session

    def save_requirements(self, rfp_id, requirements):
        crud.save_requirements(self.session, rfp_id, requirements)

    def save_pricing(self, rfp_id, pricing):
        crud.save_pricing(self.session, rfp_id, pricing)

    def save_draft_sections(self, rfp_id, sections):
        crud.save_draft_sections(self.session, rfp_id, sections)

    def save_evaluation(self, rfp_id, metrics):
        crud.save_evaluation_metrics(self.session, rfp_id, metrics)

    def update_evaluation(self, rfp_id, patch: dict):
        crud.update_evaluation_metrics(self.session, rfp_id, patch)

    def set_ragas_status(self, rfp_id, status, error=None, attempts=None):
        crud.set_ragas_status(self.session, rfp_id, status, error=error, attempts=attempts)

    def flag_below_threshold(self, rfp_id, notes):
        crud.flag_below_threshold(self.session, rfp_id, notes)

    def update_metrics(self, rfp_id, reqs, flags, status):
        crud.update_rfp_metrics(self.session, rfp_id, reqs, flags, status)

    def set_error(self, rfp_id, message):
        crud.set_rfp_error(self.session, rfp_id, message)

    def log(self, rfp_id, action, actor, detail=""):
        crud.log_action(self.session, rfp_id, action, actor, detail)


def _ingest_rfp_document(rfp_id, raw_text, filename):
    try:
        DocumentIngestion().reindex_document(
            text=raw_text, rfp_id=rfp_id, filename=filename or f"rfp_{rfp_id}",
        )
    except Exception:
        logger.exception("Pinecone ingestion failed for rfp_id=%s; retrieval will "
                         "fall back to the shared knowledge base only.", rfp_id)


def _apply_ragas_gate(repo, rfp_id, evaluation: dict):
    try:
        repo.update_evaluation(rfp_id, {
            "ragas_faithfulness": evaluation.get("faithfulness", 0),
            "ragas_answer_relevancy": evaluation.get("answer_relevancy", 0),
            "ragas_context_precision": evaluation.get("context_precision", 0),
            "ragas_context_recall": evaluation.get("context_recall", 0),
        })
        repo.set_ragas_status(rfp_id, "completed", attempts=1)

        breaches = []
        checks = [
            ("faithfulness", evaluation.get("faithfulness", 0), settings.EVAL_MIN_FAITHFULNESS),
            ("answer_relevancy", evaluation.get("answer_relevancy", 0), settings.EVAL_MIN_ANSWER_RELEVANCY),
            ("context_precision", evaluation.get("context_precision", 0), settings.EVAL_MIN_CONTEXT_PRECISION),
            ("context_recall", evaluation.get("context_recall", 0), settings.EVAL_MIN_CONTEXT_RECALL),
            ("proposal_completeness", evaluation.get("proposal_completeness", 0), settings.EVAL_MIN_COMPLETENESS),
        ]
        for name, value, minimum in checks:
            EVAL_SCORE.labels(metric=name).set(value or 0)
            if (value or 0) < minimum:
                breaches.append(f"{name}={value:.2f} < {minimum:.2f}")

        if breaches:
            EVAL_BELOW_THRESHOLD.inc()
            repo.flag_below_threshold(
                rfp_id, "Below configured quality threshold: " + "; ".join(breaches))
    except Exception:
        logger.exception("RAGAS threshold gating failed for rfp_id=%s", rfp_id)
        try:
            repo.set_ragas_status(rfp_id, "failed", error="threshold gating raised an exception")
        except Exception:
            pass


@traceable(
    name="SmartRFP Pipeline",
    run_type="chain",
)
def run_pipeline(db, rfp_id, raw_text, filename=None, use_web_search=True, progress=None):
    repo = Repository(db)
    logger.info("********** PIPELINE STARTED **********")
    print("********** PIPELINE STARTED **********")
    logger.info("=" * 80)
    logger.info("SMART RFP PIPELINE STARTED")
    logger.info("RFP ID      : %s", rfp_id)
    logger.info("Filename    : %s", filename)
    logger.info("Web Search  : %s", use_web_search)
    logger.info("=" * 80)
    stage_latencies = {}

    def _stage(name):
        """Context manager-ish timer: with _stage("Parsing") as t: ..."""
        return _StageTimer(name, stage_latencies)

    try:
        PIPELINE_RUNS.inc()
        start_time = time.perf_counter()

        def step(label, frac):
            if progress:
                progress(label, frac)

        # ---- Ingest the RFP's own text into its Pinecone namespace --------
        step("Indexing document (Pinecone)…", 0.05)
        with _stage("Pinecone Ingestion"):
            _ingest_rfp_document(rfp_id, raw_text, filename)

        # ---- F1: parse & extract requirements ------------------------------
        step("Parsing & extracting requirements (F1)…", 0.15)
        with trace("Requirement Extraction", run_type="chain"), _stage("Requirement Extraction"):
            requirements = extract_requirements(raw_text)
        repo.save_requirements(rfp_id, requirements)
        repo.log(rfp_id, "Parsed", "System",
                f"{len(requirements)} requirements extracted")

        # ---- F2 + F3: run both agents in PARALLEL --------------------------
        step("Running Agent 1 (RAG) and Agent 2 (Pricing) in parallel…", 0.45)
        with trace("Parallel Agent Execution", run_type="chain"), _stage("Parallel Agent Execution"):
            rag_agent = RAGAgent(rfp_id=rfp_id)

            with ThreadPoolExecutor(max_workers=2) as ex:
                parent_run = get_current_run_tree()
                pricing_future = ex.submit(fetch_pricing, rfp_id, raw_text, parent_run)
                pricing_lines, web_insight = pricing_future.result()

        if not use_web_search:
            web_insight = None

        repo.save_pricing(rfp_id, pricing_lines)
        repo.log(rfp_id, "Agents run", "System",
                f"RAG ready over namespaces {rag_agent._namespaces}; "
                f"{len(pricing_lines)} pricing lines fetched")

        # ---- F4: synthesize the draft ---------------------------------------
        step("Synthesizing draft (F4)…", 0.8)
        with _stage("Draft Generation"):
            sections = generate_draft(requirements, rag_agent, pricing_lines, web_insight)
        repo.save_draft_sections(rfp_id, sections)

        # ---------------- Evaluation (deterministic + RAGAS-style) ----------
        with _stage("Evaluation"):
            current_run = get_current_run_tree()
            trace_id = str(current_run.trace_id) if current_run else None
            runtime = time.perf_counter() - start_time

            evaluation = evaluate_pipeline(
                requirements=requirements,
                sections=sections,
                pricing_lines=pricing_lines,
                runtime_seconds=runtime,
                rag_agent=rag_agent,
            )
            evaluation["retrieved_docs_count"] = sum(
                len(s.get("retrieved_docs", [])) for s in sections
            )
            evaluation["stage_latencies"] = stage_latencies

        repo.save_evaluation(rfp_id, evaluation)
        _apply_ragas_gate(repo, rfp_id, evaluation)

        num_flags = evaluation["hallucination_flags"]

        repo.update_metrics(rfp_id, len(requirements), num_flags, "In Review")
        repo.log(rfp_id, "Draft generated", "System",
                f"{len(sections)} sections, {num_flags} flags")

        step("Done.", 1.0)
        elapsed = time.perf_counter() - start_time

       

        PIPELINE_RUNTIME.observe(elapsed)
        REQUIREMENTS_EXTRACTED.observe(len(requirements))
        SECTIONS_GENERATED.observe(len(sections))
        HALLUCINATION_FLAGS.set(num_flags)

        # ----------------------------------------------------------------------
        # Production Success Logging
        # ----------------------------------------------------------------------
        logger.info("=" * 80)
        logger.info("SMART RFP PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("RFP ID        : %s", rfp_id)
        logger.info("Requirements  : %d", len(requirements))
        logger.info("Draft Sections: %d", len(sections))
        logger.info("Pricing Lines : %d", len(pricing_lines))
        logger.info("Flags         : %d", num_flags)
        logger.info("Web Search    : %s", bool(web_insight))
        logger.info("Trace ID      : %s", trace_id)
        logger.info("Runtime       : %.2f seconds", elapsed)
        logger.info("=" * 80)

        return {
            "requirements": len(requirements),
            "sections": len(sections),
            "flags": num_flags,
            "pricing_lines": len(pricing_lines),
            "web_insight": bool(web_insight),
            "evaluation": evaluation,
            "trace_id": trace_id,
        }
    except Exception as exc:
        logger.exception("PIPELINE FAILED")
        PIPELINE_FAILURES.inc()
        try:
            repo.set_error(rfp_id, str(exc))
            repo.log(rfp_id, "Pipeline failed", "System", str(exc)[:300])
        except Exception:
            logger.exception("Additionally failed to record pipeline failure for rfp_id=%s", rfp_id)
        raise


class _StageTimer:

    def __init__(self, name, sink: dict):
        self.name = name
        self.sink = sink
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        logger.info("=" * 70)
        logger.info("STARTING STAGE : %s", self.name)
        logger.info("=" * 70)
        return self

    def __exit__(self, exc_type, exc, tb):
        elapsed = time.perf_counter() - self._start

        self.sink[self.name] = round(elapsed, 3)

        STAGE_LATENCY.labels(stage=self.name).observe(elapsed)

        if exc:
            logger.exception(
                "FAILED STAGE : %s (%.2f seconds)",
                self.name,
                elapsed,
            )
        else:
            logger.info(
                "COMPLETED STAGE : %s (%.2f seconds)",
                self.name,
                elapsed,
            )

        return False