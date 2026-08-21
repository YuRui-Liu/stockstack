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


def test_local_storage_rejects_symlink_root(tmp_path: Path) -> None:
    actual_root = tmp_path / "actual"
    actual_root.mkdir()
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(actual_root, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic link"):
        LocalImageStorage(linked_root)


def test_local_storage_removes_partial_file_when_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "uploads"
    image = validate_image(PNG + b"pixels", "image/png", "photo.png")
    original_open = Path.open

    class FailingWriter:
        def __init__(self, destination):
            self.destination = destination

        def __enter__(self):
            self.destination.__enter__()
            return self

        def __exit__(self, *args):
            return self.destination.__exit__(*args)

        def write(self, content: bytes) -> None:
            self.destination.write(content[:1])
            raise OSError("disk write failed")

    def failing_open(path: Path, *args, **kwargs):
        return FailingWriter(original_open(path, *args, **kwargs))

    monkeypatch.setattr(Path, "open", failing_open)

    with pytest.raises(OSError, match="disk write failed"):
        LocalImageStorage(root).save(image)

    assert list(root.iterdir()) == []
