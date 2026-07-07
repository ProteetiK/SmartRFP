import streamlit as st
import pandas as pd
import altair as alt

from ui import api
from ui.ui_utils import topbar, card, current_rfp, metric

from langsmith_utils import (
    get_trace_id_for_rfp,
    get_trace_latencies,
)

# =========================================================================== #
#  PAGE: AI Evaluation
# =========================================================================== #
def page_llm_eval():
    topbar(
        "AI Evaluation",
        "Check performance of LLM calls.",
        show_rfp=True,
    )
    
    rfp = current_rfp()
    if not rfp:
        st.info("No RFP selected.")
        return
    evaluation = api.get_evaluation_metrics(rfp["id"])
    if not evaluation:
        st.info("No evaluation metrics available yet for this RFP -- it may still be "
                "processing, or the pipeline run failed before evaluation.")
        return
    if evaluation:
        overall_score = (
            evaluation["proposal_completeness"]
            + evaluation["average_confidence"]
            + evaluation["context_coverage"]
            + evaluation["pricing_freshness"]
        ) / 4

        left, _, _ = st.columns([1, 2, 1])

        with left:
            st.metric(
                "Overall AI Quality Score",
                f"{overall_score * 100:.1f}%",
            )

        # ----------------------------------------------------------------------- #
        # Core Metrics
        # ----------------------------------------------------------------------- #
        cols = st.columns(4)

        metric(
            cols[0],
            "ic-green",
            "✅",
            "Completeness",
            f"{evaluation['proposal_completeness'] * 100:.0f}%",
            "Proposal",
        )

        metric(
            cols[1],
            "ic-blue",
            "📚",
            "Context",
            f"{evaluation['context_coverage'] * 100:.0f}%",
            "Grounded",
        )

        metric(
            cols[2],
            "ic-purple",
            "🎯",
            "Confidence",
            f"{evaluation['average_confidence']:.2f}",
            "LLM",
        )

        metric(
            cols[3],
            "ic-red",
            "⚠️",
            "Flags",
            str(evaluation["hallucination_flags"]),
            "Review",
        )
        st.divider()

        # ----------------------------------------------------------------------- #
        # Advanced RAG Metrics
        # ----------------------------------------------------------------------- #
        st.subheader("🧠 Advanced RAG Evaluation")

        cols = st.columns(4)

        metric(
            cols[0],
            "ic-blue",
            "📖",
            "Faithfulness",
            f"{evaluation['faithfulness'] * 100:.1f}%",
            "Grounded",
        )

        metric(
            cols[1],
            "ic-green",
            "🎯",
            "Answer Relevancy",
            f"{evaluation['answer_relevancy'] * 100:.1f}%",
            "Relevant",
        )

        metric(
            cols[2],
            "ic-purple",
            "📚",
            "Context Precision",
            f"{evaluation['context_precision'] * 100:.1f}%",
            "Retrieved",
        )

        metric(
            cols[3],
            "ic-amber",
            "🔍",
            "Context Recall",
            f"{evaluation['context_recall'] * 100:.1f}%",
            "Coverage",
        )

        cols = st.columns(3)

        metric(
            cols[0],
            "ic-blue",
            "🏆",
            "MRR@K",
            f"{evaluation['mrr']:.2f}",
            "Ranking",
        )

        metric(
            cols[1],
            "ic-green",
            "🎯",
            "Hit Rate@K",
            f"{evaluation['hit_rate'] * 100:.0f}%",
            "Success",
        )

        metric(
            cols[2],
            "ic-red",
            "🧩",
            "Chunk Overlap",
            f"{evaluation['chunk_overlap'] * 100:.1f}%",
            "Lower is Better",
        )

    st.divider()
    # ----------------------------------------------------------------------- #
    # Runtime Statistics
    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    trace_id = get_trace_id_for_rfp(rfp.get("id"))
    latencies = {}

    if trace_id != 0:
        try:
            latencies = get_trace_latencies(trace_id)
        except Exception as e:
            st.warning(f"Unable to retrieve LangSmith trace: {e}")

    # Build runtime table
    runtime_rows = []

    # # Show locally measured runtime first
    runtime_rows.append({
        "Metric": "Pipeline Runtime",
        "Value": f"{evaluation['runtime_seconds']} sec",
    })

    # Add every LangSmith span that exists
    preferred_order = [
        "SmartRFP Pipeline",
        "RAG Agent Initialization",
        "RAG Retrieval",
        "Pricing Engine",
        "Pricing Web Search",
        "Fetch Pricing",
        "Groq Chat",
        "Draft Generator",
    ]

    for name in preferred_order:
        if name in latencies:
            runtime_rows.append(
                {
                    "Metric": f"{name} Latency",
                    "Value": f"{latencies[name]} sec",
                }
            )

        # Add any additional traces automatically
    for name, value in sorted(latencies.items()):
        if name not in preferred_order:
            runtime_rows.append(
                {
                    "Metric": f"{name} Latency",
                    "Value": f"{value} sec",
                }
            )

    runtime_rows.extend(
        [
            {
                "Metric": "LLM Calls",
                "Value": evaluation["llm_calls"],
            },
            {
                "Metric": "Knowledge Base Documents",
                "Value": evaluation["knowledge_documents"],
            },
            {
                "Metric": "Pricing Items",
                "Value": evaluation["pricing_items"],
            },
        ]
    )

    stats = pd.DataFrame(runtime_rows)
   
    st.subheader("⚡ Runtime Performance")

    # ---------------- Latency Chart ----------------
    latency_stats = stats[
        stats["Metric"].str.contains("Latency")
    ].copy()

    if not latency_stats.empty:
        latency_stats["Seconds"] = (
            latency_stats["Value"]
            .str.replace(" sec", "", regex=False)
            .astype(float)
        )

        chart = (
            alt.Chart(latency_stats)
            .mark_bar(
                color="#FFE600",  # EY Yellow
                cornerRadiusTopLeft=4,
                cornerRadiusTopRight=4,
            )
            .encode(
                x=alt.X(
                    "Metric:N",
                    sort=None,
                    axis=alt.Axis(
                        title="",
                        labelColor="white",
                        labelAngle=-20,
                        labelFontSize=12,
                        tickColor="#666666",
                        domainColor="#666666",
                    ),
                ),
                y=alt.Y(
                    "Seconds:Q",
                    axis=alt.Axis(
                        title="Seconds",
                        titleColor="white",
                        labelColor="white",
                        gridColor="#333333",
                        tickColor="#666666",
                        domainColor="#666666",
                    ),
                ),
                tooltip=[
                    alt.Tooltip("Metric:N"),
                    alt.Tooltip("Seconds:Q", format=".2f"),
                ],
            )
            .properties(
                height=350,
                background="#0A0A0A",   # Entire chart background
            )
            .configure_view(
                fill="#0A0A0A",         # Plotting area background
                stroke=None,
            )
            .configure_axis(
                labelColor="white",
                titleColor="white",
                gridColor="#333333",
                domainColor="#666666",
                tickColor="#666666",
            )
            .configure_title(
                color="white",
                fontSize=18,
                font="Calibri",
            )
            .configure_legend(
                labelColor="white",
                titleColor="white",
                fillColor="#0A0A0A",
                strokeColor="#0A0A0A",
            )
        )

    st.altair_chart(chart, use_container_width=True)
    
    # ---------------- Summary Metrics ----------------
    st.subheader("📊 Pipeline Statistics")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "LLM Calls",
        stats.loc[
            stats["Metric"] == "LLM Calls",
            "Value",
        ].iloc[0],
    )

    c2.metric(
        "Knowledge Docs",
        stats.loc[
            stats["Metric"] == "Knowledge Base Documents",
            "Value",
        ].iloc[0],
    )

    c3.metric(
        "Pricing Items",
        stats.loc[
            stats["Metric"] == "Pricing Items",
            "Value",
        ].iloc[0],
    )

    with st.expander("View Raw Runtime Data"):
        st.dataframe(
            stats,
            hide_index=True,
            use_container_width=True,
        )