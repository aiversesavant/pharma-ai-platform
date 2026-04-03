from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional


def ensure_dir(path: str) -> None:
    """Create a directory if it does not already exist."""
    os.makedirs(path, exist_ok=True)


def reset_dir(path: str) -> None:
    """Remove and recreate a directory."""
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """
    Keep filenames safe and simple for local storage.
    This is intentionally conservative.
    """
    keep_chars = (" ", ".", "_", "-")
    cleaned = "".join(c for c in filename if c.isalnum() or c in keep_chars).strip()
    return cleaned or "uploaded_file.pdf"


def _format_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds).strftime("%Y-%m-%d %H:%M:%S")


def build_file_manifest(file_path: str) -> Dict:
    """Return a richer manifest object for a saved file."""
    exists = os.path.exists(file_path)
    size_bytes = os.path.getsize(file_path) if exists else 0
    modified_ts = os.path.getmtime(file_path) if exists else None

    return {
        "name": os.path.basename(file_path),
        "path": file_path,
        "size_bytes": size_bytes,
        "size_kb": round(size_bytes / 1024, 2) if size_bytes else 0.0,
        "modified_at": _format_timestamp(modified_ts) if modified_ts else "Unknown",
        "exists": exists,
    }


def save_uploaded_files(uploaded_files, target_dir: str) -> List[Dict]:
    """
    Save uploaded Streamlit files to disk and return a list of manifest objects.
    Existing files with the same name are overwritten.
    """
    ensure_dir(target_dir)

    manifests: List[Dict] = []

    for uploaded_file in uploaded_files:
        safe_name = sanitize_filename(uploaded_file.name)
        save_path = os.path.join(target_dir, safe_name)

        with open(save_path, "wb") as f:
            f.write(uploaded_file.read())

        manifests.append(build_file_manifest(save_path))

    return manifests


def list_files_in_dir(
    target_dir: str,
    extensions: Optional[tuple[str, ...]] = None,
) -> List[Dict]:
    """
    List saved files in a directory as manifest objects.
    Optionally filter by file extension.
    """
    if not os.path.exists(target_dir):
        return []

    manifests: List[Dict] = []

    for name in sorted(os.listdir(target_dir)):
        path = os.path.join(target_dir, name)

        if not os.path.isfile(path):
            continue

        if extensions and not name.lower().endswith(tuple(ext.lower() for ext in extensions)):
            continue

        manifests.append(build_file_manifest(path))

    return manifests


def delete_file(file_path: str) -> bool:
    """
    Delete a single file if it exists.
    Returns True if deleted, False otherwise.
    """
    if os.path.exists(file_path) and os.path.isfile(file_path):
        os.remove(file_path)
        return True
    return False