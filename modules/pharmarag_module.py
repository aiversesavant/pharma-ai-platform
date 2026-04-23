import re
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from services.llm_client import generate_text
from services.llm_config import llm_is_configured


CHROMA_PATH = "data/runtime/vector_store/chroma_db"
COLLECTION_NAME = "pharmarag_docs"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embedding_model


def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        text_parts: List[str] = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts).strip()
    except Exception:
        return ""


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_into_sentences(text: str) -> List[str]:
    text = normalize_whitespace(text)
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def chunk_text(text: str, chunk_size: int = 900, overlap_sentences: int = 2) -> List[str]:
    text = normalize_whitespace(text)
    if not text:
        return []

    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_length = len(sentence)

        if current_chunk and current_length + sentence_length > chunk_size:
            chunks.append(" ".join(current_chunk).strip())

            overlap = (
                current_chunk[-overlap_sentences:]
                if len(current_chunk) >= overlap_sentences
                else current_chunk[:]
            )
            current_chunk = overlap[:]
            current_length = sum(len(s) for s in current_chunk) + max(len(current_chunk) - 1, 0)

        current_chunk.append(sentence)
        current_length += sentence_length + 1

    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks


def get_client():
    return chromadb.PersistentClient(path=CHROMA_PATH)


def get_collection():
    client = get_client()
    return client.get_or_create_collection(name=COLLECTION_NAME)


def reset_collection():
    client = get_client()
    existing = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing:
        client.delete_collection(COLLECTION_NAME)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def ingest_saved_files(file_paths: List[str]) -> str:
    if not file_paths:
        return "No files provided for ingestion."

    collection = reset_collection()

    total_chunks = 0
    processed_files = 0
    skipped_files: List[str] = []

    model = get_embedding_model()

    for file_path in file_paths:
        pdf_file = Path(file_path)

        text = extract_text_from_pdf(str(pdf_file))
        if not text:
            skipped_files.append(f"{pdf_file.name} (no extractable text)")
            continue

        chunks = chunk_text(text)
        if not chunks:
            skipped_files.append(f"{pdf_file.name} (no chunks created)")
            continue

        try:
            embeddings = model.encode(chunks).tolist()

            ids = [f"{pdf_file.stem}_{i}" for i in range(len(chunks))]
            metadatas = [
                {"source": pdf_file.name, "chunk_index": i}
                for i in range(len(chunks))
            ]

            collection.upsert(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            total_chunks += len(chunks)
            processed_files += 1

        except Exception as exc:
            skipped_files.append(f"{pdf_file.name} ({exc})")

    message = [
        "Ingestion complete.",
        f"Processed PDFs: {processed_files}",
        f"Total chunks added: {total_chunks}",
    ]

    if skipped_files:
        message.append("\nSkipped files:")
        message.extend(skipped_files)

    return "\n".join(message)


def keyword_overlap_score(text: str, user_query: str) -> int:
    query_terms = [w for w in re.findall(r"\b\w+\b", user_query.lower()) if len(w) > 3]
    text_lower = text.lower()
    return sum(3 for term in query_terms if term in text_lower)


def question_focus_score(text: str, user_query: str) -> int:
    text_lower = text.lower()
    query_lower = user_query.lower()

    score = 0

    patterns = [
        "must",
        "should",
        "required",
        "recommend",
        "include",
        "means",
        "defined",
        "responsible",
        "report",
        "documented",
        "within",
    ]
    for token in patterns:
        if token in text_lower:
            score += 1

    if "what" in query_lower and any(term in text_lower for term in ["is", "means", "defined", "refers to"]):
        score += 2

    if "how" in query_lower and any(term in text_lower for term in ["should", "must", "steps", "process"]):
        score += 2

    return score


def rerank_retrieved_chunks(
    documents: List[str],
    metadatas: List[dict],
    distances: Optional[List[float]],
    user_query: str,
) -> List[Dict]:
    candidates: List[Dict] = []

    for idx, (doc, meta) in enumerate(zip(documents, metadatas)):
        distance = distances[idx] if distances and idx < len(distances) else None

        vector_score = max(0.0, 10.0 - float(distance)) if distance is not None else 0.0
        keyword_score = float(keyword_overlap_score(doc, user_query))
        focus_score = float(question_focus_score(doc, user_query))

        total_score = (vector_score * 1.5) + (keyword_score * 2.0) + (focus_score * 1.2)

        candidates.append(
            {
                "score": total_score,
                "document": normalize_whitespace(doc),
                "metadata": meta,
                "distance": float(distance) if distance is not None else None,
            }
        )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def clean_excerpt(text: str, max_chars: int = 320) -> str:
    text = normalize_whitespace(text)
    if len(text) <= max_chars:
        return text

    clipped = text[:max_chars].rsplit(" ", 1)[0].strip()
    return clipped + "..."


def pick_best_sentences(text: str, user_query: str, max_sentences: int = 3) -> List[str]:
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    scored_sentences = []
    for sentence in sentences:
        score = keyword_overlap_score(sentence, user_query) + question_focus_score(sentence, user_query)
        scored_sentences.append((score, sentence))

    scored_sentences.sort(key=lambda x: x[0], reverse=True)

    selected = []
    seen = set()

    for score, sentence in scored_sentences:
        normalized = sentence.lower().strip()
        if normalized in seen:
            continue
        if len(sentence) < 35:
            continue

        selected.append(sentence)
        seen.add(normalized)

        if len(selected) >= max_sentences:
            break

    if not selected:
        selected = sentences[:max_sentences]

    return selected


def build_retrieval_summary(reranked_items: List[Dict], user_query: str) -> str:
    if not reranked_items:
        return "No relevant answer was found in the prepared documents."

    best_doc = reranked_items[0]["document"]
    selected_sentences = pick_best_sentences(best_doc, user_query, max_sentences=3)

    summary = " ".join(selected_sentences).strip()
    summary = normalize_whitespace(summary)

    if len(summary) > 700:
        summary = summary[:700].rsplit(" ", 1)[0] + "..."

    return summary or clean_excerpt(best_doc, max_chars=400)


def format_supporting_sources(reranked_items: List[Dict], top_k: int = 3) -> List[str]:
    lines: List[str] = []
    for item in reranked_items[:top_k]:
        meta = item["metadata"]
        score = item["score"]
        line = f"{meta['source']} | chunk {meta['chunk_index']} | relevance {score:.1f}"
        lines.append(line)
    return lines


def format_relevant_excerpts(reranked_items: List[Dict], top_k: int = 3) -> List[Dict]:
    excerpts: List[Dict] = []

    for item in reranked_items[:top_k]:
        meta = item["metadata"]
        excerpts.append(
            {
                "source": meta["source"],
                "chunk_index": meta["chunk_index"],
                "text": clean_excerpt(item["document"], max_chars=450),
            }
        )

    return excerpts


def build_rag_prompt(user_query: str, reranked_items: List[Dict], top_k: int = 3) -> str:
    context_blocks = []

    for idx, item in enumerate(reranked_items[:top_k], start=1):
        meta = item["metadata"]
        context_blocks.append(
            f"[Source {idx}] {meta['source']} | chunk {meta['chunk_index']}\n"
            f"{item['document']}"
        )

    context = "\n\n".join(context_blocks)

    return f"""
You are assisting with pharma and regulatory document question answering.

Answer the user's question using ONLY the grounded context below.
Do not invent facts.
If the context is insufficient, say that clearly.
Write a clean, concise professional answer in 1 to 3 short paragraphs.

User Question:
{user_query}

Grounded Context:
{context}

Return only the final answer text.
""".strip()


def build_answer_summary(user_query: str, reranked_items: List[Dict]) -> tuple[str, str]:
    retrieval_summary = build_retrieval_summary(reranked_items, user_query)

    if not llm_is_configured():
        return retrieval_summary, "retrieval"

    prompt = build_rag_prompt(user_query, reranked_items, top_k=3)
    llm_text = generate_text(prompt)

    if llm_text:
        return normalize_whitespace(llm_text), "llm"

    return retrieval_summary, "retrieval"


def query_documents(user_query: str, top_k: int = 3) -> Dict[str, object]:
    if not user_query.strip():
        return {
            "summary": "Please enter a question.",
            "primary_citation": "",
            "supporting_sources": [],
            "relevant_excerpts": [],
            "answer_note": "Enter a question to search the prepared documents.",
            "answer_mode": "retrieval",
        }

    try:
        collection = get_collection()

        if collection.count() == 0:
            return {
                "summary": "No documents are ingested yet. Please prepare PharmaRAG first.",
                "primary_citation": "",
                "supporting_sources": [],
                "relevant_excerpts": [],
                "answer_note": "PharmaRAG needs prepared documents before question answering can run.",
                "answer_mode": "retrieval",
            }

        model = get_embedding_model()
        query_embedding = model.encode([user_query]).tolist()[0]

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=max(top_k * 4, 12),
            include=["documents", "metadatas", "distances"],
        )

        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]

        reranked_items = rerank_retrieved_chunks(
            documents,
            metadatas,
            distances,
            user_query,
        )

        if not reranked_items:
            return {
                "summary": "No relevant answer was found in the prepared documents.",
                "primary_citation": "",
                "supporting_sources": [],
                "relevant_excerpts": [],
                "answer_note": "Try narrowing the selected source documents or rephrasing the question.",
                "answer_mode": "retrieval",
            }

        best_meta = reranked_items[0]["metadata"]
        summary, answer_mode = build_answer_summary(user_query, reranked_items)

        answer_note = (
            "LLM-assisted grounded synthesis using retrieved document chunks."
            if answer_mode == "llm"
            else "Retrieval-based answer synthesized from the most relevant prepared document chunks."
        )

        return {
            "summary": summary,
            "primary_citation": f"{best_meta['source']} | chunk {best_meta['chunk_index']}",
            "supporting_sources": format_supporting_sources(reranked_items, top_k=top_k),
            "relevant_excerpts": format_relevant_excerpts(reranked_items, top_k=top_k),
            "answer_note": answer_note,
            "answer_mode": answer_mode,
        }

    except Exception as exc:
        return {
            "summary": f"Error: {exc}",
            "primary_citation": "",
            "supporting_sources": [],
            "relevant_excerpts": [],
            "answer_note": "An unexpected retrieval error occurred.",
            "answer_mode": "retrieval",
        }