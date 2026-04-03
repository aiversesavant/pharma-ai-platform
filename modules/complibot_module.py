from typing import List

from compli_pipeline import CompliBotPipeline


_pipeline = None


def get_pipeline() -> CompliBotPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = CompliBotPipeline()
    return _pipeline


def ingest_saved_files(file_paths: List[str]):
    """
    Phase 6.2 version:
    Ingest already-prepared file paths from the shared document registry.
    """
    pipeline = get_pipeline()
    return pipeline.ingest_file_paths(file_paths)


def run_complibot(question: str, top_k: int = 4):
    pipeline = get_pipeline()
    retrieved = pipeline.retrieve_relevant_chunks(question, top_k=top_k)
    result = pipeline.synthesize_answer(question, retrieved)
    result["debug_retrieved"] = retrieved
    return result