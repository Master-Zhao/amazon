from django.core.serializers.json import DjangoJSONEncoder


class SafeJSONEncoder(DjangoJSONEncoder):
    """DjangoJSONEncoder already emits Decimal, UUID, dates, and times as strings."""
