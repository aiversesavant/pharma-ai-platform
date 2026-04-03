from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, TypedDict, cast

import streamlit as st


TOC_NOISE_PATTERNS = [
    r"\.{3,}",
    r"^\s*executive summary\s*$",
    r"^\s*introduction\s*$",
    r"^\s*scope and goals.*$",
    r"^\s*purpose\s*$",
    r"^\s*responsibilities\s*$",
    r"^\s*process\s*$",
    r"^\s*compliance notes\s*$",
    r"^\s*key highlights\s*$",
    r"^\s*table of contents\s*$",
    r"^\s*contents\s*$",
]


class LLMStatus(TypedDict, total=False):
    configured: bool
    enabled_flag: bool
    provider: str
    model: str
    api_key_present: bool
    base_url: str
    timeout_seconds: int
    temperature: float
    max_output_tokens: int


class HealthStatus(TypedDict, total=False):
    core_ready: bool
    checks: Dict[str, Any]


class PreparedDocument(TypedDict, total=False):
    name: str
    size_kb: float
    modified_at: str
    category: str
    document_version: str


class PreparationMetrics(TypedDict, total=False):
    selected_file_count: int
    processed_docs: int
    total_chunks: int
    processed_pdfs: int
    total_chunks_added: int
    rag_ready: bool
    complibot_ready: bool
    complibot_total_chunks: int
    rag_processed_pdfs: int
    rag_total_chunks_added: int


class PreparationResult(TypedDict, total=False):
    ok: bool
    engine: str
    ready: bool
    status: str
    details: str
    metrics: PreparationMetrics
    processed_docs: List[str]
    status_lines: List[str]
    results: Dict[str, Any]


class SummaryResult(TypedDict, total=False):
    error: str
    title: str
    source: str
    document_type: str
    summary: str
    preview_text: str
    summary_note: str
    summary_mode: str
    trace_id: str
    document_version: str
    sections: Dict[str, str]
    highlights: List[str]


class RAGExcerpt(TypedDict, total=False):
    source: str
    chunk_index: int
    text: str


class RAGResult(TypedDict, total=False):
    summary: str
    answer_note: str
    primary_citation: str
    answer_mode: str
    trace_id: str
    document_version: str
    supporting_sources: List[str]
    relevant_excerpts: List[RAGExcerpt]


class ComplianceEvidence(TypedDict, total=False):
    source: str
    chunk_index: int
    distance: float
    text: str


class CompliBotResult(TypedDict, total=False):
    answer_summary: str
    procedure_guidance: str
    source: str
    answer_mode: str
    trace_id: str
    document_version: str
    key_requirements: List[str]
    evidence: List[ComplianceEvidence]
    compliance_note: str


class AuditEvent(TypedDict, total=False):
    timestamp_utc: str
    event_type: str
    status: str
    actor: str
    module: str
    route: str
    target_file: str
    review_status: str
    trace_id: str
    document_version: str
    details: Dict[str, Any]


class ReviewMetrics(TypedDict, total=False):
    total: int
    pending_review: int
    approved: int
    rejected: int


class ReviewQueueItem(TypedDict, total=False):
    review_id: str
    title: str
    status: str
    item_type: str
    source: str
    created_at_utc: str
    updated_at_utc: str
    reviewed_by: str
    reviewed_at_utc: str
    decision_note: str
    trace_id: str
    document_version: str
    content_summary: str
    metadata: Dict[str, Any]


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove some obvious formatting noise."""
    if not text:
        return ""

    text = str(text).replace("\r", "\n")
    text = re.sub(r"\t+", " ", text)
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\.{3,}", " ", text)
    return text.strip()


def _looks_like_toc_line(line: str) -> bool:
    """Detect likely TOC/decorative lines without stripping too many real headings."""
    stripped = (line or "").strip()
    if not stripped:
        return False

    lowered = stripped.lower()

    if re.search(r"\.{3,}\s*\d*\s*$", stripped):
        return True

    if lowered in {"table of contents", "contents"}:
        return True

    for pattern in TOC_NOISE_PATTERNS:
        if re.match(pattern, stripped, flags=re.IGNORECASE):
            if lowered in {"executive summary", "key highlights", "table of contents", "contents"}:
                return True
            if re.search(r"\.{3,}|\bpage\b|\d+\s*$", stripped, flags=re.IGNORECASE):
                return True

    return False


def _remove_noise_lines(text: str) -> str:
    """Remove likely TOC/noise lines from extracted text."""
    if not text:
        return ""

    cleaned_lines: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _looks_like_toc_line(stripped):
            continue
        cleaned_lines.append(stripped)

    return "\n".join(cleaned_lines).strip()


def _split_sentences(text: str) -> List[str]:
    """Split text into rough sentences while protecting common abbreviations."""
    if not text:
        return []

    text = _clean_text(text)

    protected = text
    abbreviation_map = {
        "e.g.": "EG_ABBR",
        "i.e.": "IE_ABBR",
        "u.s.": "US_ABBR",
        "u.k.": "UK_ABBR",
        "mr.": "MR_ABBR",
        "mrs.": "MRS_ABBR",
        "dr.": "DR_ABBR",
    }

    for original, placeholder in abbreviation_map.items():
        protected = re.sub(re.escape(original), placeholder, protected, flags=re.IGNORECASE)

    parts = re.split(r"(?<=[.!?])\s+", protected)
    restored: List[str] = []

    for part in parts:
        item = part.strip()
        if not item:
            continue

        for original, placeholder in abbreviation_map.items():
            item = re.sub(placeholder, original, item, flags=re.IGNORECASE)

        restored.append(item.strip())

    return restored


def _safe_int(value: Any, default: int = 0) -> int:
    """Safely coerce a value to int."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any) -> Optional[float]:
    """Safely coerce a value to float."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sanitize_for_ui(data: Any, max_depth: int = 4, max_items: int = 50) -> Any:
    """
    Sanitize arbitrary nested data for safe UI display.
    Prevents very deep or huge objects from rendering badly.
    """
    if max_depth <= 0:
        return "[truncated]"

    if data is None or isinstance(data, (str, int, float, bool)):
        return data

    if isinstance(data, list):
        trimmed = data[:max_items]
        return [_sanitize_for_ui(item, max_depth=max_depth - 1, max_items=max_items) for item in trimmed]

    if isinstance(data, dict):
        sanitized: Dict[str, Any] = {}
        for idx, (key, value) in enumerate(data.items()):
            if idx >= max_items:
                sanitized["..."] = "[additional items truncated]"
                break
            sanitized[str(key)] = _sanitize_for_ui(value, max_depth=max_depth - 1, max_items=max_items)
        return sanitized

    return str(data)


def build_executive_summary(raw_summary: str, preview_text: str = "") -> str:
    """Build a cleaner, user-facing executive summary from extracted text."""
    raw_summary = _remove_noise_lines(raw_summary or "")
    preview_text = _remove_noise_lines(preview_text or "")

    summary_sentences = _split_sentences(raw_summary)
    preview_sentences = _split_sentences(preview_text)

    candidate_sentences: List[str] = []
    candidate_sentences.extend(summary_sentences)
    candidate_sentences.extend(preview_sentences)

    cleaned_sentences: List[str] = []
    seen = set()

    for sentence in candidate_sentences:
        normalized = sentence.strip()
        dedupe_key = normalized.lower()

        if len(normalized) < 35:
            continue
        if len(normalized) > 350:
            continue
        if "........" in normalized:
            continue
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        cleaned_sentences.append(normalized)

    if not cleaned_sentences:
        return (
            "This document was processed successfully, but a clean executive summary "
            "could not be generated from the extracted content."
        )

    return " ".join(cleaned_sentences[:4])


def build_key_highlights(raw_highlights: List[str]) -> List[str]:
    """Clean and deduplicate key highlight bullets."""
    if not raw_highlights:
        return []

    cleaned: List[str] = []
    seen = set()

    for item in raw_highlights:
        if not item:
            continue

        value = _clean_text(str(item))
        value = re.sub(r"^[•\-\*\d\.\)\s]+", "", value).strip()
        value = re.sub(r"\.{3,}", " ", value).strip()

        if len(value) < 8:
            continue
        if value.lower() in seen:
            continue

        seen.add(value.lower())
        cleaned.append(value)

    return cleaned[:5]


def render_platform_status_row(
    prepared_file_count: int,
    rag_ready: bool,
    complibot_ready: bool,
    last_route_label: Optional[str] = None,
) -> None:
    """Render platform-level status metrics."""
    cols = st.columns(4)
    cols[0].metric("Prepared Files", _safe_int(prepared_file_count, 0))
    cols[1].metric("PharmaRAG", "Ready" if rag_ready else "Not Ready")
    cols[2].metric("CompliBot", "Ready" if complibot_ready else "Not Ready")
    cols[3].metric("Last Engine", last_route_label or "—")


def render_route_info(route_label: str, route_description: str) -> None:
    """Render selected engine info."""
    st.success(f"Selected Engine: {route_label or 'Unknown'}")
    st.caption(route_description or "")


def render_latest_status_block(last_status: str) -> None:
    """Render the latest status text block."""
    if last_status:
        with st.expander("Latest Status", expanded=False):
            st.text(str(last_status))


def render_llm_status_panel(llm_status: LLMStatus) -> None:
    """Render LLM configuration and readiness state."""
    llm_status = cast(LLMStatus, llm_status or {})

    configured = bool(llm_status.get("configured"))
    enabled_flag = bool(llm_status.get("enabled_flag"))
    provider = llm_status.get("provider")
    model = llm_status.get("model")
    api_key_present = bool(llm_status.get("api_key_present"))

    with st.expander("LLM Status", expanded=False):
        if configured and provider and model:
            st.success(f"LLM configured: provider={provider} | model={model}")
        elif enabled_flag and not configured:
            st.warning(
                "LLM is enabled in configuration, but setup is incomplete. "
                "Retrieval-only fallback will be used."
            )
        else:
            st.caption("LLM is currently disabled. Retrieval-based answers will be used.")

        st.write(f"**Provider:** {provider}")
        st.write(f"**Model:** {model}")
        st.write(f"**API Key Present:** {api_key_present}")
        st.write(f"**Base URL:** {llm_status.get('base_url')}")
        st.write(f"**Timeout Seconds:** {llm_status.get('timeout_seconds')}")
        st.write(f"**Temperature:** {llm_status.get('temperature')}")
        st.write(f"**Max Output Tokens:** {llm_status.get('max_output_tokens')}")


def render_platform_health_panel(health: HealthStatus, readiness: Dict[str, bool]) -> None:
    """Render platform health checks and deployment readiness."""
    health = cast(HealthStatus, health or {})
    readiness = readiness or {}

    with st.expander("Platform Health & Deployment Readiness", expanded=False):
        if health.get("core_ready"):
            st.success("Core platform storage is ready.")
        else:
            st.warning("Some core platform storage areas are not ready yet.")

        st.markdown("**Health Checks**")
        checks = health.get("checks", {}) or {}
        if checks:
            for key, value in checks.items():
                st.write(f"- {key}: {value}")
        else:
            st.write("No health check data available.")

        st.markdown("**Deployment Readiness**")
        if readiness:
            for key, value in readiness.items():
                st.write(f"- {key}: {value}")
        else:
            st.write("No deployment readiness data available.")


def render_document_history_header(prepared_docs: List[PreparedDocument]) -> None:
    """Render document history header and count."""
    st.subheader("Document History")
    if not prepared_docs:
        st.caption("No prepared files available.")
        return
    st.caption(f"{len(prepared_docs)} prepared document(s) available.")


def render_document_history_table(prepared_docs: List[PreparedDocument]) -> None:
    """Render document history cards."""
    if not prepared_docs:
        return

    for item in prepared_docs:
        item = cast(PreparedDocument, item or {})
        with st.container(border=True):
            st.markdown(f"**{item.get('name', 'Unnamed Document')}**")
            meta_cols = st.columns(4)
            meta_cols[0].caption(f"Size: {_safe_float(item.get('size_kb')) or 0:.2f} KB")
            meta_cols[1].caption(f"Updated: {item.get('modified_at', 'Unknown')}")
            meta_cols[2].caption(f"Type: {item.get('category', 'General')}")
            meta_cols[3].caption(f"Version: {item.get('document_version', 'Unknown')}")


def render_engine_prep_result(prep_result: PreparationResult) -> None:
    """Render single-engine preparation result."""
    prep_result = cast(PreparationResult, prep_result or {})

    if prep_result.get("ok"):
        st.success(prep_result.get("status", "Preparation completed successfully."))
    else:
        st.warning(prep_result.get("status", "Preparation completed with warnings."))

    details = prep_result.get("details", "")
    if details:
        with st.expander("Preparation Details", expanded=False):
            st.text(str(details))

    metrics = prep_result.get("metrics", {}) or {}
    if metrics:
        with st.expander("Preparation Metrics", expanded=False):
            for key, value in metrics.items():
                st.write(f"- {key}: {value}")


def render_prepare_all_result(prep_result: PreparationResult) -> None:
    """Render combined preparation result for all engines."""
    prep_result = cast(PreparationResult, prep_result or {})

    if prep_result.get("ok"):
        st.success(prep_result.get("status", "All engines prepared successfully."))
    else:
        st.warning(prep_result.get("status", "One or more engines completed with warnings."))

    status_lines = prep_result.get("status_lines", []) or []
    if status_lines:
        with st.expander("Engine Preparation Summary", expanded=False):
            for line in status_lines:
                st.write(f"- {line}")

    details = prep_result.get("details", "")
    if details:
        with st.expander("Preparation Details", expanded=False):
            st.text(str(details))

    metrics = prep_result.get("metrics", {}) or {}
    if metrics:
        with st.expander("Preparation Metrics", expanded=False):
            for key, value in metrics.items():
                st.write(f"- {key}: {value}")


def render_summarizer_result(result: SummaryResult, show_debug: bool = False) -> None:
    """Render document summarizer output."""
    result = cast(SummaryResult, result or {})

    if "error" in result:
        st.error(str(result["error"]))
        return

    title = result.get("title", "Untitled Document")
    source = result.get("source", "Unknown")
    document_type = result.get("document_type", "Unknown")
    raw_summary = result.get("summary", "")
    preview_text = result.get("preview_text", "")
    summary_note = result.get("summary_note", "")
    summary_mode = result.get("summary_mode", "rule_based")
    trace_id = result.get("trace_id")
    document_version = result.get("document_version")
    sections = result.get("sections", {}) or {}
    highlights = build_key_highlights(result.get("highlights", []) or [])
    executive_summary = build_executive_summary(raw_summary=raw_summary, preview_text=preview_text)

    st.subheader("Document Summary")

    with st.container(border=True):
        st.markdown(f"### {title}")

        meta_cols = st.columns(2)
        with meta_cols[0]:
            st.caption(f"Source: {source}")
        with meta_cols[1]:
            st.caption(f"Type: {document_type}")

        st.markdown("#### Executive Summary")
        st.write(executive_summary)

        if summary_note:
            st.caption(summary_note)

        st.markdown("#### Key Highlights")
        if highlights:
            for point in highlights:
                st.markdown(f"- {point}")
        else:
            st.write("No highlights identified.")

    if show_debug:
        with st.expander("Summary Debug Details", expanded=False):
            st.write(f"**Summary Mode:** {summary_mode}")
            if trace_id:
                st.write(f"**Trace ID:** {trace_id}")
            if document_version:
                st.write(f"**Document Version:** {document_version}")

            if isinstance(sections, dict) and sections:
                st.markdown("**Detected Sections**")
                for section_name, section_text in sections.items():
                    with st.expander(str(section_name), expanded=False):
                        st.write(section_text)

            st.markdown("**Raw Extracted Preview**")
            st.text(preview_text or "No preview available.")


def render_rag_result(result: RAGResult, show_debug: bool = False) -> None:
    """Render PharmaRAG answer output."""
    result = cast(RAGResult, result or {})

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

        if show_debug:
            st.subheader("Answer Mode")
            st.code(result.get("answer_mode", "retrieval"))
            if result.get("trace_id"):
                st.subheader("Trace ID")
                st.code(result.get("trace_id"))
            if result.get("document_version"):
                st.subheader("Document Version")
                st.code(result.get("document_version"))

    supporting_sources = result.get("supporting_sources", []) or []
    st.subheader("Top Supporting Sources")
    if supporting_sources:
        for item in supporting_sources:
            st.write(f"- {item}")
    else:
        st.write("No supporting sources available.")

    excerpts = result.get("relevant_excerpts", []) or []
    if excerpts:
        st.subheader("Relevant Excerpts")
        for idx, item in enumerate(excerpts, start=1):
            excerpt = cast(RAGExcerpt, item or {})
            label = (
                f"Excerpt {idx} — {excerpt.get('source', 'Unknown')} "
                f"(chunk {excerpt.get('chunk_index', 'N/A')})"
            )
            with st.expander(label, expanded=False):
                st.write(excerpt.get("text", "No excerpt available."))


def render_complibot_result(result: CompliBotResult, show_debug: bool = False) -> None:
    """Render CompliBot grounded compliance answer output."""
    result = cast(CompliBotResult, result or {})

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Answer Summary")
        st.write(result.get("answer_summary", "No answer available."))

        st.subheader("Procedure / Guidance")
        st.write(result.get("procedure_guidance", "No procedure guidance available."))

    with right:
        st.subheader("Primary Source")
        st.info(result.get("source", "No grounded source found"))

        if show_debug:
            st.subheader("Answer Mode")
            st.code(result.get("answer_mode", "retrieval"))
            if result.get("trace_id"):
                st.subheader("Trace ID")
                st.code(result.get("trace_id"))
            if result.get("document_version"):
                st.subheader("Document Version")
                st.code(result.get("document_version"))

    st.subheader("Key Requirements")
    key_requirements = result.get("key_requirements", []) or []
    if key_requirements:
        for item in key_requirements:
            st.write(f"- {item}")
    else:
        st.write("No explicit key requirements identified.")

    evidence = result.get("evidence", []) or []
    if evidence:
        st.subheader("Supporting Evidence")
        for idx, item in enumerate(evidence, start=1):
            evidence_item = cast(ComplianceEvidence, item or {})
            distance_value = _safe_float(evidence_item.get("distance"))

            if distance_value is not None:
                label = (
                    f"Evidence {idx} — {evidence_item.get('source', 'Unknown')} "
                    f"(chunk {evidence_item.get('chunk_index', 'N/A')}) | distance={distance_value:.4f}"
                )
            else:
                label = (
                    f"Evidence {idx} — {evidence_item.get('source', 'Unknown')} "
                    f"(chunk {evidence_item.get('chunk_index', 'N/A')})"
                )

            with st.expander(label, expanded=False):
                st.write(evidence_item.get("text", "No evidence text available."))

    st.subheader("Compliance Interpretation Note")
    st.warning(result.get("compliance_note", "No compliance interpretation note available."))


def render_audit_log_panel(audit_events: List[AuditEvent]) -> None:
    """Render audit log events."""
    st.subheader("Audit Log")

    if not audit_events:
        st.caption("No audit events recorded yet.")
        return

    st.caption(f"Showing {len(audit_events)} recent audit event(s).")

    for idx, event in enumerate(audit_events, start=1):
        event = cast(AuditEvent, event or {})
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
        details = _sanitize_for_ui(event.get("details", {}) or {})

        label = f"{idx}. {event_type} | {status} | {ts}"
        with st.expander(label, expanded=False):
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


def render_review_metrics(metrics: ReviewMetrics) -> None:
    """Render review queue summary metrics."""
    metrics = cast(ReviewMetrics, metrics or {})

    st.subheader("Review Metrics")
    cols = st.columns(4)
    cols[0].metric("Total", _safe_int(metrics.get("total", 0), 0))
    cols[1].metric("Pending", _safe_int(metrics.get("pending_review", 0), 0))
    cols[2].metric("Approved", _safe_int(metrics.get("approved", 0), 0))
    cols[3].metric("Rejected", _safe_int(metrics.get("rejected", 0), 0))


def render_review_queue_panel(review_items: List[ReviewQueueItem]) -> None:
    """Render review queue items."""
    st.subheader("Review Queue")

    if not review_items:
        st.caption("No review items found for the current filters.")
        return

    st.caption(f"Showing {len(review_items)} filtered review item(s).")

    for idx, item in enumerate(review_items, start=1):
        review_item = cast(ReviewQueueItem, item or {})
        title = review_item.get("title", "Untitled Review Item")
        status = review_item.get("status", "pending_review")
        item_type = review_item.get("item_type", "unknown")
        source = review_item.get("source", "Unknown")
        created_at = review_item.get("created_at_utc", "Unknown time")
        updated_at = review_item.get("updated_at_utc", "Unknown time")
        reviewed_by = review_item.get("reviewed_by", "")
        reviewed_at = review_item.get("reviewed_at_utc", "")
        decision_note = review_item.get("decision_note", "")
        trace_id = review_item.get("trace_id", "")
        document_version = review_item.get("document_version", "")
        content_summary = review_item.get("content_summary", "")
        metadata = _sanitize_for_ui(review_item.get("metadata", {}) or {})
        review_id = review_item.get("review_id", "unknown")

        label = f"{idx}. {title} | {status}"
        with st.expander(label, expanded=False):
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
            st.write(content_summary or "No content summary available.")
            st.write("**Metadata:**")
            st.json(metadata)