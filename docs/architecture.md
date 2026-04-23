# Architecture

## Purpose
Pharma AI Platform is a modular AI-assisted workspace for pharma and compliance workflows.

## Core Entry Points
- `app.py` — main application entry point
- `router.py` — routing logic
- `compli_pipeline.py` — compliance pipeline

## Main Modules
- `modules/pharmarag_module.py`
- `modules/pharmasummarizer_module.py`
- `modules/complibot_module.py`

## Services
Shared services are under `services/` and include:
- file handling
- document registry
- engine preparation
- LLM configuration/client
- platform health
- review queue
- session state
- UI rendering

## Data Areas
- `data/uploads/` — uploaded files
- `data/audit/` — audit records
- `data/review/` — review queue artifacts
- `data/runtime/vector_store/chroma_db/` — runtime vector storage

## Notes
This project is being normalized to an enterprise workspace standard while preserving current behavior.
