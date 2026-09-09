from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    REGISTRY,
)

def _metric(factory, name, description):
    try:
        return factory(name, description)
    except ValueError:
        return REGISTRY._names_to_collectors[name]


# -------------------------------------------------------
# Pipeline Metrics
# -------------------------------------------------------

PIPELINE_RUNS = _metric(
    Counter,
    "smartrfp_pipeline_runs_total",
    "Total pipeline executions"
)

PIPELINE_FAILURES = _metric(
    Counter,
    "smartrfp_pipeline_failures_total",
    "Failed pipeline executions"
)

PIPELINE_RUNTIME = _metric(
    Histogram,
    "smartrfp_pipeline_runtime_seconds",
    "Pipeline execution time"
)

# -------------------------------------------------------
# LLM Metrics
# -------------------------------------------------------

LLM_REQUESTS = _metric(
    Counter,
    "smartrfp_llm_requests_total",
    "Total LLM requests"
)

LLM_ERRORS = _metric(
    Counter,
    "smartrfp_llm_errors_total",
    "Total LLM failures"
)

LLM_LATENCY = _metric(
    Histogram,
    "smartrfp_llm_latency_seconds",
    "LLM response time"
)

LLM_DEMO_MODE = _metric(
    Counter,
    "smartrfp_demo_mode_total",
    "Fallback demo responses"
)

# -------------------------------------------------------
# RAG Metrics
# -------------------------------------------------------

RAG_QUERIES = _metric(
    Counter,
    "smartrfp_rag_queries_total",
    "Total retrieval requests"
)

RAG_RESULTS = _metric(
    Histogram,
    "smartrfp_rag_results",
    "Documents returned by retrieval"
)

RAG_EMPTY = _metric(
    Counter,
    "smartrfp_rag_empty_total",
    "Queries returning no KB documents"
)

# -------------------------------------------------------
# Pricing Metrics
# -------------------------------------------------------

PRICING_REQUESTS = _metric(
    Counter,
    "smartrfp_pricing_requests_total",
    "Pricing agent requests"
)

PRICING_ITEMS = _metric(
    Histogram,
    "smartrfp_pricing_items",
    "Pricing items returned"
)

# -------------------------------------------------------
# Proposal Metrics
# -------------------------------------------------------

REQUIREMENTS_EXTRACTED = _metric(
    Histogram,
    "smartrfp_requirements_extracted",
    "Requirements extracted from RFP"
)

SECTIONS_GENERATED = _metric(
    Histogram,
    "smartrfp_sections_generated",
    "Proposal sections generated"
)

HALLUCINATION_FLAGS = _metric(
    Gauge,
    "smartrfp_hallucination_flags",
    "Number of hallucination flags"
)

# -------------------------------------------------------
# Guardrail Metrics
# -------------------------------------------------------

def _metric_labeled(factory, name, description, labelnames):
    try:
        return factory(name, description, labelnames)
    except ValueError:
        return REGISTRY._names_to_collectors[name]


GUARDRAIL_INPUT_BLOCKS = _metric_labeled(
    Counter,
    "smartrfp_guardrail_input_blocks_total",
    "Inputs rejected by guardrails, by rule",
    ["rule"],
)

GUARDRAIL_OUTPUT_REDACTIONS = _metric_labeled(
    Counter,
    "smartrfp_guardrail_output_redactions_total",
    "Output redactions applied, by reason",
    ["reason"],
)

GUARDRAIL_PII_REDACTIONS = _metric_labeled(
    Counter,
    "smartrfp_guardrail_pii_redactions_total",
    "PII redactions applied, by category",
    ["category"],
)

GUARDRAIL_HALLUCINATION_FLAGS = _metric(
    Counter,
    "smartrfp_guardrail_hallucination_terms_total",
    "Risky/unverifiable claim terms detected in generated output",
)

# -------------------------------------------------------
# LLM Failover Metrics
# -------------------------------------------------------

LLM_FAILOVER_TOTAL = _metric_labeled(
    Counter,
    "smartrfp_llm_failover_total",
    "LLM provider failover events, by from_provider/to_provider",
    ["from_provider", "to_provider"],
)

LLM_PROVIDER_REQUESTS = _metric_labeled(
    Counter,
    "smartrfp_llm_provider_requests_total",
    "LLM requests by provider and outcome",
    ["provider", "outcome"],
)

# -------------------------------------------------------
# API / Auth / Rate-limit Metrics
# -------------------------------------------------------

AUTH_FAILURES = _metric(
    Counter,
    "smartrfp_auth_failures_total",
    "Rejected requests due to missing/invalid API key"
)

RATE_LIMIT_REJECTIONS = _metric(
    Counter,
    "smartrfp_rate_limit_rejections_total",
    "Requests rejected due to rate limiting"
)

# -------------------------------------------------------
# Evaluation Metrics (deterministic, per latest run)
# -------------------------------------------------------

EVAL_SCORE = _metric_labeled(
    Gauge,
    "smartrfp_eval_score",
    "Latest deterministic evaluation score, by metric name",
    ["metric"],
)

EVAL_BELOW_THRESHOLD = _metric(
    Counter,
    "smartrfp_eval_below_threshold_total",
    "Proposals flagged below a configured quality threshold"
)

# -------------------------------------------------------
# RAGAS Metrics
# -------------------------------------------------------

RAGAS_SCORE = _metric_labeled(
    Gauge,
    "smartrfp_ragas_score",
    "Latest RAGAS (LLM-judged) score, by metric name",
    ["metric"],
)

RAGAS_RUNS = _metric_labeled(
    Counter,
    "smartrfp_ragas_runs_total",
    "RAGAS evaluation job outcomes",
    ["outcome"],  # completed | failed | skipped
)

RAGAS_RETRIES = _metric(
    Counter,
    "smartrfp_ragas_retries_total",
    "RAGAS evaluation retry attempts after a transient failure"
)

RAGAS_DURATION = _metric(
    Histogram,
    "smartrfp_ragas_duration_seconds",
    "Wall-clock time for a RAGAS evaluation job, including retries"
)

# -------------------------------------------------------
# Per-stage pipeline latency (real, measured, not estimated)
# -------------------------------------------------------

STAGE_LATENCY = _metric_labeled(
    Histogram,
    "smartrfp_stage_latency_seconds",
    "Wall-clock time per pipeline stage, by stage name",
    ["stage"],
)