"""Validation and local storage primitives for product image uploads."""

from dataclasses import dataclass
from pathlib import Path

from uuid6 import uuid7

MAX_IMAGE_BYTES = 2 * 1024 * 1024

_MIME_EXTENSIONS = {
    "image/jpeg": (".jpg", ".jpeg"),
    "image/png": (".png",),
    "image/webp": (".webp",),
}
_OUTPUT_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class UploadValidationError(ValueError):
    """A stable, client-safe upload validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ValidatedImage:
    content: bytes
    mime: str
    size: int
    extension: str


@dataclass(frozen=True, slots=True)
class StoredImage:
    path: str
    url: str
    size: int
    mime: str


def _detect_mime(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(content: bytes, declared_mime: str, original_filename: str) -> ValidatedImage:
    """Validate upload metadata and signature without decoding image contents."""
    size = len(content)
    if size == 0:
        raise UploadValidationError("empty_image", "Image must not be empty")
    if size > MAX_IMAGE_BYTES:
        raise UploadValidationError(
            "image_too_large", f"Image must not exceed {MAX_IMAGE_BYTES} bytes"
        )
    if declared_mime not in _MIME_EXTENSIONS:
        raise UploadValidationError("unsupported_mime", "Unsupported image MIME type")

    actual_mime = _detect_mime(content)
    if actual_mime is None:
        raise UploadValidationError(
            "invalid_image_signature", "Content is not a supported image"
        )
    if actual_mime != declared_mime:
        raise UploadValidationError(
            "mime_mismatch", "Declared MIME type does not match image content"
        )

    filename_extension = Path(original_filename).suffix.lower()
    if filename_extension not in _MIME_EXTENSIONS[actual_mime]:
        raise UploadValidationError(
            "extension_mismatch", "Filename extension does not match image content"
        )

    return ValidatedImage(
        content=content,
        mime=actual_mime,
        size=size,
        extension=_OUTPUT_EXTENSIONS[actual_mime],
    )


class LocalImageStorage:
    """Store validated images beneath one local root without overwriting files."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save(self, image: ValidatedImage) -> StoredImage:
        self.root.mkdir(parents=True, exist_ok=True)
        resolved_root = self.root.resolve()
        relative_path = f"{uuid7()}{image.extension}"
        target = (resolved_root / relative_path).resolve()
        if not target.is_relative_to(resolved_root):
            raise ValueError("Storage target must remain inside upload root")

        with target.open("xb") as destination:
            destination.write(image.content)

        return StoredImage(
            path=relative_path,
            url=relative_path,
            size=image.size,
            mime=image.mime,
        )
