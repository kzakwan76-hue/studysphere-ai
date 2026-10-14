"""Saving and deleting uploaded files. The user's filename never becomes part of a path."""

import logging
import uuid

from app.config import get_settings

logger = logging.getLogger("studysphere.storage")


def save_upload(user_id: int, extension: str, data: bytes) -> str:
    """Write the file under a random name and return its path relative to the uploads folder."""
    folder = get_settings().uploads_dir / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (folder / stored_name).write_bytes(data)
    return f"{user_id}/{stored_name}"


def delete_upload(relative_path: str) -> None:
    """Delete a stored file, but never anything outside the uploads folder."""
    base = get_settings().uploads_dir.resolve()
    target = (base / relative_path).resolve()
    if base not in target.parents:
        logger.error("Refusing to delete a path outside the uploads folder: %s", relative_path)
        return
    target.unlink(missing_ok=True)