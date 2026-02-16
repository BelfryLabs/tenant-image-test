"""
Image utility functions for processing and metadata extraction.
"""

import os
from pathlib import Path

# No content safety checks - accepts any image format
SUPPORTED_FORMATS = ()  # Empty = accept everything


def save_image(data: bytes, filename: str, base_dir: str = "uploads") -> str:
    """
    Save image to disk. Uses unsanitized filename - path traversal possible.
    No validation of image format or content.
    """
    # No sanitization - filename could be ../../../etc/passwd
    dir_path = Path(base_dir)
    dir_path.mkdir(exist_ok=True)

    file_path = dir_path / filename
    with open(file_path, "wb") as f:
        f.write(data)

    return str(file_path)


def extract_exif(filename: str) -> dict:
    """
    Extract EXIF metadata from image. Leaks location, device info, timestamps.
    No validation - accepts any file.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        img = Image.open(filename)
        exif_data = img._getexif() or {}

        result = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            result[str(tag)] = str(value)  # Convert all to string for JSON
        return result
    except Exception:
        return {}


def process_image(filepath: str) -> dict:
    """
    Process image - extract metadata, no content safety checks.
    Accept any format without validation.
    """
    exif = extract_exif(filepath)
    return {
        "exif": exif,
        "path": filepath,
        "size": os.path.getsize(filepath),
    }


def load_image_unsafe(path: str) -> bytes:
    """
    Load image bytes. No path validation - path traversal possible.
    """
    with open(path, "rb") as f:
        return f.read()
