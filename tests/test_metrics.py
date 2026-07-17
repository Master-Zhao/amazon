"""Five deterministic metric calculations and unknown handling."""

from decimal import Decimal

from amazon_ads_agent.metrics import calculate_metrics


def test_acos_is_exact(high_task: dict) -> None:
    assert calculate_metrics(high_task["entity_metrics"][0]).acos == Decimal("0.35")


def test_roas_is_exact(high_task: dict) -> None:
    result = calculate_metrics(high_task["entity_metrics"][0])
    assert result.roas == Decimal("900.00") / Decimal("315.00")


def test_ctr_cpc_and_cvr_are_exact(high_task: dict) -> None:
    result = calculate_metrics(high_task["entity_metrics"][0])
    assert result.ctr == Decimal("420") / Decimal("25000")
    assert result.cpc == Decimal("315.00") / Decimal("420")
    assert result.cvr == Decimal("30") / Decimal("420")


def test_zero_denominators_are_unknown_with_reasons(high_task: dict) -> None:
    entity = high_task["entity_metrics"][0]
    entity.update({"impressions": 0, "clicks": 0, "orders": 0, "spend": "0.00", "sales": "0.00"})
    result = calculate_metrics(entity)
    assert result.ctr is result.cpc is result.cvr is result.acos is result.roas is None
    assert all(reason is not None for reason in result.reason_codes.values())


def test_unknown_metric_is_not_replaced_by_zero(high_task: dict) -> None:
    high_task["entity_metrics"][0]["sales"] = "0.00"
    assert calculate_metrics(high_task["entity_metrics"][0]).acos is None
