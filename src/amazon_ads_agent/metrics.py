"""Deterministic Amazon Ads metric calculations."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from .decimal_utils import parse_decimal, safe_divide
from .models import MetricsResult


def calculate_metrics(entity: dict[str, Any]) -> MetricsResult:
    """Calculate CTR, CPC, CVR, ACoS, and ROAS without binary floats."""

    impressions = Decimal(entity["impressions"])
    clicks = Decimal(entity["clicks"])
    orders = Decimal(entity["orders"])
    spend = parse_decimal(entity["spend"])
    sales = parse_decimal(entity["sales"])

    ctr, ctr_reason = safe_divide(clicks, impressions, "DENOMINATOR_ZERO_IMPRESSIONS")
    cpc, cpc_reason = safe_divide(spend, clicks, "DENOMINATOR_ZERO_CLICKS")
    cvr, cvr_reason = safe_divide(orders, clicks, "DENOMINATOR_ZERO_CLICKS")
    acos, acos_reason = safe_divide(spend, sales, "DENOMINATOR_ZERO_SALES")
    roas, roas_reason = safe_divide(sales, spend, "DENOMINATOR_ZERO_SPEND")

    return MetricsResult(
        ctr=ctr,
        cpc=cpc,
        cvr=cvr,
        acos=acos,
        roas=roas,
        reason_codes={
            "ctr": ctr_reason,
            "cpc": cpc_reason,
            "cvr": cvr_reason,
            "acos": acos_reason,
            "roas": roas_reason,
        },
    )
