from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from apps.core.case_conversion import to_camel_case, to_snake_case
from apps.core.parsers import CamelCaseJSONParser
from apps.core.renderers import CamelCaseJSONRenderer


def test_nested_objects_arrays_and_pagination_convert_to_camel_case():
    source = {
        "items": [
            {
                "object_id": "42",
                "before_value": {"daily_budget": Decimal("10.00")},
            }
        ],
        "pagination": {
            "page_size": 20,
            "total_pages": 2,
        },
        "field_errors": {"nested_field": ["invalid"]},
    }

    converted = to_camel_case(source)

    assert converted["items"][0]["objectId"] == "42"
    assert converted["items"][0]["beforeValue"]["dailyBudget"] == Decimal("10.00")
    assert converted["pagination"] == {"pageSize": 20, "totalPages": 2}
    assert converted["fieldErrors"] == {"nestedField": ["invalid"]}


def test_nested_objects_and_arrays_convert_to_snake_case():
    source = {
        "actionType": "UPDATE",
        "afterValue": {"dailyBudget": "12.00"},
        "evidenceItems": [{"sourceId": "7"}],
    }

    assert to_snake_case(source) == {
        "action_type": "UPDATE",
        "after_value": {"daily_budget": "12.00"},
        "evidence_items": [{"source_id": "7"}],
    }


def test_json_parser_converts_request_keys_to_snake_case():
    stream = BytesIO(
        b'{"outerObject":{"childItems":[{"objectId":"9"}]},"pageSize":20}'
    )

    parsed = CamelCaseJSONParser().parse(stream)

    assert parsed == {
        "outer_object": {"child_items": [{"object_id": "9"}]},
        "page_size": 20,
    }


def test_renderer_serializes_decimal_dates_and_ids_safely():
    rendered = CamelCaseJSONRenderer().render(
        {
            "amount_value": Decimal("100.00"),
            "business_date": date(2026, 7, 28),
            "created_at": datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
            "object_id": UUID("00000000-0000-0000-0000-000000000001"),
        }
    )
    text = rendered.decode()

    assert '"amountValue":"100.00"' in text
    assert '"businessDate":"2026-07-28"' in text
    assert '"createdAt":"2026-07-28T12:00:00Z"' in text
    assert '"objectId":"00000000-0000-0000-0000-000000000001"' in text
