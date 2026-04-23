# Runbook

## Local Setup
1. Activate the project virtual environment
2. Install dependencies from `requirements.txt`
3. Ensure `.env` exists locally
4. Start the application from the project root

## Operational Checks
- uploads directory exists
- audit directory exists
- review directory exists
- vector store path exists
- `.env` file exists if LLM is enabled

## Important Paths
- app entry: `app.py`
- runtime vector store: `data/runtime/vector_store/chroma_db/`

## Recovery Notes
- if vector store is missing, rebuild retrieval indexes
- if `.env` is missing, restore local environment values manually
- never commit secrets or runtime storage
