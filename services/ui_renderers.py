from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st


def render_platform_status_row(
    prepared_file_count: int,
    rag_ready: bool,
    complibot_ready: bool,
    last_route_label: Optional[str] = None,
) -> None:
    cols = st.columns(4)

    cols[0].metric("Prepared Files", prepared_file_count)
    cols[1].metric("PharmaRAG", "Ready" if rag_ready else "Not Ready")
    cols[2].metric("CompliBot", "Ready" if complibot_ready else "Not Ready")
    cols[3].metric("Last Engine", last_route_label or "—")


def render_route_info(route_label: str, route_description: str) -> None:
    st.success(f"Selected Engine: {route_label}")
    st.caption(route_description)


def render_latest_status_block(last_status: str) -> None:
    if last_status:
        st.subheader("Latest Status")
        st.text_area("Status", value=last_status, height=180)


def render_llm_status_panel(llm_status: Dict) -> None:
    st.subheader("LLM Status")

    if llm_status.get("configured"):
        st.success(
            f"LLM is configured: provider={llm_status.get('provider')} | model={llm_status.get('model')}"
        )
    elif llm_status.get("enabled_flag") and not llm_status.get("configured"):
        st.warning(
            "LLM is enabled in configuration, but setup is incomplete. Retrieval-only fallback will be used."
        )
    else:
        st.caption("LLM is currently disabled. Retrieval-based answers will be used.")

    with st.expander("LLM Configuration Summary"):
        st.write(f"- Provider: {llm_status.get('provider')}")
        st.write(f"- Model: {llm_status.get('model')}")
        st.write(f"- API Key Present: {llm_status.get('api_key_present')}")
        st.write(f"- Base URL: {llm_status.get('base_url')}")
        st.write(f"- Timeout Seconds: {llm_status.get('timeout_seconds')}")
        st.write(f"- Temperature: {llm_status.get('temperature')}")
        st.write(f"- Max Output Tokens: {llm_status.get('max_output_tokens')}")


def render_platform_health_panel(health: Dict, readiness: Dict[str, bool]) -> None:
    st.subheader("Platform Health")

    if health.get("core_ready"):
        st.success("Core platform storage is ready.")
    else:
        st.warning("Some core platform storage areas are not ready yet.")

    with st.expander("Health Checks"):
        for key, value in health.get("checks", {}).items():
            st.write(f"- {key}: {value}")

    st.subheader("Deployment Readiness")
    with st.expander("Readiness Checklist"):
        for key, value in readiness.items():
            st.write(f"- {key}: {value}")


def render_document_history_header(prepared_docs: List[Dict]) -> None:
    st.subheader("Document History")

    if not prepared_docs:
        st.caption("No prepared files available.")
        return

    st.caption(f"{len(prepared_docs)} prepared document(s) available.")


def render_document_history_table(prepared_docs: List[Dict]) -> None:
    if not prepared_docs:
        return

    for item in prepared_docs:
        with st.container():
            st.markdown(f"**{item['name']}**")
            meta_cols = st.columns(4)
            meta_cols[0].caption(f"Size: {item.get('size_kb', 0):.2f} KB")
            meta_cols[1].caption(f"Updated: {item.get('modified_at', 'Unknown')}")
            meta_cols[2].caption(f"Type: {item.get('category', 'General')}")
            meta_cols[3].caption(f"Version: {item.get('document_version', 'Unknown')}")
            st.markdown("---")


def render_engine_prep_result(prep_result: Dict) -> None:
    if prep_result.get("ok"):
        st.success(prep_result.get("status", "Preparation completed successfully."))
    else:
        st.warning(prep_result.get("status", "Preparation completed with warnings."))

    details = prep_result.get("details", "")
    if details:
        with st.expander("Preparation Details"):
            st.text(details)

    metrics = prep_result.get("metrics", {})
    if metrics:
        with st.expander("Preparation Metrics"):
            for key, value in metrics.items():
                st.write(f"- {key}: {value}")


def render_prepare_all_result(prep_result: Dict) -> None:
    if prep_result.get("ok"):
        st.success(prep_result.get("status", "All engines prepared successfully."))
    else:
        st.warning(prep_result.get("status", "One or more engines completed with warnings."))

    status_lines = prep_result.get("status_lines", [])
    if status_lines:
        st.subheader("Engine Preparation Summary")
        for line in status_lines:
            st.write(f"- {line}")

    details = prep_result.get("details", "")
    if details:
        with st.expander("Preparation Details"):
            st.text(details)

    metrics = prep_result.get("metrics", {})
    if metrics:
        with st.expander("Preparation Metrics"):
            for key, value in metrics.items():
                st.write(f"- {key}: {value}")


def render_summarizer_result(result: Dict) -> None:
    if "error" in result:
        st.error(result["error"])
        return

    top_left, top_right = st.columns([2, 1])

    with top_left:
        st.subheader("Document Title")
        st.info(result.get("title", "Untitled Document"))

        st.subheader("Structured Summary")
        st.write(result.get("summary", "No summary available."))

        note = result.get("summary_note", "")
        if note:
            st.caption(note)

    with top_right:
        st.subheader("Source")
        st.success(result.get("source", "Unknown"))

        st.subheader("Document Type")
        st.write(result.get("document_type", "Unknown"))

        st.subheader("Summary Mode")
        st.code(result.get("summary_mode", "rule_based"))

        if result.get("trace_id"):
            st.subheader("Trace ID")
            st.code(result.get("trace_id"))

        if result.get("document_version"):
            st.subheader("Document Version")
            st.code(result.get("document_version"))

    sections = result.get("sections", {})
    if sections:
        st.subheader("Detected Sections")
        for section_name, section_text in sections.items():
            with st.expander(section_name):
                st.write(section_text)

    st.subheader("Key Highlights")
    highlights = result.get("highlights", [])
    if highlights:
        for point in highlights:
            st.write(f"- {point}")
    else:
        st.write("No highlights identified.")

    with st.expander("Extracted Text Preview"):
        st.text(result.get("preview_text", "No preview available."))


def render_rag_result(result: Dict) -> None:
    left, right = st.columns([2, 1])

    with left:
        st.subheader("Answer Summary")
        st.write(result.get("summary", "No summary available."))

        note = result.get("answer_note", "")
        if note:
            st.caption(note)

    with right:
        st.subheader("Primary Citation")
        st.code(result.get("primary_citation", "") or "No citation")

        st.subheader("Answer Mode")
        st.code(result.get("answer_mode", "retrieval"))

        if result.get("trace_id"):
            st.subheader("Trace ID")
            st.code(result.get("trace_id"))

        if result.get("document_version"):
            st.subheader("Document Version")
            st.code(result.get("document_version"))

    supporting_sources = result.get("supporting_sources", [])
    st.subheader("Top Supporting Sources")
    if supporting_sources:
        for item in supporting_sources:
            st.write(f"- {item}")
    else:
        st.write("No supporting sources available.")

    excerpts = result.get("relevant_excerpts", [])
    st.subheader("Relevant Excerpts")
    if excerpts:
        for idx, item in enumerate(excerpts, start=1):
            label = f"Excerpt {idx} — {item.get('source', 'Unknown')} (chunk {item.get('chunk_index', 'N/A')})"
            with st.expander(label):
                st.write(item.get("text", "No excerpt available."))
    else:
        st.write("No excerpts available.")


def render_complibot_result(result: Dict) -> None:
    left, right = st.columns([2, 1])

    with left:
        st.subheader("Answer Summary")
        st.write(result.get("answer_summary", "No answer available."))

        st.subheader("Procedure / Guidance")
        st.write(result.get("procedure_guidance", "No procedure guidance available."))

    with right:
        st.subheader("Primary Source")
        st.info(result.get("source", "No grounded source found"))

        st.subheader("Answer Mode")
        st.code(result.get("answer_mode", "retrieval"))

        if result.get("trace_id"):
            st.subheader("Trace ID")
            st.code(result.get("trace_id"))

        if result.get("document_version"):
            st.subheader("Document Version")
            st.code(result.get("document_version"))

    st.subheader("Key Requirements")
    key_requirements = result.get("key_requirements", [])
    if key_requirements:
        for item in key_requirements:
            st.write(f"- {item}")
    else:
        st.write("No explicit key requirements identified.")

    st.subheader("Supporting Evidence")
    evidence = result.get("evidence", [])
    if evidence:
        for idx, item in enumerate(evidence, start=1):
            distance = item.get("distance", None)
            if distance is not None:
                label = (
                    f"Evidence {idx} — {item.get('source', 'Unknown')} "
                    f"(chunk {item.get('chunk_index', 'N/A')}) | distance={distance:.4f}"
                )
            else:
                label = (
                    f"Evidence {idx} — {item.get('source', 'Unknown')} "
                    f"(chunk {item.get('chunk_index', 'N/A')})"
                )

            with st.expander(label):
                st.write(item.get("text", "No evidence text available."))
    else:
        st.write("No evidence available.")

    st.subheader("Compliance Interpretation Note")
    st.warning(result.get("compliance_note", "No compliance interpretation note available."))


def render_audit_log_panel(audit_events: List[Dict]) -> None:
    st.subheader("Audit Log")

    if not audit_events:
        st.caption("No audit events recorded yet.")
        return

    st.caption(f"Showing {len(audit_events)} recent audit event(s).")

    for idx, event in enumerate(audit_events, start=1):
        ts = event.get("timestamp_utc", "Unknown time")
        event_type = event.get("event_type", "unknown_event")
        status = event.get("status", "unknown_status")
        actor = event.get("actor", "unknown_actor")
        module = event.get("module", "platform")
        route = event.get("route")
        target_file = event.get("target_file")
        review_status = event.get("review_status")
        trace_id = event.get("trace_id")
        document_version = event.get("document_version")
        details = event.get("details", {})

        label = f"{idx}. {event_type} | {status} | {ts}"
        with st.expander(label):
            st.write(f"**Event Type:** {event_type}")
            st.write(f"**Status:** {status}")
            st.write(f"**Actor:** {actor}")
            st.write(f"**Module:** {module}")
            if route:
                st.write(f"**Route:** {route}")
            if target_file:
                st.write(f"**Target File:** {target_file}")
            if review_status:
                st.write(f"**Review Status:** {review_status}")
            if trace_id:
                st.write(f"**Trace ID:** {trace_id}")
            if document_version:
                st.write(f"**Document Version:** {document_version}")
            st.write(f"**Timestamp (UTC):** {ts}")
            st.write("**Details:**")
            st.json(details)


def render_review_metrics(metrics: Dict[str, int]) -> None:
    st.subheader("Review Metrics")
    cols = st.columns(4)
    cols[0].metric("Total", metrics.get("total", 0))
    cols[1].metric("Pending", metrics.get("pending_review", 0))
    cols[2].metric("Approved", metrics.get("approved", 0))
    cols[3].metric("Rejected", metrics.get("rejected", 0))


def render_review_queue_panel(review_items: List[Dict]) -> None:
    st.subheader("Review Queue")

    if not review_items:
        st.caption("No review items found for the current filters.")
        return

    st.caption(f"Showing {len(review_items)} filtered review item(s).")

    for idx, item in enumerate(review_items, start=1):
        title = item.get("title", "Untitled Review Item")
        status = item.get("status", "pending_review")
        item_type = item.get("item_type", "unknown")
        source = item.get("source", "Unknown")
        created_at = item.get("created_at_utc", "Unknown time")
        updated_at = item.get("updated_at_utc", "Unknown time")
        reviewed_by = item.get("reviewed_by", "")
        reviewed_at = item.get("reviewed_at_utc", "")
        decision_note = item.get("decision_note", "")
        trace_id = item.get("trace_id", "")
        document_version = item.get("document_version", "")
        content_summary = item.get("content_summary", "")
        metadata = item.get("metadata", {})
        review_id = item.get("review_id", "unknown")

        label = f"{idx}. {title} | {status}"
        with st.expander(label):
            st.write(f"**Review ID:** {review_id}")
            st.write(f"**Item Type:** {item_type}")
            st.write(f"**Status:** {status}")
            st.write(f"**Source:** {source}")
            if trace_id:
                st.write(f"**Trace ID:** {trace_id}")
            if document_version:
                st.write(f"**Document Version:** {document_version}")
            st.write(f"**Created At (UTC):** {created_at}")
            st.write(f"**Updated At (UTC):** {updated_at}")
            if reviewed_by:
                st.write(f"**Reviewed By:** {reviewed_by}")
            if reviewed_at:
                st.write(f"**Reviewed At (UTC):** {reviewed_at}")
            if decision_note:
                st.write(f"**Decision Note:** {decision_note}")
            st.write("**Content Summary:**")
            st.write(content_summary)
            st.write("**Metadata:**")
            st.json(metadata)