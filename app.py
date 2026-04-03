import hashlib

import streamlit as st

from router import (
    detect_route,
    get_route_description,
    get_route_label,
)
from services.audit_logger import (
    clear_audit_events,
    log_audit_event,
    read_audit_events,
)
from services.document_registry import (
    filter_prepared_files,
    get_prepared_file_by_name,
    get_prepared_file_map,
    get_prepared_file_paths_by_names,
    list_prepared_files,
    prepare_uploaded_files,
    remove_prepared_file,
    reset_prepared_files,
)
from services.engine_prep import (
    prepare_all_engines,
    prepare_complibot,
    prepare_pharmarag,
)
from services.llm_config import llm_status_summary
from services.platform_health import get_platform_health, get_deployment_readiness_items
from services.review_queue import (
    clear_review_items,
    create_review_item,
    filter_review_items,
    get_available_review_item_types,
    get_review_metrics,
    update_review_item_status,
)
from services.session_state import (
    initialize_session_state,
    refresh_audit_log_view,
    refresh_review_queue_view,
    refresh_uploader,
    reset_engine_state,
)
from services.ui_renderers import (
    render_audit_log_panel,
    render_complibot_result,
    render_document_history_header,
    render_document_history_table,
    render_engine_prep_result,
    render_latest_status_block,
    render_llm_status_panel,
    render_platform_health_panel,
    render_platform_status_row,
    render_prepare_all_result,
    render_rag_result,
    render_review_metrics,
    render_review_queue_panel,
    render_route_info,
    render_summarizer_result,
)
from modules.complibot_module import run_complibot
from modules.pharmarag_module import query_documents
from modules.pharmasummarizer_module import run_pharmasummarizer_from_path


def build_output_trace_id(route: str, source: str, version: str, user_input: str = "") -> str:
    raw = f"{route}|{source}|{version}|{user_input}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


st.set_page_config(page_title="PharmaAI Platform", page_icon="💊", layout="wide")

initialize_session_state()

st.title("💊 PharmaAI Platform")
st.markdown(
    "A unified workspace for pharma/regulatory Q&A, document summarization, and compliance/SOP assistance."
)

llm_status = llm_status_summary()
render_llm_status_panel(llm_status)

health = get_platform_health()
deployment_readiness = get_deployment_readiness_items()
render_platform_health_panel(health, deployment_readiness)

with st.sidebar:
    st.header("Prepare Documents")

    uploaded_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"platform_uploader_{st.session_state.uploader_key}",
    )

    st.caption(
        "Do not upload confidential, proprietary, patient-sensitive, or regulated documents "
        "to free-tier external AI services unless approved."
    )

    save_col, reset_col = st.columns(2)

    with save_col:
        if st.button("Save Files"):
            if not uploaded_files:
                st.warning("Please upload at least one PDF.")
                log_audit_event(
                    event_type="save_files",
                    status="warning",
                    details={"reason": "no_files_uploaded"},
                    actor="local_user",
                    module="platform",
                )
            else:
                manifests = prepare_uploaded_files(uploaded_files)
                st.session_state.prepared_docs = list_prepared_files()
                st.session_state.last_status = (
                    f"Saved {len(manifests)} file(s) into shared upload storage."
                )
                reset_engine_state()
                st.success("Files saved successfully.")
                log_audit_event(
                    event_type="save_files",
                    status="success",
                    details={
                        "saved_file_count": len(manifests),
                        "saved_files": [item["name"] for item in manifests],
                    },
                    actor="local_user",
                    module="document_registry",
                )
                refresh_audit_log_view()

    with reset_col:
        if st.button("Reset Files"):
            reset_prepared_files()
            st.session_state.prepared_docs = []
            st.session_state.selected_summary_file = None
            st.session_state.selected_source_docs = []
            st.session_state.last_status = "Prepared files were reset."
            reset_engine_state()
            refresh_uploader()
            st.success("Prepared files reset complete.")
            log_audit_event(
                event_type="reset_files",
                status="success",
                details={"message": "Prepared files were reset."},
                actor="local_user",
                module="document_registry",
            )
            refresh_audit_log_view()

    category_options = ["All", "SOP / Compliance", "Regulatory / Guideline", "General"]
    selected_category = st.selectbox(
        "Filter prepared documents by type",
        options=category_options,
        index=category_options.index(st.session_state.selected_category_filter)
        if st.session_state.selected_category_filter in category_options
        else 0,
    )
    st.session_state.selected_category_filter = selected_category

    prepared_docs = filter_prepared_files(selected_category)
    st.session_state.prepared_docs = prepared_docs

    render_document_history_header(prepared_docs)
    render_document_history_table(prepared_docs)

    visible_file_names = [item["name"] for item in prepared_docs]

    st.subheader("Select Source Documents")
    st.caption("Optional. Leave empty to prepare all currently visible filtered documents.")

    if visible_file_names:
        selected_docs = st.multiselect(
            "Choose documents for preparation and task scope",
            options=visible_file_names,
            default=[
                name for name in st.session_state.selected_source_docs if name in visible_file_names
            ],
        )
        st.session_state.selected_source_docs = selected_docs
    else:
        st.caption("No documents available for selection.")
        st.session_state.selected_source_docs = []

    if visible_file_names:
        st.markdown("**Remove a document**")

        remove_options = ["-- Select a file to remove --"] + visible_file_names
        remove_name = st.selectbox(
            "Select prepared file to remove",
            options=remove_options,
            index=0,
            key="remove_prepared_file_select",
        )

        if st.button("Remove Selected File"):
            if remove_name == "-- Select a file to remove --":
                st.warning("Please select a file to remove.")
                log_audit_event(
                    event_type="remove_file",
                    status="warning",
                    details={"reason": "no_file_selected"},
                    actor="local_user",
                    module="document_registry",
                )
            else:
                removed = remove_prepared_file(remove_name)
                if removed:
                    st.session_state.prepared_docs = filter_prepared_files(
                        st.session_state.selected_category_filter
                    )
                    st.session_state.last_status = f"Removed prepared file: {remove_name}"
                    reset_engine_state()

                    if st.session_state.selected_summary_file == remove_name:
                        st.session_state.selected_summary_file = None

                    if remove_name in st.session_state.selected_source_docs:
                        st.session_state.selected_source_docs = [
                            name for name in st.session_state.selected_source_docs if name != remove_name
                        ]

                    st.success(f"Removed {remove_name}")
                    log_audit_event(
                        event_type="remove_file",
                        status="success",
                        details={"removed_file": remove_name},
                        actor="local_user",
                        module="document_registry",
                        target_file=remove_name,
                    )
                    refresh_audit_log_view()
                    st.rerun()
                else:
                    st.warning("Could not remove the selected file.")
                    log_audit_event(
                        event_type="remove_file",
                        status="error",
                        details={"selected_file": remove_name},
                        actor="local_user",
                        module="document_registry",
                        target_file=remove_name,
                    )

    st.subheader("Prepare Engines")

    effective_source_docs = (
        st.session_state.selected_source_docs
        if st.session_state.selected_source_docs
        else visible_file_names
    )
    selected_file_paths = get_prepared_file_paths_by_names(effective_source_docs)

    if st.button("Prepare PharmaRAG"):
        prep_result = prepare_pharmarag(selected_file_paths)

        st.session_state.last_status = prep_result["details"] or prep_result["status"]
        st.session_state.rag_ready = prep_result["ready"]

        render_engine_prep_result(prep_result)
        log_audit_event(
            event_type="prepare_pharmarag",
            status="success" if prep_result.get("ok") else "warning",
            details={
                "selected_documents": effective_source_docs,
                "ready": prep_result.get("ready"),
                "status": prep_result.get("status"),
            },
            actor="local_user",
            module="pharmarag",
            route="pharmarag",
        )
        refresh_audit_log_view()

    if st.button("Prepare CompliBot"):
        prep_result = prepare_complibot(selected_file_paths)

        st.session_state.last_status = prep_result["details"] or prep_result["status"]
        st.session_state.complibot_ready = prep_result["ready"]

        render_engine_prep_result(prep_result)
        log_audit_event(
            event_type="prepare_complibot",
            status="success" if prep_result.get("ok") else "warning",
            details={
                "selected_documents": effective_source_docs,
                "ready": prep_result.get("ready"),
                "status": prep_result.get("status"),
            },
            actor="local_user",
            module="complibot",
            route="complibot",
        )
        refresh_audit_log_view()

    if st.button("Prepare All"):
        prep_result = prepare_all_engines(selected_file_paths)

        st.session_state.last_status = prep_result["details"] or prep_result["status"]
        st.session_state.rag_ready = prep_result["results"]["pharmarag"]["ready"]
        st.session_state.complibot_ready = prep_result["results"]["complibot"]["ready"]

        render_prepare_all_result(prep_result)
        log_audit_event(
            event_type="prepare_all_engines",
            status="success" if prep_result.get("ok") else "warning",
            details={
                "selected_documents": effective_source_docs,
                "rag_ready": prep_result["results"]["pharmarag"]["ready"],
                "complibot_ready": prep_result["results"]["complibot"]["ready"],
                "status": prep_result.get("status"),
            },
            actor="local_user",
            module="platform",
        )
        refresh_audit_log_view()

    render_latest_status_block(st.session_state.last_status)

all_prepared_docs = list_prepared_files()
prepared_file_count = len(all_prepared_docs)
prepared_file_map = get_prepared_file_map()

last_route_label = (
    get_route_label(st.session_state.last_route)
    if st.session_state.last_route
    else None
)

render_platform_status_row(
    prepared_file_count=prepared_file_count,
    rag_ready=st.session_state.rag_ready,
    complibot_ready=st.session_state.complibot_ready,
    last_route_label=last_route_label,
)

st.divider()

left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("Choose Task")
    mode = st.selectbox(
        "Task Mode",
        ["Auto", "PharmaRAG", "PharmaSummarizer", "CompliBot"],
    )

    user_input = st.text_area(
        "Ask a question or request a summary",
        placeholder=(
            "Examples:\n"
            "- Summarize this document\n"
            "- What does ICH E6 say about GCP?\n"
            "- What does this SOP say about deviation handling?"
        ),
        height=160,
    )

    all_file_names = [item["name"] for item in all_prepared_docs]
    summarizer_file_path = None
    selected_summary_manifest = None

    if all_file_names:
        summary_options = ["-- Select a file to summarize --"] + all_file_names

        default_index = 0
        if (
            st.session_state.selected_summary_file
            and st.session_state.selected_summary_file in all_file_names
        ):
            default_index = summary_options.index(st.session_state.selected_summary_file)

        selected_summary_file = st.selectbox(
            "Select file for summarization",
            options=summary_options,
            index=default_index,
        )

        if selected_summary_file == "-- Select a file to summarize --":
            st.session_state.selected_summary_file = None
            summarizer_file_path = None
        else:
            st.session_state.selected_summary_file = selected_summary_file
            summarizer_file_path = prepared_file_map.get(selected_summary_file)
            selected_summary_manifest = get_prepared_file_by_name(selected_summary_file)

    create_review = st.checkbox("Create review item for this output")
    run_clicked = st.button("Run")

with right_col:
    st.subheader("How to Use")
    st.markdown(
        """
        **Step 1**  
        Upload PDFs and click **Save Files**

        **Step 2**  
        Optionally filter and select source documents in the sidebar

        **Step 3**  
        Prepare the engine you need:
        - **PharmaRAG** for general Q&A
        - **CompliBot** for SOP/compliance Q&A
        - **PharmaSummarizer** does not require preparation

        **Step 4**  
        Ask a question or request a summary
        """
    )

    st.subheader("Engine Notes")
    st.markdown(
        """
        - **PharmaRAG** → general pharma/regulatory Q&A  
        - **PharmaSummarizer** → title, summary, highlights  
        - **CompliBot** → SOP/compliance/process answers
        """
    )

st.divider()

if run_clicked:
    if not all_prepared_docs:
        st.warning("Please upload and save at least one PDF first.")
        log_audit_event(
            event_type="run_task",
            status="warning",
            details={"reason": "no_prepared_documents"},
            actor="local_user",
            module="platform",
        )
        refresh_audit_log_view()
    else:
        route = detect_route(
            user_input=user_input,
            selected_mode=mode,
            prepared_file_count=prepared_file_count,
        )
        st.session_state.last_route = route

        render_route_info(
            route_label=get_route_label(route),
            route_description=get_route_description(route),
        )

        if route == "pharmasummarizer":
            if not summarizer_file_path:
                st.warning("Please select a file to summarize.")
                log_audit_event(
                    event_type="run_pharmasummarizer",
                    status="warning",
                    details={"reason": "no_summary_file_selected"},
                    actor="local_user",
                    module="pharmasummarizer",
                    route="pharmasummarizer",
                )
            else:
                result = run_pharmasummarizer_from_path(summarizer_file_path)
                if selected_summary_manifest:
                    result["trace_id"] = build_output_trace_id(
                        route="pharmasummarizer",
                        source=selected_summary_manifest.get("name", ""),
                        version=selected_summary_manifest.get("document_version", ""),
                    )
                    result["document_version"] = selected_summary_manifest.get("document_version", "")
                render_summarizer_result(result)

                if create_review and "error" not in result:
                    review_item = create_review_item(
                        item_type="summary_output",
                        title=result.get("title", "Document Summary Review"),
                        source=result.get("source", "Unknown"),
                        content_summary=result.get("summary", ""),
                        metadata={
                            "summary_mode": result.get("summary_mode"),
                            "document_type": result.get("document_type"),
                        },
                        trace_id=result.get("trace_id", ""),
                        document_version=result.get("document_version", ""),
                    )
                    st.success(f"Review item created: {review_item['review_id']}")
                    refresh_review_queue_view()

                log_audit_event(
                    event_type="run_pharmasummarizer",
                    status="success" if "error" not in result else "error",
                    details={
                        "selected_file": st.session_state.selected_summary_file,
                        "summary_mode": result.get("summary_mode"),
                        "document_type": result.get("document_type"),
                        "review_item_created": bool(create_review and "error" not in result),
                    },
                    actor="local_user",
                    module="pharmasummarizer",
                    route="pharmasummarizer",
                    target_file=st.session_state.selected_summary_file,
                    review_status="pending_review" if create_review and "error" not in result else None,
                    trace_id=result.get("trace_id"),
                    document_version=result.get("document_version"),
                )
            refresh_audit_log_view()

        elif route == "pharmarag":
            if not st.session_state.rag_ready:
                st.warning("PharmaRAG is not prepared yet. Select documents if needed, then click 'Prepare PharmaRAG' or 'Prepare All'.")
                log_audit_event(
                    event_type="run_pharmarag",
                    status="warning",
                    details={"reason": "pharmarag_not_prepared"},
                    actor="local_user",
                    module="pharmarag",
                    route="pharmarag",
                )
            elif not user_input.strip():
                st.warning("Please enter a question for PharmaRAG.")
                log_audit_event(
                    event_type="run_pharmarag",
                    status="warning",
                    details={"reason": "empty_question"},
                    actor="local_user",
                    module="pharmarag",
                    route="pharmarag",
                )
            else:
                result = query_documents(user_input, top_k=3)
                result["trace_id"] = build_output_trace_id(
                    route="pharmarag",
                    source=result.get("primary_citation", ""),
                    version="retrieval-context",
                    user_input=user_input,
                )
                result["document_version"] = "retrieval-context"
                render_rag_result(result)

                if create_review and not str(result.get("summary", "")).startswith("Error:"):
                    review_item = create_review_item(
                        item_type="rag_answer_review",
                        title="PharmaRAG Answer Review",
                        source=result.get("primary_citation", "Unknown"),
                        content_summary=result.get("summary", ""),
                        metadata={
                            "question": user_input,
                            "answer_mode": result.get("answer_mode"),
                        },
                        trace_id=result.get("trace_id", ""),
                        document_version=result.get("document_version", ""),
                    )
                    st.success(f"Review item created: {review_item['review_id']}")
                    refresh_review_queue_view()

                log_audit_event(
                    event_type="run_pharmarag",
                    status="success" if not str(result.get("summary", "")).startswith("Error:") else "error",
                    details={
                        "question": user_input,
                        "answer_mode": result.get("answer_mode"),
                        "primary_citation": result.get("primary_citation"),
                        "review_item_created": bool(create_review and not str(result.get("summary", "")).startswith("Error:")),
                    },
                    actor="local_user",
                    module="pharmarag",
                    route="pharmarag",
                    target_file=result.get("primary_citation"),
                    review_status="pending_review" if create_review and not str(result.get("summary", "")).startswith("Error:") else None,
                    trace_id=result.get("trace_id"),
                    document_version=result.get("document_version"),
                )
            refresh_audit_log_view()

        elif route == "complibot":
            if not st.session_state.complibot_ready:
                st.warning("CompliBot is not prepared yet. Select documents if needed, then click 'Prepare CompliBot' or 'Prepare All'.")
                log_audit_event(
                    event_type="run_complibot",
                    status="warning",
                    details={"reason": "complibot_not_prepared"},
                    actor="local_user",
                    module="complibot",
                    route="complibot",
                )
            elif not user_input.strip():
                st.warning("Please enter a question for CompliBot.")
                log_audit_event(
                    event_type="run_complibot",
                    status="warning",
                    details={"reason": "empty_question"},
                    actor="local_user",
                    module="complibot",
                    route="complibot",
                )
            else:
                result = run_complibot(user_input, top_k=4)
                result["trace_id"] = build_output_trace_id(
                    route="complibot",
                    source=result.get("source", ""),
                    version="retrieval-context",
                    user_input=user_input,
                )
                result["document_version"] = "retrieval-context"
                render_complibot_result(result)

                if create_review:
                    review_item = create_review_item(
                        item_type="compliance_answer_review",
                        title="CompliBot Answer Review",
                        source=result.get("source", "Unknown"),
                        content_summary=result.get("answer_summary", ""),
                        metadata={
                            "question": user_input,
                            "answer_mode": result.get("answer_mode"),
                        },
                        trace_id=result.get("trace_id", ""),
                        document_version=result.get("document_version", ""),
                    )
                    st.success(f"Review item created: {review_item['review_id']}")
                    refresh_review_queue_view()

                log_audit_event(
                    event_type="run_complibot",
                    status="success",
                    details={
                        "question": user_input,
                        "answer_mode": result.get("answer_mode"),
                        "primary_source": result.get("source"),
                        "review_item_created": bool(create_review),
                    },
                    actor="local_user",
                    module="complibot",
                    route="complibot",
                    target_file=result.get("source"),
                    review_status="pending_review" if create_review else None,
                    trace_id=result.get("trace_id"),
                    document_version=result.get("document_version"),
                )
            refresh_audit_log_view()

st.divider()

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    audit_events = read_audit_events(limit=50)
    render_audit_log_panel(audit_events)

    audit_action_cols = st.columns(2)
    with audit_action_cols[0]:
        if st.button("Refresh Audit Log"):
            refresh_audit_log_view()
            st.rerun()
    with audit_action_cols[1]:
        if st.button("Clear Audit Log"):
            clear_audit_events()
            log_audit_event(
                event_type="clear_audit_log",
                status="success",
                details={"message": "Audit log was cleared by user action."},
                actor="local_user",
                module="audit",
            )
            refresh_audit_log_view()
            st.success("Audit log cleared.")
            st.rerun()

with bottom_right:
    metrics = get_review_metrics()
    render_review_metrics(metrics)

    st.subheader("Review Queue Filters")

    status_options = ["All", "pending_review", "approved", "rejected"]
    selected_review_status = st.selectbox(
        "Filter by review status",
        options=status_options,
        index=status_options.index(st.session_state.review_status_filter)
        if st.session_state.review_status_filter in status_options
        else 0,
    )
    st.session_state.review_status_filter = selected_review_status

    available_item_types = get_available_review_item_types()
    item_type_options = ["All"] + available_item_types
    selected_review_item_type = st.selectbox(
        "Filter by review item type",
        options=item_type_options,
        index=item_type_options.index(st.session_state.review_item_type_filter)
        if st.session_state.review_item_type_filter in item_type_options
        else 0,
    )
    st.session_state.review_item_type_filter = selected_review_item_type

    pending_only = st.checkbox(
        "Show pending items only in decision controls",
        value=st.session_state.review_pending_only,
    )
    st.session_state.review_pending_only = pending_only

    filtered_review_items = filter_review_items(
        status_filter=st.session_state.review_status_filter,
        item_type_filter=st.session_state.review_item_type_filter,
        limit=50,
    )
    render_review_queue_panel(filtered_review_items)

    st.subheader("Review Decision Controls")

    decision_source_items = filtered_review_items
    if st.session_state.review_pending_only:
        decision_source_items = [
            item for item in filtered_review_items if item.get("status") == "pending_review"
        ]

    if decision_source_items:
        review_options = ["-- Select a review item --"] + [
            f"{item.get('review_id')} | {item.get('title')} | {item.get('status')}"
            for item in decision_source_items
        ]

        selected_review_option = st.selectbox(
            "Select review item",
            options=review_options,
            index=0,
        )

        decision_note = st.text_area(
            "Decision Note",
            placeholder="Optional note for approval or rejection",
            height=100,
        )

        review_action_cols = st.columns(2)

        with review_action_cols[0]:
            if st.button("Approve Review Item"):
                if selected_review_option == "-- Select a review item --":
                    st.warning("Please select a review item first.")
                else:
                    selected_review_id = selected_review_option.split(" | ")[0]
                    updated = update_review_item_status(
                        review_id=selected_review_id,
                        new_status="approved",
                        reviewed_by="local_reviewer",
                        decision_note=decision_note,
                    )
                    if updated:
                        st.success("Review item approved.")
                        log_audit_event(
                            event_type="review_item_approved",
                            status="success",
                            details={
                                "review_id": selected_review_id,
                                "decision_note": decision_note,
                            },
                            actor="local_reviewer",
                            module="review_queue",
                            review_status="approved",
                            trace_id=updated.get("trace_id"),
                            document_version=updated.get("document_version"),
                        )
                        refresh_review_queue_view()
                        refresh_audit_log_view()
                        st.rerun()
                    else:
                        st.error("Could not approve the selected review item.")

        with review_action_cols[1]:
            if st.button("Reject Review Item"):
                if selected_review_option == "-- Select a review item --":
                    st.warning("Please select a review item first.")
                else:
                    selected_review_id = selected_review_option.split(" | ")[0]
                    updated = update_review_item_status(
                        review_id=selected_review_id,
                        new_status="rejected",
                        reviewed_by="local_reviewer",
                        decision_note=decision_note,
                    )
                    if updated:
                        st.success("Review item rejected.")
                        log_audit_event(
                            event_type="review_item_rejected",
                            status="success",
                            details={
                                "review_id": selected_review_id,
                                "decision_note": decision_note,
                            },
                            actor="local_reviewer",
                            module="review_queue",
                            review_status="rejected",
                            trace_id=updated.get("trace_id"),
                            document_version=updated.get("document_version"),
                        )
                        refresh_review_queue_view()
                        refresh_audit_log_view()
                        st.rerun()
                    else:
                        st.error("Could not reject the selected review item.")
    else:
        st.caption("No review items available for the current filters and decision settings.")

    review_action_cols = st.columns(2)
    with review_action_cols[0]:
        if st.button("Refresh Review Queue"):
            refresh_review_queue_view()
            st.rerun()
    with review_action_cols[1]:
        if st.button("Clear Review Queue"):
            clear_review_items()
            log_audit_event(
                event_type="clear_review_queue",
                status="success",
                details={"message": "Review queue was cleared by user action."},
                actor="local_user",
                module="review_queue",
            )
            refresh_review_queue_view()
            refresh_audit_log_view()
            st.success("Review queue cleared.")
            st.rerun()