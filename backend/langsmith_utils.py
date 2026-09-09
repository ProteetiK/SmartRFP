import os
from typing import Optional, Dict
from langsmith import Client
from langsmith.run_helpers import get_current_run_tree

client = Client()


# ----------------------------------------------------------
# Helpers
# ----------------------------------------------------------

def _duration(run) -> Optional[float]:
    if not run.start_time or not run.end_time:
        return None

    return round(
        (run.end_time - run.start_time).total_seconds(),
        3,
    )


# ----------------------------------------------------------
# Current in-flight run helpers
# ----------------------------------------------------------

def get_current_pipeline_run():
    return get_current_run_tree()


def get_current_trace_id() -> Optional[str]:
    run = get_current_run_tree()

    if run is None:
        return None

    return str(run.trace_id)


def get_current_pipeline_latency() -> Optional[float]:
    run = get_current_run_tree()

    if run is None:
        return None

    return _duration(run)


# ----------------------------------------------------------
# Finished trace helpers
# ----------------------------------------------------------

def get_trace_latencies(trace_id: str) -> Dict[str, float]:
    latencies = {}

    try:
        runs = list(
            client.list_runs(
                trace_id=trace_id,
                limit=100,
            )
        )

        for run in runs:

            d = _duration(run)

            if d is not None:
                latencies[run.name] = d

    except Exception as e:
        print(f"LangSmith lookup failed: {e}")

    return latencies


def get_latency(
    trace_id: str,
    run_name: str,
) -> Optional[float]:

    return get_trace_latencies(trace_id).get(run_name)


def get_pipeline_latency(trace_id: str):
    return get_latency(
        trace_id,
        "SmartRFP Pipeline",
    )


def get_pricing_latency(trace_id: str):
    return get_latency(
        trace_id,
        "Pricing Agent",
    )


def get_requirement_extraction_latency(trace_id: str):
    return get_latency(
        trace_id,
        "Requirement Extraction",
    )


def get_draft_generation_latency(trace_id: str):
    return get_latency(
        trace_id,
        "Draft Generation",
    )

def get_trace_id_for_rfp(rfp_id: int) -> Optional[str]:
    project = os.getenv("LANGSMITH_PROJECT")

    runs = list(
        client.list_runs(
            project_name=project,
            is_root=True,
            limit=50,
        )
    )

    if not runs:
        return None

    for run in runs:
        if not run.inputs:
            continue

        run_rfp_id = run.inputs.get("rfp_id")

        if run_rfp_id is None:
            continue

        if str(run_rfp_id) == str(rfp_id):
            return str(run.trace_id)

    return None