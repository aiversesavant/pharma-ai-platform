import re
from pathlib import Path
from typing import Dict, List

import fitz

from services.llm_client import generate_text
from services.llm_config import llm_is_configured


NOISE_PATTERNS = [
    "www.",
    "email:",
    "phone:",
    "fax:",
    "additional copies are available",
    "office of communications",
    "division of drug information",
    "new hampshire ave",
    "silver spring",
    "reproduction is authorised",
    "see websites for contact details",
    "heads of medicines agencies",
    "an agency of the european union",
    "committee for human medicinal products",
    "page ",
    "table of contents",
    "document history",
    "regulatory history",
    "draft revision",
    "date for coming into effect",
    "final adoption",
    "start of public consultation",
    "end of consultation",
    "effective date",
]

TITLE_KEYWORDS = [
    "guideline",
    "best practices",
    "pharmacovigilance",
    "clinical practice",
    "module",
    "drug safety",
    "sop",
    "deviation",
    "capa",
]

BODY_START_HINTS = [
    "introduction",
    "objectives",
    "scope",
    "background",
    "purpose",
    "risk-based approach",
    "pharmacovigilance system",
    "clinical practice",
    "the principles of ich gcp",
    "structures and processes",
    "this guideline",
    "this document",
    "executive summary",
    "procedure",
    "responsibilities",
]

SECTION_HINTS = {
    "Purpose": ["purpose", "objective", "aim"],
    "Scope": ["scope", "applies to", "application"],
    "Responsibilities": ["responsibilities", "responsibility", "roles"],
    "Process": ["procedure", "process", "steps", "workflow"],
    "Compliance Notes": ["must", "shall", "required", "ensure", "documented"],
}


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text_parts: List[str] = []

    for page in doc:
        page_text = page.get_text()
        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()


def extract_text_from_pdf_path(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_parts: List[str] = []

    for page in doc:
        page_text = page.get_text()
        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()


def clean_preview_text(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines = []

    blank_count = 0
    for line in lines:
        if not line.strip():
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def get_clean_lines(text: str) -> List[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_noise_line(line: str) -> bool:
    lowered = line.lower().strip()
    if not lowered:
        return True
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def normalize_sentence(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence).strip()
    sentence = re.sub(r"^\d+\s+", "", sentence)
    sentence = re.sub(r"^[•\-]+\s*", "", sentence)
    return sentence


def split_sentences(text: str) -> List[str]:
    text = text.replace("\n", " ")
    raw = re.split(r"(?<=[.!?])\s+", text)
    normalized = [normalize_sentence(s) for s in raw]
    return [s for s in normalized if s and len(s) > 20]


def extract_title(text: str) -> str:
    lines = get_clean_lines(text)

    for i, line in enumerate(lines[:80]):
        lowered = line.lower()

        if is_noise_line(line):
            continue

        if any(keyword in lowered for keyword in TITLE_KEYWORDS):
            title_parts = [line]

            for j in range(1, 4):
                if i + j < len(lines):
                    next_line = lines[i + j].strip()
                    next_lower = next_line.lower()

                    if is_noise_line(next_line):
                        continue
                    if len(next_line) > 100:
                        continue
                    if any(x in next_lower for x in [
                        "date",
                        "page",
                        "table of contents",
                        "document history",
                        "draft revision",
                        "adopted by",
                        "public consultation",
                    ]):
                        continue

                    title_parts.append(next_line)

            title = " ".join(title_parts).strip()
            title = re.sub(r"\s+", " ", title)
            return title

    for line in lines:
        if not is_noise_line(line) and len(line) > 10:
            return line

    return "Untitled Document"


def find_body_sentences(text: str) -> List[str]:
    sentences = split_sentences(text)

    meaningful = []
    started = False

    for sentence in sentences:
        lowered = sentence.lower()

        if any(pattern in lowered for pattern in NOISE_PATTERNS):
            continue

        if len(sentence) < 50:
            continue

        if not started and any(hint in lowered for hint in BODY_START_HINTS):
            started = True

        if started:
            meaningful.append(sentence)

    if not meaningful:
        meaningful = [s for s in sentences if len(s) >= 50]

    return meaningful


def summarize_text(text: str) -> str:
    sentences = find_body_sentences(text)

    if not sentences:
        return "No meaningful summary could be generated from the PDF."

    summary = ". ".join(sentences[:3]).strip()
    if summary and not summary.endswith("."):
        summary += "."
    return summary


def extract_key_highlights(text: str, max_points: int = 5) -> List[str]:
    sentences = find_body_sentences(text)

    keywords = [
        "must",
        "should",
        "required",
        "recommended",
        "safety",
        "risk",
        "surveillance",
        "pharmacovigilance",
        "reporting",
        "monitoring",
        "system",
        "master file",
        "guideline",
        "clinical trial",
        "approval",
        "review",
        "deviation",
        "capa",
    ]

    highlights = []
    seen = set()

    for sentence in sentences:
        lowered = sentence.lower()

        if any(keyword in lowered for keyword in keywords):
            norm = lowered.strip()
            if norm not in seen:
                highlights.append(sentence)
                seen.add(norm)

        if len(highlights) >= max_points:
            break

    if not highlights:
        highlights = sentences[:max_points]

    return highlights[:max_points]


def infer_document_type(source_name: str, text: str) -> str:
    name = (source_name or "").lower()
    text_lower = text.lower()

    if "sop" in name or any(term in text_lower for term in ["procedure", "deviation", "capa", "approval workflow"]):
        return "SOP / Compliance Document"

    if any(term in name for term in ["guideline", "ich", "fda", "ema"]):
        return "Regulatory / Guideline Document"

    return "General Pharma Document"


def extract_sections(text: str) -> Dict[str, str]:
    sentences = find_body_sentences(text)
    section_map: Dict[str, str] = {}

    for section_name, hints in SECTION_HINTS.items():
        matched = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(hint in lowered for hint in hints):
                matched.append(sentence)
            if len(matched) >= 2:
                break

        if matched:
            section_map[section_name] = " ".join(matched)

    return section_map


def build_structured_summary(summary: str, highlights: List[str], sections: Dict[str, str]) -> str:
    parts = [summary]

    if sections.get("Purpose"):
        parts.append(f"Purpose: {sections['Purpose']}")

    if sections.get("Scope"):
        parts.append(f"Scope: {sections['Scope']}")

    if highlights:
        parts.append(f"Key point: {highlights[0]}")

    return "\n\n".join(parts).strip()


def build_llm_summary_prompt(title: str, source_name: str, summary: str, highlights: List[str], sections: Dict[str, str]) -> str:
    section_text = "\n".join(f"{k}: {v}" for k, v in sections.items()) if sections else "None"
    highlight_text = "\n".join(f"- {h}" for h in highlights[:5]) if highlights else "None"

    return f"""
You are assisting with pharma document summarization.

Rewrite the following extracted summary into a cleaner professional summary.
Use only the provided content.
Do not invent facts.
Keep the answer concise and structured.

Document Title:
{title}

Source File:
{source_name}

Current Summary:
{summary}

Highlights:
{highlight_text}

Extracted Sections:
{section_text}

Return only the improved summary text.
""".strip()


def maybe_enhance_summary_with_llm(
    title: str,
    source_name: str,
    summary: str,
    highlights: List[str],
    sections: Dict[str, str],
) -> tuple[str, str]:
    structured_summary = build_structured_summary(summary, highlights, sections)

    if not llm_is_configured():
        return structured_summary, "rule_based"

    prompt = build_llm_summary_prompt(title, source_name, structured_summary, highlights, sections)
    llm_text = generate_text(prompt)

    if llm_text:
        return llm_text.strip(), "llm"

    return structured_summary, "rule_based"


def _build_summary_result(extracted_text: str, source_name: str) -> Dict:
    title = extract_title(extracted_text)
    summary = summarize_text(extracted_text)
    highlights = extract_key_highlights(extracted_text)
    preview_text = clean_preview_text(extracted_text)
    sections = extract_sections(extracted_text)
    document_type = infer_document_type(source_name, extracted_text)
    structured_summary, summary_mode = maybe_enhance_summary_with_llm(
        title=title,
        source_name=source_name,
        summary=summary,
        highlights=highlights,
        sections=sections,
    )

    return {
        "title": title,
        "document_type": document_type,
        "summary": structured_summary,
        "highlights": highlights,
        "sections": sections,
        "preview_text": preview_text[:4000],
        "source": source_name,
        "summary_mode": summary_mode,
        "summary_note": (
            "LLM-enhanced summary generated from extracted document content."
            if summary_mode == "llm"
            else "Structured summary generated from extracted document content."
        ),
    }


def run_pharmasummarizer_from_path(file_path: str) -> Dict:
    if not file_path:
        return {"error": "No file path provided."}

    path_obj = Path(file_path)
    if not path_obj.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        extracted_text = extract_text_from_pdf_path(file_path)

        if not extracted_text:
            return {"error": "No readable text could be extracted from the PDF."}

        return _build_summary_result(extracted_text, path_obj.name)

    except Exception as exc:
        return {"error": f"Failed to summarize PDF: {exc}"}


def run_pharmasummarizer(uploaded_files) -> Dict:
    if not uploaded_files:
        return {"error": "Please upload at least one PDF."}

    uploaded_file = uploaded_files[0]

    try:
        pdf_bytes = uploaded_file.read()
        extracted_text = extract_text_from_pdf_bytes(pdf_bytes)

        if not extracted_text:
            return {"error": "No readable text could be extracted from the PDF."}

        return _build_summary_result(extracted_text, uploaded_file.name)

    except Exception as exc:
        return {"error": f"Failed to summarize PDF: {exc}"}