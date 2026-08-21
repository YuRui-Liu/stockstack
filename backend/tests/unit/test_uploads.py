from pathlib import Path

import pytest

from app.catalog.uploads import (
    MAX_IMAGE_BYTES,
    LocalImageStorage,
    UploadValidationError,
    validate_image,
)

PNG = b"\x89PNG\r\n\x1a\n"
JPEG = b"\xff\xd8\xff"
WEBP = b"RIFF\x00\x00\x00\x00WEBP"


def test_rejects_shell_script_disguised_as_png() -> None:
    with pytest.raises(UploadValidationError) as error:
        validate_image(b"#!/bin/sh\necho owned", "image/png", "photo.png")

    assert error.value.code == "invalid_image_signature"


@pytest.mark.parametrize(
    ("size", "accepted"),
    [(MAX_IMAGE_BYTES, True), (MAX_IMAGE_BYTES + 1, False)],
)
def test_enforces_two_mibibyte_boundary(size: int, accepted: bool) -> None:
    payload = PNG + b"x" * (size - len(PNG))

    if accepted:
        assert validate_image(payload, "image/png", "photo.png").size == size
    else:
        with pytest.raises(UploadValidationError) as error:
            validate_image(payload, "image/png", "photo.png")
        assert error.value.code == "image_too_large"


@pytest.mark.parametrize(
    ("payload", "declared_mime", "filename"),
    [
        (JPEG, "image/png", "photo.jpg"),
        (PNG, "image/webp", "photo.png"),
        (WEBP, "image/jpeg", "photo.webp"),
    ],
)
def test_rejects_magic_that_disagrees_with_declared_mime(
    payload: bytes, declared_mime: str, filename: str
) -> None:
    with pytest.raises(UploadValidationError) as error:
        validate_image(payload, declared_mime, filename)

    assert error.value.code == "mime_mismatch"


def test_local_storage_uses_generated_name_and_stays_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "uploads"
    image = validate_image(PNG + b"pixels", "image/png", "../../escape.png")

    stored = LocalImageStorage(root).save(image)

    target = (root / stored.path).resolve()
    assert target.is_relative_to(root.resolve())
    assert "escape" not in stored.path
    assert target.read_bytes() == image.content
    assert stored.mime == "image/png"
    assert stored.size == len(image.content)
    assert stored.path.endswith(".png")
