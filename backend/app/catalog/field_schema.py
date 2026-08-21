import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import HttpUrl, TypeAdapter, ValidationError

_FORMAT_CHECKER = FormatChecker()
_HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)
_HOST_LABEL = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
)


def _has_valid_host_labels(host: str) -> bool:
    if host.startswith("[") and host.endswith("]"):
        return True
    labels = host.removesuffix(".").split(".")
    return bool(labels) and all(_HOST_LABEL.fullmatch(label) for label in labels)


def _has_empty_port(value: str) -> bool:
    match = re.match(r"^https?://([^/?#]*)", value, flags=re.IGNORECASE)
    if match is None:
        return False
    authority = match.group(1).rsplit("@", 1)[-1]
    if authority.startswith("["):
        closing_bracket = authority.find("]")
        return closing_bracket >= 0 and authority[closing_bracket + 1 :] == ":"
    return authority.endswith(":")


@_FORMAT_CHECKER.checks("http-url")
def _is_http_url(value: object) -> bool:
    """Validate stored asset URLs; the service never fetches them or resolves DNS."""
    if not isinstance(value, str):
        return False
    if any(
        character.isspace() or unicodedata.category(character) == "Cc"
        for character in value
    ):
        return False
    if "\\" in value or re.search(r"%(?![0-9A-Fa-f]{2})", value):
        return False
    if _has_empty_port(value):
        return False
    try:
        parsed = _HTTP_URL_ADAPTER.validate_python(value)
    except ValidationError:
        return False
    return (
        parsed.username is None
        and parsed.password is None
        and _has_valid_host_labels(parsed.host)
    )


@dataclass(frozen=True, slots=True)
class FieldValidationError:
    path: tuple[str | int, ...]
    message: str


def _field_path(error: Any) -> tuple[str | int, ...]:
    return tuple(error.absolute_path)


def _additional_property_errors(error: Any) -> list[FieldValidationError]:
    if not isinstance(error.instance, dict):
        return [FieldValidationError(path=_field_path(error), message=error.message)]

    properties = error.schema.get("properties", {})
    pattern_properties = error.schema.get("patternProperties", {})
    unknown_fields = []
    for field in error.instance:
        explicitly_defined = field in properties
        pattern_defined = any(re.search(pattern, field) for pattern in pattern_properties)
        if not explicitly_defined and not pattern_defined:
            unknown_fields.append(field)

    if not unknown_fields:
        return [FieldValidationError(path=_field_path(error), message=error.message)]
    return [
        FieldValidationError(
            path=(*error.absolute_path, field),
            message=f"additional property {field!r} is not allowed",
        )
        for field in unknown_fields
    ]


def validate_attributes(
    schema: dict[str, Any], attributes: dict[str, Any]
) -> list[FieldValidationError]:
    """Validate untrusted attributes and return every error in stable field order."""
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    errors: list[FieldValidationError] = []
    seen_required: set[tuple[tuple[str | int, ...], str]] = set()
    for error in validator.iter_errors(attributes):
        if error.validator == "additionalProperties":
            errors.extend(_additional_property_errors(error))
            continue
        if error.validator == "required" and isinstance(error.instance, dict):
            for field in error.validator_value:
                if field in error.instance:
                    continue
                path = (*error.absolute_path, field)
                marker = (tuple(error.absolute_path), field)
                if marker not in seen_required:
                    seen_required.add(marker)
                    errors.append(
                        FieldValidationError(
                            path=path,
                            message=f"required property {field!r} is missing",
                        )
                    )
            continue
        errors.append(
            FieldValidationError(path=_field_path(error), message=error.message)
        )
    return sorted(errors, key=lambda error: (tuple(map(str, error.path)), error.message))
