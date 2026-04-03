from __future__ import annotations

from typing import Dict, List

from modules.complibot_module import ingest_saved_files as ingest_compliance_files
from modules.pharmarag_module import ingest_saved_files as ingest_rag_files


def prepare_pharmarag(file_paths: List[str]) -> Dict:
    if not file_paths:
        return {
            "ok": False,
            "engine": "pharmarag",
            "ready": False,
            "status": "No selected documents found for PharmaRAG preparation.",
            "details": "",
            "metrics": {
                "selected_file_count": 0,
            },
        }

    status = ingest_rag_files(file_paths)
    ready = "Ingestion complete." in status

    return {
        "ok": ready,
        "engine": "pharmarag",
        "ready": ready,
        "status": (
            f"PharmaRAG prepared successfully using {len(file_paths)} selected document(s)."
            if ready
            else "PharmaRAG preparation completed with warnings."
        ),
        "details": status,
        "metrics": {
            "selected_file_count": len(file_paths),
        },
    }


def prepare_complibot(file_paths: List[str]) -> Dict:
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

    details = (
        f"CompliBot prepared {len(processed_docs)} document(s). "
        f"Total chunks indexed: {total_chunks}"
    )

    return {
        "ok": ready,
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


def prepare_all_engines(file_paths: List[str]) -> Dict:
    rag_result = prepare_pharmarag(file_paths)
    complibot_result = prepare_complibot(file_paths)

    overall_ok = rag_result["ok"] and complibot_result["ok"]

    status_lines = [
        f"PharmaRAG: {rag_result['status']}",
        f"CompliBot: {complibot_result['status']}",
    ]

    detail_lines = []
    if rag_result.get("details"):
        detail_lines.append("PharmaRAG Details:")
        detail_lines.append(rag_result["details"])

    if complibot_result.get("details"):
        detail_lines.append("")
        detail_lines.append("CompliBot Details:")
        detail_lines.append(complibot_result["details"])

    return {
        "ok": overall_ok,
        "engine": "all",
        "ready": rag_result["ready"] and complibot_result["ready"],
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
        },
        "results": {
            "pharmarag": rag_result,
            "complibot": complibot_result,
        },
        "status_lines": status_lines,
    }