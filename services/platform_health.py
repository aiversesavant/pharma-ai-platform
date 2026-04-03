from __future__ import annotations

import os
from typing import Dict

from services.llm_config import llm_is_configured


def get_platform_health() -> Dict[str, object]:
    upload_dir_exists = os.path.exists("data/uploads")
    audit_dir_exists = os.path.exists("data/audit")
    review_dir_exists = os.path.exists("data/review")
    chroma_dir_exists = os.path.exists("chroma_db")
    env_exists = os.path.exists(".env")

    checks = {
        "uploads_storage_ready": upload_dir_exists,
        "audit_storage_ready": audit_dir_exists,
        "review_storage_ready": review_dir_exists,
        "vector_store_ready": chroma_dir_exists,
        "local_env_file_present": env_exists,
        "llm_ready": llm_is_configured(),
    }

    all_core_ready = all([
        checks["uploads_storage_ready"],
        checks["audit_storage_ready"],
        checks["review_storage_ready"],
    ])

    return {
        "checks": checks,
        "core_ready": all_core_ready,
    }


def get_deployment_readiness_items() -> Dict[str, bool]:
    return {
        "env_file_is_local_only": True,
        "api_keys_not_hardcoded": True,
        "gitignore_should_include_env": True,
        "gitignore_should_exclude_runtime_data": True,
        "readme_should_be_finalized": False,
        "requirements_should_be_finalized": True,
        "huggingface_secrets_needed_for_llm": True,
    }