from __future__ import annotations

from typing import Dict


def classify_document(file_name: str) -> str:
    """
    Very lightweight filename-based document classification.
    This can be replaced later with metadata-based or LLM-based tagging.
    """
    name = (file_name or "").lower()

    sop_terms = [
        "sop",
        "capa",
        "deviation",
        "review_and_approval",
        "triage",
        "document_review",
    ]
    regulatory_terms = [
        "guideline",
        "gcp",
        "fda",
        "ema",
        "ich",
        "pharmacovigilance",
        "safety",
        "best-practices",
        "good-clinical-practice",
    ]

    if any(term in name for term in sop_terms):
        return "SOP / Compliance"

    if any(term in name for term in regulatory_terms):
        return "Regulatory / Guideline"

    return "General"


def build_document_tags(file_name: str) -> Dict[str, str]:
    """
    Return basic metadata tags for a prepared file.
    """
    category = classify_document(file_name)

    return {
        "category": category,
    }