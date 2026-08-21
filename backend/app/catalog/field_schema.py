import re
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("uri")
def _is_uri(value: object) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"[A-Za-z][A-Za-z0-9+.-]*:\S+", value)
    )


@dataclass(frozen=True, slots=True)
class FieldValidationError:
    path: tuple[str | int, ...]
    message: str


def _field_path(error: Any) -> tuple[str | int, ...]:
    path = tuple(error.absolute_path)
    if error.validator == "required":
        missing = error.message.split("'", 2)[1]
        return (*path, missing)

    if error.validator == "additionalProperties":
        unexpected = error.message.split("'", 2)[1]
        return (*path, unexpected)

    return path


def validate_attributes(
    schema: dict[str, Any], attributes: dict[str, Any]
) -> list[FieldValidationError]:
    """Validate untrusted attributes and return every error in stable field order."""
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    errors: list[FieldValidationError] = []
    for error in validator.iter_errors(attributes):
        if error.validator == "additionalProperties":
            known_fields = error.schema.get("properties", {})
            for field in error.instance.keys() - known_fields.keys():
                errors.append(
                    FieldValidationError(
                        path=(*error.absolute_path, field),
                        message=f"additional property {field!r} is not allowed",
                    )
                )
            continue
        errors.append(
            FieldValidationError(path=_field_path(error), message=error.message)
        )
    return sorted(errors, key=lambda error: (tuple(map(str, error.path)), error.message))
