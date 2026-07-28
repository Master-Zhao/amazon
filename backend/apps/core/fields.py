from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


@extend_schema_field(OpenApiTypes.STR)
class ObjectIdentifierField(serializers.Field):
    """Serialize an explicitly declared object identifier as a JSON string."""

    def to_representation(self, value) -> str:
        if value is None:
            return None
        return str(value)

    def to_internal_value(self, data) -> str:
        if isinstance(data, bool) or not isinstance(data, (str, int)):
            raise serializers.ValidationError("Object identifier must be a string or integer.")
        value = str(data)
        if not value:
            raise serializers.ValidationError("Object identifier must not be empty.")
        return value


class ObjectIdentifierListField(serializers.ListField):
    child = ObjectIdentifierField()
