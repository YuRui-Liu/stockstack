from enum import StrEnum


class ProductType(StrEnum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    CREATIVE = "creative"


class ProductStatus(StrEnum):
    ON_SHELF = "on_shelf"
    OFF_SHELF = "off_shelf"
    PENALIZED = "penalized"


class DeliveryMethod(StrEnum):
    EMS = "ems"
    LOGISTICS = "logistics"
    VOUCHER = "voucher"


class ReturnRule(StrEnum):
    SEVEN_DAYS = "seven_days"
    NO_RETURNS = "no_returns"


class IllegalProductStatusTransition(ValueError):
    """Raised when a product status transition violates domain rules."""


_ALLOWED_TRANSITIONS = {
    ProductStatus.ON_SHELF: {ProductStatus.OFF_SHELF, ProductStatus.PENALIZED},
    ProductStatus.OFF_SHELF: {ProductStatus.ON_SHELF, ProductStatus.PENALIZED},
    ProductStatus.PENALIZED: set(),
}


def assert_transition(source: ProductStatus, target: ProductStatus) -> None:
    if target not in _ALLOWED_TRANSITIONS[source]:
        raise IllegalProductStatusTransition(
            f"illegal product status transition: {source.value} -> {target.value}"
        )
