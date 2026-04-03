from __future__ import annotations

import streamlit as st


DEFAULT_SESSION_STATE = {
    "prepared_docs": [],
    "last_status": "",
    "rag_ready": False,
    "complibot_ready": False,
    "last_route": None,
    "selected_summary_file": None,
    "uploader_key": 0,
    "selected_category_filter": "All",
    "selected_source_docs": [],
    "audit_refresh_counter": 0,
    "review_refresh_counter": 0,
    "review_status_filter": "All",
    "review_item_type_filter": "All",
    "review_pending_only": False,
}


def initialize_session_state() -> None:
    for key, default_value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_engine_state() -> None:
    st.session_state["rag_ready"] = False
    st.session_state["complibot_ready"] = False
    st.session_state["last_route"] = None


def reset_platform_state() -> None:
    for key, default_value in DEFAULT_SESSION_STATE.items():
        st.session_state[key] = default_value


def refresh_uploader() -> None:
    st.session_state["uploader_key"] += 1


def refresh_audit_log_view() -> None:
    st.session_state["audit_refresh_counter"] += 1


def refresh_review_queue_view() -> None:
    st.session_state["review_refresh_counter"] += 1