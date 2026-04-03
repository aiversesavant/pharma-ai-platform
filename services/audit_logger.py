from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


AUDIT_LOG_DIR = "data/audit"
AUDIT_LOG_FILE = os.path.join(AUDIT_LOG_DIR, "audit_log.jsonl")


def ensure_audit_log_storage() -> None:
    os.makedirs(AUDIT_LOG_DIR, exist_ok=True)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_audit_event(
    event_type: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    actor: str = "local_user",
    module: str = "platform",
    route: Optional[str] = None,
    target_file: Optional[str] = None,
    review_status: Optional[str] = None,
    trace_id: Optional[str] = None,
    document_version: Optional[str] = None,
) -> None:
    ensure_audit_log_storage()

    record = {
        "timestamp_utc": _utc_timestamp(),
        "event_type": event_type,
        "status": status,
        "actor": actor,
        "module": module,
        "route": route,
        "target_file": target_file,
        "review_status": review_status,
        "trace_id": trace_id,
        "document_version": document_version,
        "details": details or {},
    }

    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_audit_events(limit: int = 100) -> List[Dict[str, Any]]:
    ensure_audit_log_storage()

    if not os.path.exists(AUDIT_LOG_FILE):
        return []

    events: List[Dict[str, Any]] = []

    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    events.reverse()
    return events[:limit]


def clear_audit_events() -> None:
    ensure_audit_log_storage()
    with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("")