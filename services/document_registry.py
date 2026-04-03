from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

from services.document_classifier import build_document_tags
from services.file_utils import (
    delete_file,
    ensure_dir,
    list_files_in_dir,
    reset_dir,
    save_uploaded_files,
)


DEFAULT_UPLOAD_DIR = "data/uploads"


def _build_document_version_fields(manifest: Dict) -> Dict:
    name = manifest.get("name", "")
    modified_at = manifest.get("modified_at", "")
    size_bytes = manifest.get("size_bytes", 0)

    version_source = f"{name}|{modified_at}|{size_bytes}"
    version_hash = hashlib.sha1(version_source.encode("utf-8")).hexdigest()[:12]

    return {
        "document_version": f"v-{version_hash}",
        "document_trace_id": f"{name}:{version_hash}",
    }


def _attach_tags(manifest: Dict) -> Dict:
    tagged = dict(manifest)
    tagged.update(build_document_tags(manifest.get("name", "")))
    tagged.update(_build_document_version_fields(manifest))
    return tagged


def prepare_uploaded_files(uploaded_files, target_dir: str = DEFAULT_UPLOAD_DIR) -> List[Dict]:
    if not uploaded_files:
        return []

    ensure_dir(target_dir)
    manifests = save_uploaded_files(uploaded_files, target_dir)
    return [_attach_tags(item) for item in manifests]


def list_prepared_files(target_dir: str = DEFAULT_UPLOAD_DIR) -> List[Dict]:
    manifests = list_files_in_dir(target_dir, extensions=(".pdf",))
    return [_attach_tags(item) for item in manifests]


def reset_prepared_files(target_dir: str = DEFAULT_UPLOAD_DIR) -> None:
    reset_dir(target_dir)


def remove_prepared_file(file_name: str, target_dir: str = DEFAULT_UPLOAD_DIR) -> bool:
    manifests = list_prepared_files(target_dir)

    for item in manifests:
        if item["name"] == file_name:
            return delete_file(item["path"])

    return False


def get_prepared_file_paths(target_dir: str = DEFAULT_UPLOAD_DIR) -> List[str]:
    manifests = list_prepared_files(target_dir)
    return [item["path"] for item in manifests]


def get_prepared_filenames(target_dir: str = DEFAULT_UPLOAD_DIR) -> List[str]:
    manifests = list_prepared_files(target_dir)
    return [item["name"] for item in manifests]


def get_prepared_file_map(target_dir: str = DEFAULT_UPLOAD_DIR) -> Dict[str, str]:
    manifests = list_prepared_files(target_dir)
    return {item["name"]: item["path"] for item in manifests}


def get_prepared_file_by_name(
    file_name: str,
    target_dir: str = DEFAULT_UPLOAD_DIR,
) -> Optional[Dict]:
    manifests = list_prepared_files(target_dir)

    for item in manifests:
        if item["name"] == file_name:
            return item

    return None


def filter_prepared_files(
    category: str = "All",
    target_dir: str = DEFAULT_UPLOAD_DIR,
) -> List[Dict]:
    manifests = list_prepared_files(target_dir)

    if category == "All":
        return manifests

    return [item for item in manifests if item.get("category") == category]


def get_prepared_file_paths_by_names(
    file_names: List[str],
    target_dir: str = DEFAULT_UPLOAD_DIR,
) -> List[str]:
    manifests = list_prepared_files(target_dir)
    selected = []

    wanted = set(file_names or [])

    for item in manifests:
        if item["name"] in wanted:
            selected.append(item["path"])

    return selected