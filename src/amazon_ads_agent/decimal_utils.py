"""Strict Decimal parsing, formatting, rounding, and range helpers."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

DECIMAL_PATTERN = re.compile(r"^-?(0|[1-9][0-9]*)(\.[0-9]+)?$")


class DecimalValueError(ValueError):
    """Raised when a business value is not a canonical Decimal string."""


def parse_decimal(value: str) -> Decimal:
    """Parse a canonical Decimal string while rejecting numbers and floats."""

    if not isinstance(value, str) or not DECIMAL_PATTERN.fullmatch(value):
        raise DecimalValueError("business Decimal values must be canonical strings")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DecimalValueError(f"invalid Decimal string: {value!r}") from exc
    if not parsed.is_finite():
        raise DecimalValueError("business Decimal values must be finite")
    return parsed


def decimal_to_string(value: Decimal, places: int | None = None) -> str:
    """Serialize a finite Decimal without exponent notation."""

    if not isinstance(value, Decimal) or not value.is_finite():
        raise DecimalValueError("expected a finite Decimal")
    if places is not None:
        quantum = Decimal(1).scaleb(-places)
        value = value.quantize(quantum, rounding=ROUND_HALF_UP)
        return f"{value:.{places}f}"
    return format(value, "f")


def safe_divide(numerator: Decimal, denominator: Decimal, reason_code: str) -> tuple[Decimal | None, str | None]:
    """Divide Decimal values or return an explicit reason for an unknown value."""

    if denominator == Decimal("0"):
        return None, reason_code
    return numerator / denominator, None


def round_to_step(value: Decimal, step: Decimal) -> Decimal:
    """Round a Decimal to a positive step with ROUND_HALF_UP."""

    if step <= Decimal("0"):
        raise DecimalValueError("step must be greater than zero")
    units = (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (units * step).quantize(step, rounding=ROUND_HALF_UP)


def step_decimal_places(step: Decimal) -> int:
    """Return the fixed decimal scale represented by a step."""

    return max(0, -step.as_tuple().exponent)


def percentage_change(current: Decimal, suggested: Decimal) -> Decimal:
    """Calculate `(suggested-current)/current` exactly."""

    if current == Decimal("0"):
        raise DecimalValueError("percentage change is undefined for a zero current value")
    return (suggested - current) / current


def validate_range(value: Decimal, minimum: Decimal, maximum: Decimal) -> None:
    """Raise if a Decimal is outside an inclusive configured range."""

    if minimum > maximum:
        raise DecimalValueError("invalid configured range")
    if value < minimum or value > maximum:
        raise DecimalValueError(f"value {value} is outside [{minimum}, {maximum}]")
