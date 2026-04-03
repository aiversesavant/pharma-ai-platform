from typing import Literal


RouteType = Literal["pharmarag", "pharmasummarizer", "complibot"]


ROUTE_LABELS = {
    "pharmarag": "PharmaRAG",
    "pharmasummarizer": "PharmaSummarizer",
    "complibot": "CompliBot",
}

ROUTE_DESCRIPTIONS = {
    "pharmarag": "General pharma/regulatory question answering over prepared documents.",
    "pharmasummarizer": "Document title extraction, summary, and key highlights.",
    "complibot": "Compliance, SOP, deviation, CAPA, and policy/process assistance.",
}


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _is_summary_request(text: str) -> bool:
    return any(term in text for term in [
        "summarize",
        "summary",
        "summarise",
        "key highlights",
        "highlights",
        "title of this document",
        "what is this document about",
        "give me the summary",
        "summarize this document",
        "summarize this pdf",
    ])


def _is_compliance_request(text: str) -> bool:
    return any(term in text for term in [
        "sop",
        "deviation",
        "capa",
        "approval process",
        "review process",
        "document review",
        "training requirement",
        "policy requirement",
        "quality event",
        "escalation",
        "compliance",
        "must be documented",
        "what does this sop say",
        "procedure",
    ])


def _is_general_rag_request(text: str) -> bool:
    return any(term in text for term in [
        "guideline",
        "regulatory",
        "what does ich",
        "what does fda",
        "what does ema",
        "what does this guideline say",
        "what is pharmacovigilance",
        "gcp",
        "safety reporting",
        "adverse event",
        "clinical practice",
        "regulatory requirement",
    ])


def detect_route(
    user_input: str,
    selected_mode: str,
    prepared_file_count: int = 0,
) -> RouteType:
    """
    Decide which engine should handle the current request.

    Rules:
    1. Explicit user mode wins.
    2. In Auto mode:
       - empty input + files -> summarizer
       - summary request -> summarizer
       - compliance/SOP request -> complibot
       - broad pharma/regulatory request -> pharmarag
       - fallback -> pharmarag
    """
    explicit_mapping = {
        "PharmaRAG": "pharmarag",
        "PharmaSummarizer": "pharmasummarizer",
        "CompliBot": "complibot",
    }

    if selected_mode in explicit_mapping:
        return explicit_mapping[selected_mode]

    text = _normalize(user_input)

    if not text:
        if prepared_file_count > 0:
            return "pharmasummarizer"
        return "pharmarag"

    if _is_summary_request(text):
        return "pharmasummarizer"

    if _is_compliance_request(text):
        return "complibot"

    if _is_general_rag_request(text):
        return "pharmarag"

    if prepared_file_count >= 2:
        return "pharmarag"

    return "pharmarag"


def get_route_label(route: str) -> str:
    return ROUTE_LABELS.get(route, route)


def get_route_description(route: str) -> str:
    return ROUTE_DESCRIPTIONS.get(route, "No description available for this route.")