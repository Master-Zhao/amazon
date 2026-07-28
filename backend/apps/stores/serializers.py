from rest_framework import serializers


class TenantContextSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    tenantType = serializers.CharField()
    membershipRole = serializers.CharField()
    permissionCodes = serializers.ListField(child=serializers.CharField())


class StoreContextSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    externalStoreId = serializers.CharField()


class MarketplaceSerializer(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()
    countryCode = serializers.CharField()
    currency = serializers.CharField()
    timezone = serializers.CharField()


class StoreMarketplaceContextSerializer(serializers.Serializer):
    id = serializers.CharField()
    marketplace = MarketplaceSerializer()


class ProfileContextSerializer(serializers.Serializer):
    id = serializers.CharField()
    externalProfileId = serializers.CharField()
    name = serializers.CharField()
    currency = serializers.CharField()
    timezone = serializers.CharField()
    accessLevel = serializers.CharField()


def list_response_serializer(name, item_serializer):
    result_class = type(
        f"{name}ResultSerializer",
        (serializers.Serializer,),
        {"items": item_serializer(many=True)},
    )
    return type(
        f"{name}ResponseSerializer",
        (serializers.Serializer,),
        {
            "code": serializers.CharField(),
            "message": serializers.CharField(),
            "data": result_class(),
            "requestId": serializers.CharField(),
        },
    )


TenantContextResponseSerializer = list_response_serializer(
    "TenantContext", TenantContextSerializer
)
StoreContextResponseSerializer = list_response_serializer(
    "StoreContext", StoreContextSerializer
)
StoreMarketplaceContextResponseSerializer = list_response_serializer(
    "StoreMarketplaceContext", StoreMarketplaceContextSerializer
)
ProfileContextResponseSerializer = list_response_serializer(
    "ProfileContext", ProfileContextSerializer
)

