"""Exact Decimal utility behavior."""

from decimal import Decimal

import pytest

from amazon_ads_agent.decimal_utils import (
    DecimalValueError,
    decimal_to_string,
    parse_decimal,
    percentage_change,
    round_to_step,
    safe_divide,
    validate_range,
)


def test_decimal_string_parses_exactly() -> None:
    assert parse_decimal("315.00") == Decimal("315.00")


def test_float_input_is_rejected() -> None:
    with pytest.raises(DecimalValueError):
        parse_decimal(1.2)  # type: ignore[arg-type]


def test_round_half_up_to_step() -> None:
    assert round_to_step(Decimal("1.235"), Decimal("0.01")) == Decimal("1.24")


def test_percentage_change_is_exact() -> None:
    assert percentage_change(Decimal("1.20"), Decimal("1.08")) == Decimal("-0.1")


def test_safe_divide_returns_none_and_reason() -> None:
    assert safe_divide(Decimal("1"), Decimal("0"), "ZERO") == (None, "ZERO")


def test_fixed_decimal_serialization() -> None:
    assert decimal_to_string(Decimal("0.35"), places=6) == "0.350000"


def test_range_validation_rejects_outside_value() -> None:
    with pytest.raises(DecimalValueError):
        validate_range(Decimal("6"), Decimal("0.02"), Decimal("5.00"))
