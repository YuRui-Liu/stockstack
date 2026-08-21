import pytest

from app.catalog.field_schema import FieldValidationError, validate_attributes


def test_physical_attributes_are_accepted(physical_schema: dict) -> None:
    assert validate_attributes(
        physical_schema,
        {
            "weight_kg": 1.2,
            "specification": "黑色 / 30L",
            "shipping_template": "standard",
        },
    ) == []


def test_virtual_attributes_are_accepted(virtual_schema: dict) -> None:
    assert validate_attributes(
        virtual_schema,
        {
            "validity_days": 30,
            "verification_method": "qr",
            "redemption_instructions": "到店出示二维码",
        },
    ) == []


def test_creative_attributes_are_accepted(creative_schema: dict) -> None:
    assert validate_attributes(
        creative_schema,
        {
            "asset_type": "image",
            "dimensions": "1920x1080",
            "file_url": "https://cdn.example.com/banner.png",
        },
    ) == []


@pytest.mark.parametrize(
    ("fixture_name", "attributes", "expected_path"),
    [
        ("physical_schema", {"specification": "黑色", "shipping_template": "standard"}, ("weight_kg",)),
        (
            "physical_schema",
            {"weight_kg": "heavy", "specification": "黑色", "shipping_template": "standard"},
            ("weight_kg",),
        ),
        (
            "physical_schema",
            {"weight_kg": -0.1, "specification": "黑色", "shipping_template": "standard"},
            ("weight_kg",),
        ),
        (
            "physical_schema",
            {"weight_kg": 1, "specification": "x" * 101, "shipping_template": "standard"},
            ("specification",),
        ),
        (
            "physical_schema",
            {"weight_kg": 1, "specification": "黑色", "shipping_template": "express"},
            ("shipping_template",),
        ),
        (
            "physical_schema",
            {"weight_kg": 1, "specification": "黑色", "shipping_template": "standard", "color": "black"},
            ("color",),
        ),
        (
            "virtual_schema",
            {"validity_days": 0, "verification_method": "qr", "redemption_instructions": "使用说明"},
            ("validity_days",),
        ),
        (
            "virtual_schema",
            {"validity_days": 1.5, "verification_method": "qr", "redemption_instructions": "使用说明"},
            ("validity_days",),
        ),
        (
            "virtual_schema",
            {"validity_days": 30, "verification_method": "face", "redemption_instructions": "使用说明"},
            ("verification_method",),
        ),
        (
            "virtual_schema",
            {"validity_days": 30, "verification_method": "code", "redemption_instructions": "x" * 501},
            ("redemption_instructions",),
        ),
        (
            "creative_schema",
            {"asset_type": "audio", "dimensions": "100x100", "file_url": "https://example.com/a"},
            ("asset_type",),
        ),
        (
            "creative_schema",
            {"asset_type": "image", "dimensions": "0x100", "file_url": "https://example.com/a"},
            ("dimensions",),
        ),
        (
            "creative_schema",
            {"asset_type": "image", "dimensions": "100x100", "file_url": "not a uri"},
            ("file_url",),
        ),
    ],
)
def test_invalid_attributes_return_field_errors(
    request: pytest.FixtureRequest,
    fixture_name: str,
    attributes: dict,
    expected_path: tuple[str, ...],
) -> None:
    errors = validate_attributes(request.getfixturevalue(fixture_name), attributes)

    assert errors
    assert all(isinstance(error, FieldValidationError) for error in errors)
    assert expected_path in [error.path for error in errors]
    assert all(error.message for error in errors)


def test_all_errors_are_collected_in_stable_field_order(physical_schema: dict) -> None:
    errors = validate_attributes(
        physical_schema,
        {"weight_kg": -1, "specification": "x" * 101, "shipping_template": "invalid"},
    )

    assert [error.path for error in errors] == [
        ("shipping_template",),
        ("specification",),
        ("weight_kg",),
    ]


def test_each_unknown_field_has_its_own_path(physical_schema: dict) -> None:
    errors = validate_attributes(
        physical_schema,
        {
            "weight_kg": 1,
            "specification": "黑色",
            "shipping_template": "standard",
            "color": "black",
            "size": "large",
        },
    )

    assert [error.path for error in errors] == [("color",), ("size",)]


def test_nested_required_error_points_to_missing_field() -> None:
    schema = {
        "type": "object",
        "properties": {
            "shipping": {
                "type": "object",
                "properties": {"carrier": {"type": "string"}},
                "required": ["carrier"],
            }
        },
    }

    errors = validate_attributes(schema, {"shipping": {}})

    assert [error.path for error in errors] == [("shipping", "carrier")]
