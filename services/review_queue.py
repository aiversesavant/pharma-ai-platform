from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


REVIEW_DIR = "data/review"
REVIEW_FILE = os.path.join(REVIEW_DIR, "review_queue.jsonl")


def ensure_review_storage() -> None:
    os.makedirs(REVIEW_DIR, exist_ok=True)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_all_review_items() -> List[Dict[str, Any]]:
    ensure_review_storage()

    if not os.path.exists(REVIEW_FILE):
        return []

    items: List[Dict[str, Any]] = []

    with open(REVIEW_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return items


def _write_all_review_items(items: List[Dict[str, Any]]) -> None:
    ensure_review_storage()

    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def create_review_item(
    item_type: str,
    title: str,
    source: str,
    content_summary: str,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: str = "",
    document_version: str = "",
) -> Dict[str, Any]:
    ensure_review_storage()

    review_item = {
        "review_id": str(uuid.uuid4()),
        "created_at_utc": _utc_timestamp(),
        "updated_at_utc": _utc_timestamp(),
        "status": "pending_review",
        "decision_note": "",
        "reviewed_by": "",
        "reviewed_at_utc": "",
        "item_type": item_type,
        "title": title,
        "source": source,
        "content_summary": content_summary,
        "trace_id": trace_id,
        "document_version": document_version,
        "metadata": metadata or {},
    }

    with open(REVIEW_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(review_item, ensure_ascii=False) + "\n")

    return review_item


def read_review_items(limit: int = 100) -> List[Dict[str, Any]]:
    items = _read_all_review_items()
    items.reverse()
    return items[:limit]


def get_review_item_by_id(review_id: str) -> Optional[Dict[str, Any]]:
    items = _read_all_review_items()
    for item in items:
        if item.get("review_id") == review_id:
            return item
    return None


def update_review_item_status(
    review_id: str,
    new_status: str,
    reviewed_by: str = "local_reviewer",
    decision_note: str = "",
) -> Optional[Dict[str, Any]]:
    valid_statuses = {"pending_review", "approved", "rejected"}
    if new_status not in valid_statuses:
        return None

    items = _read_all_review_items()
    updated_item: Optional[Dict[str, Any]] = None

    for item in items:
        if item.get("review_id") == review_id:
            item["status"] = new_status
            item["reviewed_by"] = reviewed_by
            item["reviewed_at_utc"] = _utc_timestamp()
            item["updated_at_utc"] = _utc_timestamp()
            item["decision_note"] = decision_note
            updated_item = item
            break

    if updated_item is not None:
        _write_all_review_items(items)

    return updated_item


def clear_review_items() -> None:
    ensure_review_storage()
    with open(REVIEW_FILE, "w", encoding="utf-8") as f:
        f.write("")


def filter_review_items(
    status_filter: str = "All",
    item_type_filter: str = "All",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    items = read_review_items(limit=limit)

    filtered = items

    if status_filter != "All":
        filtered = [item for item in filtered if item.get("status") == status_filter]

    if item_type_filter != "All":
        filtered = [item for item in filtered if item.get("item_type") == item_type_filter]

    return filtered


def get_review_metrics() -> Dict[str, int]:
    items = _read_all_review_items()

    metrics = {
        "total": len(items),
        "pending_review": 0,
        "approved": 0,
        "rejected": 0,
    }

    for item in items:
        status = item.get("status", "pending_review")
        if status in metrics:
            metrics[status] += 1

    return metrics


def get_available_review_item_types() -> List[str]:
    items = _read_all_review_items()
    types = sorted({item.get("item_type", "unknown") for item in items if item.get("item_type")})
    return types