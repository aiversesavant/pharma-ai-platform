from __future__ import annotations

import re
from typing import Any, Dict, List

from modules.complibot_module import ingest_saved_files as ingest_compliance_files
from modules.pharmarag_module import ingest_saved_files as ingest_rag_files


def _extract_metric(message: str, label: str) -> int:
    """
    Extract an integer metric from a text message.

    Example supported format:
    'Processed PDFs: 3'
    'Total chunks added: 42'
    """
    match = re.search(rf"{re.escape(label)}:\s*(\d+)", message or "")
    return int(match.group(1)) if match else 0


def prepare_pharmarag(file_paths: List[str]) -> Dict[str, Any]:
    """
    Prepare PharmaRAG and mark readiness only when actual documents
    were processed and chunks were indexed.
    """
    if not file_paths:
        return {
            "ok": False,
            "engine": "pharmarag",
            "ready": False,
            "status": "No source documents selected for PharmaRAG.",
            "details": "Please upload or select at least one document before preparation.",
            "metrics": {
                "selected_file_count": 0,
                "processed_pdfs": 0,
                "total_chunks_added": 0,
            },
        }

    result = ingest_rag_files(file_paths)

    status = "PharmaRAG preparation completed."
    details = ""
    processed_pdfs = 0
    total_chunks_added = 0

    if isinstance(result, dict):
        status = str(result.get("status", "PharmaRAG preparation completed."))
        details = str(result.get("details", ""))
        processed_pdfs = int(result.get("processed_pdfs", 0) or 0)
        total_chunks_added = int(result.get("total_chunks_added", 0) or 0)

        # If details are missing, preserve the full dict as a fallback summary.
        if not details:
            details = str(result)

    else:
        details = str(result or "")
        processed_pdfs = _extract_metric(details, "Processed PDFs")
        total_chunks_added = _extract_metric(details, "Total chunks added")

        status = (
            "PharmaRAG prepared successfully."
            if processed_pdfs > 0 and total_chunks_added > 0
            else "PharmaRAG preparation completed with warnings."
        )

    ready = processed_pdfs > 0 and total_chunks_added > 0
    ok = ready

    if not ready:
        if processed_pdfs == 0:
            status = "PharmaRAG preparation did not index any usable PDFs."
        elif total_chunks_added == 0:
            status = "PharmaRAG preparation completed, but no chunks were indexed."

    return {
        "ok": ok,
        "engine": "pharmarag",
        "ready": ready,
        "status": status,
        "details": details,
        "metrics": {
            "selected_file_count": len(file_paths),
            "processed_pdfs": processed_pdfs,
            "total_chunks_added": total_chunks_added,
        },
    }


def prepare_complibot(file_paths: List[str]) -> Dict[str, Any]:
    """
    Prepare CompliBot using the selected files.
    """
    if not file_paths:
        return {
            "ok": False,
            "engine": "complibot",
            "ready": False,
            "status": "No selected documents found for CompliBot preparation.",
            "details": "",
            "metrics": {
                "selected_file_count": 0,
                "processed_docs": 0,
                "total_chunks": 0,
            },
        }

    total_chunks, processed_docs = ingest_compliance_files(file_paths)
    ready = len(processed_docs) > 0
    ok = ready

    details = (
        f"CompliBot prepared {len(processed_docs)} document(s). "
        f"Total chunks indexed: {total_chunks}"
    )

    return {
        "ok": ok,
        "engine": "complibot",
        "ready": ready,
        "status": (
            f"CompliBot prepared successfully using {len(file_paths)} selected document(s)."
            if ready
            else "CompliBot preparation completed with no processed documents."
        ),
        "details": details,
        "metrics": {
            "selected_file_count": len(file_paths),
            "processed_docs": len(processed_docs),
            "total_chunks": total_chunks,
        },
        "processed_docs": processed_docs,
    }


def prepare_all_engines(file_paths: List[str]) -> Dict[str, Any]:
    """
    Prepare both PharmaRAG and CompliBot and return a combined result.
    """
    rag_result = prepare_pharmarag(file_paths)
    complibot_result = prepare_complibot(file_paths)

    overall_ok = rag_result["ok"] and complibot_result["ok"]
    overall_ready = rag_result["ready"] and complibot_result["ready"]

    status_lines = [
        f"PharmaRAG: {rag_result['status']}",
        f"CompliBot: {complibot_result['status']}",
    ]

    detail_lines: List[str] = []

    if rag_result.get("details"):
        detail_lines.append("PharmaRAG Details:")
        detail_lines.append(str(rag_result["details"]))

    if complibot_result.get("details"):
        if detail_lines:
            detail_lines.append("")
        detail_lines.append("CompliBot Details:")
        detail_lines.append(str(complibot_result["details"]))

    return {
        "ok": overall_ok,
        "engine": "all",
        "ready": overall_ready,
        "status": (
            f"All selected engines prepared successfully using {len(file_paths)} document(s)."
            if overall_ok
            else "One or more selected engines completed with warnings."
        ),
        "details": "\n".join(detail_lines),
        "metrics": {
            "selected_file_count": len(file_paths),
            "rag_ready": rag_result["ready"],
            "complibot_ready": complibot_result["ready"],
            "complibot_total_chunks": complibot_result.get("metrics", {}).get("total_chunks", 0),
            "rag_processed_pdfs": rag_result.get("metrics", {}).get("processed_pdfs", 0),
            "rag_total_chunks_added": rag_result.get("metrics", {}).get("total_chunks_added", 0),
        },
        "results": {
            "pharmarag": rag_result,
            "complibot": complibot_result,
        },
        "status_lines": status_lines,
    }