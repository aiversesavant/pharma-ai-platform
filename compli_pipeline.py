from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from services.llm_client import generate_text
from services.llm_config import llm_is_configured


CHROMA_PATH = "data/runtime/vector_store/chroma_db"
COLLECTION_NAME = "complibot_docs"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


class CompliBotPipeline:
    def __init__(self) -> None:
        self._embedding_model: Optional[SentenceTransformer] = None

    def _get_embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return self._embedding_model

    def _get_client(self):
        return chromadb.PersistentClient(path=CHROMA_PATH)

    def _get_collection(self):
        client = self._get_client()
        return client.get_or_create_collection(name=COLLECTION_NAME)

    def _reset_collection(self):
        client = self._get_client()
        existing = [c.name for c in client.list_collections()]
        if COLLECTION_NAME in existing:
            client.delete_collection(COLLECTION_NAME)
        return client.get_or_create_collection(name=COLLECTION_NAME)

    @staticmethod
    def _extract_text_from_pdf(pdf_path: str) -> str:
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

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @classmethod
    def _chunk_text(cls, text: str, chunk_size: int = 850, overlap: int = 120) -> List[str]:
        text = cls._normalize_whitespace(text)
        if not text:
            return []

        chunks: List[str] = []
        start = 0
        length = len(text)

        while start < length:
            end = min(start + chunk_size, length)
            chunk = text[start:end]

            if end < length:
                last_period = chunk.rfind(". ")
                if last_period > int(chunk_size * 0.55):
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunk = cls._normalize_whitespace(chunk)
            if chunk:
                chunks.append(chunk)

            if end >= length:
                break

            start = max(end - overlap, start + 1)

        return chunks

    def ingest_file_paths(self, file_paths: List[str]) -> tuple[int, List[str]]:
        if not file_paths:
            return 0, []

        collection = self._reset_collection()
        model = self._get_embedding_model()

        total_chunks = 0
        processed_docs: List[str] = []

        for file_path in file_paths:
            pdf_file = Path(file_path)
            text = self._extract_text_from_pdf(str(pdf_file))
            if not text:
                continue

            chunks = self._chunk_text(text)
            if not chunks:
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
                processed_docs.append(pdf_file.name)
            except Exception:
                continue

        return total_chunks, processed_docs

    def retrieve_relevant_chunks(self, question: str, top_k: int = 4) -> List[Dict]:
        question = self._normalize_whitespace(question)
        if not question:
            return []

        try:
            collection = self._get_collection()
            if collection.count() == 0:
                return []

            model = self._get_embedding_model()
            query_embedding = model.encode([question]).tolist()[0]

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=max(top_k * 2, 8),
                include=["documents", "metadatas", "distances"],
            )

            documents = (results.get("documents") or [[]])[0]
            metadatas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]

            items: List[Dict] = []
            for idx, text in enumerate(documents):
                meta = metadatas[idx] if idx < len(metadatas) else {}
                distance = distances[idx] if idx < len(distances) else None

                normalized_text = self._normalize_whitespace(text)
                requirement_score = sum(
                    1
                    for token in ["must", "shall", "required", "ensure", "before", "within", "review", "approve"]
                    if token in normalized_text.lower()
                )

                vector_component = max(0.0, 10.0 - float(distance)) if distance is not None else 0.0
                ranking_score = (vector_component * 1.5) + (requirement_score * 2.0)

                item = {
                    "text": normalized_text,
                    "source": meta.get("source", "Unknown"),
                    "chunk_index": meta.get("chunk_index", "N/A"),
                    "ranking_score": ranking_score,
                }
                if distance is not None:
                    item["distance"] = float(distance)

                items.append(item)

            items.sort(key=lambda x: x.get("ranking_score", 0.0), reverse=True)
            return items[:top_k]
        except Exception:
            return []

    def _build_retrieval_summary(self, retrieved: List[Dict]) -> str:
        if not retrieved:
            return "Relevant compliance content was not found."

        best_text = self._normalize_whitespace(retrieved[0].get("text", ""))
        sentences = re.split(r"(?<=[.!?])\s+", best_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        summary_sentences = []
        for sentence in sentences:
            if len(sentence) < 35:
                continue
            summary_sentences.append(sentence)
            if len(summary_sentences) >= 2:
                break

        answer_summary = " ".join(summary_sentences).strip()
        if answer_summary:
            return answer_summary

        return best_text[:380].rsplit(" ", 1)[0] + "..." if len(best_text) > 380 else best_text

    def _build_llm_prompt(self, question: str, retrieved: List[Dict]) -> str:
        context_blocks = []

        for idx, item in enumerate(retrieved[:4], start=1):
            context_blocks.append(
                f"[Source {idx}] {item.get('source', 'Unknown')} | chunk {item.get('chunk_index', 'N/A')}\n"
                f"{item.get('text', '')}"
            )

        context = "\n\n".join(context_blocks)

        return f"""
You are assisting with compliance and SOP question answering for pharma workflows.

Answer the user's question using ONLY the grounded context below.
Do not invent requirements.
If the evidence is insufficient, say so clearly.
Write a concise professional answer and focus on what must be done, reviewed, approved, or documented.

User Question:
{question}

Grounded Context:
{context}

Return only the final answer text.
""".strip()

    def synthesize_answer(self, question: str, retrieved: List[Dict]) -> Dict:
        if not retrieved:
            return {
                "answer_summary": (
                    "No compliance evidence was retrieved yet. "
                    "Prepare CompliBot and ensure PDFs contain extractable text."
                ),
                "procedure_guidance": "Add or prepare documents, then ask the question again.",
                "source": "No grounded source found",
                "key_requirements": [],
                "evidence": [],
                "compliance_note": (
                    "This is a retrieval-based guidance output and is not legal or regulatory advice."
                ),
                "answer_mode": "retrieval",
            }

        best = retrieved[0]
        best_text = self._normalize_whitespace(best.get("text", ""))

        summary = self._build_retrieval_summary(retrieved)
        answer_mode = "retrieval"

        if llm_is_configured():
            prompt = self._build_llm_prompt(question, retrieved)
            llm_text = generate_text(prompt)
            if llm_text:
                summary = self._normalize_whitespace(llm_text)
                answer_mode = "llm"

        sentences = re.split(r"(?<=[.!?])\s+", best_text)
        sentences = [s.strip() for s in sentences if s.strip()]

        requirements = [
            s.strip()
            for s in sentences
            if any(
                token in s.lower()
                for token in ["must", "shall", "required", "ensure", "before", "within", "review", "approve"]
            )
        ]
        if not requirements:
            requirements = [s.strip() for s in sentences if s.strip()][:3]

        procedure_guidance = (
            "Use the cited SOP or compliance section as the primary reference, then confirm role-specific "
            "steps, approvals, reviewers, and timelines in the full source document."
        )

        cleaned_evidence = []
        for item in retrieved[:5]:
            evidence_text = item.get("text", "")
            if len(evidence_text) > 420:
                evidence_text = evidence_text[:420].rsplit(" ", 1)[0] + "..."

            cleaned_item = dict(item)
            cleaned_item["text"] = evidence_text
            cleaned_evidence.append(cleaned_item)

        compliance_note = (
            "LLM-assisted grounded compliance synthesis. Confirm final decisions with your validated SOP, QA process, and approved workflow."
            if answer_mode == "llm"
            else "Interpretation support only. Confirm final decisions with your validated SOP, QA process, and approved workflow."
        )

        return {
            "answer_summary": summary or "Relevant compliance content was found.",
            "procedure_guidance": procedure_guidance,
            "source": f"{best.get('source', 'Unknown')} | chunk {best.get('chunk_index', 'N/A')}",
            "key_requirements": requirements[:5],
            "evidence": cleaned_evidence,
            "compliance_note": compliance_note,
            "answer_mode": answer_mode,
        }