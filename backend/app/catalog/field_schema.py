import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("http-url")
def _is_http_url(value: object) -> bool:
    if not isinstance(value, str) or any(character.isspace() for character in value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username is not None or parsed.password is not None:
            return False
        if parsed.netloc.endswith(":"):
            return False
        _ = parsed.port
    except ValueError:
        return False
    return True


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
