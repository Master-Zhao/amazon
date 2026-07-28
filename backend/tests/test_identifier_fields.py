import json
from decimal import Decimal
from uuid import UUID

import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.core.fields import ObjectIdentifierField, ObjectIdentifierListField
from apps.core.renderers import CamelCaseJSONRenderer


class NestedReferenceSerializer(serializers.Serializer):
    id = ObjectIdentifierField()


class IdentifierContractSerializer(serializers.Serializer):
    id = ObjectIdentifierField()
    user_id = ObjectIdentifierField()
    nested = NestedReferenceSerializer()
    related_ids = ObjectIdentifierListField()
    clicks = serializers.IntegerField()
    orders = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    total = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    correlation_id = serializers.UUIDField()


@pytest.mark.django_db
def test_declared_object_identifiers_are_strings_while_metrics_remain_numbers():
    user = get_user_model().objects.create_user(
        username="identifier-contract-user",
        email="identifier-contract@example.invalid",
        password="test-only-password",
    )
    assert isinstance(user.pk, int)

    serializer = IdentifierContractSerializer(
        {
            "id": user.pk,
            "user_id": user.pk,
            "nested": {"id": user.pk},
            "related_ids": [user.pk, user.pk + 1],
            "clicks": 11,
            "orders": 2,
            "page": 1,
            "page_size": 20,
            "total": 41,
            "amount": Decimal("100.00"),
            "correlation_id": UUID("00000000-0000-0000-0000-000000000001"),
        }
    )

    payload = json.loads(CamelCaseJSONRenderer().render(serializer.data))

    assert payload["id"] == str(user.pk)
    assert payload["userId"] == str(user.pk)
    assert payload["nested"]["id"] == str(user.pk)
    assert payload["relatedIds"] == [str(user.pk), str(user.pk + 1)]
    assert payload["clicks"] == 11
    assert payload["orders"] == 2
    assert payload["page"] == 1
    assert payload["pageSize"] == 20
    assert payload["total"] == 41
    assert payload["amount"] == "100.00"
    assert payload["correlationId"] == "00000000-0000-0000-0000-000000000001"
