# 💊 PharmaAI Platform

PharmaAI Platform is a unified AI-assisted document intelligence workspace for pharmaceutical, regulatory, and compliance-oriented workflows.

It combines:
- **PharmaRAG** for grounded question answering over prepared pharma/regulatory documents
- **PharmaSummarizer** for structured single-document summarization
- **CompliBot** for compliance/SOP-focused guidance with evidence and review support

The platform also includes:
- prepared document history
- source filtering
- document version awareness
- traceability metadata
- audit logging
- review queue
- approval / rejection workflow foundation
- optional LLM-ready answer synthesis layer

---

# 1. Project Purpose

This project was built to demonstrate how a pharma-focused AI platform can support:

- regulatory question answering
- SOP/compliance interpretation support
- structured document summarization
- human review workflows
- auditability and traceability
- deployment-ready product thinking

This is a **prototype / demo platform**, not a validated GxP production system.

---

# 2. Core Modules

## PharmaRAG
PharmaRAG supports grounded Q&A over prepared documents.

Typical use cases:
- “What does ICH E6 say about GCP?”
- “What does this guideline say about safety communication?”
- “What is pharmacovigilance according to these documents?”

Core functions:
- ingest prepared PDFs
- chunk and embed text
- retrieve relevant chunks
- rerank evidence
- generate answer summaries with citations and excerpts
- optional LLM-assisted grounded synthesis

---

## PharmaSummarizer
PharmaSummarizer generates structured summaries for one selected document.

Typical use cases:
- summarize a regulatory guideline
- summarize an SOP
- extract key highlights from a document

Core functions:
- title extraction
- structured summary generation
- key highlight extraction
- detected section inference
- document type labeling
- trace ID and document version display
- optional LLM-ready summary enhancement

---

## CompliBot
CompliBot supports compliance/SOP-focused question answering.

Typical use cases:
- “What does this SOP say about deviation handling?”
- “What approvals are required?”
- “What must be documented before closure?”

Core functions:
- retrieve compliance-relevant chunks
- extract key requirements
- provide evidence-backed procedure guidance
- support review workflow and traceability

---

# 3. Enterprise / Compliance-Oriented Features

The platform includes foundational workflow and traceability features:

- **Audit Log**
  - records major platform actions
  - tracks runs, file operations, review actions, and approvals

- **Review Queue**
  - create review items from outputs
  - track pending / approved / rejected states
  - support human-in-the-loop review

- **Traceability**
  - document version awareness
  - trace IDs for outputs
  - audit/review linkage

These are **foundational compliance-oriented features**, not full validated regulatory controls.

---

# 4. Technology Stack

- **Frontend / App Layer:** Streamlit
- **Language:** Python
- **Document Parsing:** PyMuPDF (`fitz`), PyPDF
- **Embeddings:** Sentence Transformers
- **Vector Store:** ChromaDB
- **Optional LLM Layer:** Gemini-ready integration via environment configuration
- **Local Storage:** JSONL-based audit log and review queue
- **Environment Handling:** python-dotenv

---

# 5. Project Structure

```text
pharma-ai-platform/
├── app.py
├── router.py
├── requirements.txt
├── .gitignore
├── .env.example
├── README.md
├── DEPLOYMENT_CHECKLIST.md
├── modules/
│   ├── __init__.py
│   ├── pharmarag_module.py
│   ├── pharmasummarizer_module.py
│   └── complibot_module.py
├── services/
│   ├── __init__.py
│   ├── audit_logger.py
│   ├── document_classifier.py
│   ├── document_registry.py
│   ├── engine_prep.py
│   ├── file_utils.py
│   ├── llm_client.py
│   ├── llm_config.py
│   ├── platform_health.py
│   ├── review_queue.py
│   ├── session_state.py
│   └── ui_renderers.py
├── data/
│   ├── uploads/
│   ├── audit/
│   └── review/
└── chroma_db/