from rest_framework import serializers

from apps.accounts.serializers import AuthenticatedUserSerializer


class TenantOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    tenantType = serializers.CharField()
    membershipRole = serializers.CharField()


class StoreOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    externalStoreId = serializers.CharField()


class MarketplaceSerializer(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()
    currencyCode = serializers.CharField()
    timezone = serializers.CharField()


class StoreMarketplaceOptionSerializer(serializers.Serializer):
    storeMarketplaceId = serializers.CharField()
    marketplace = MarketplaceSerializer()


class ProfileOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    externalProfileId = serializers.CharField()
    currencyCode = serializers.CharField()
    timezone = serializers.CharField()
    accessLevel = serializers.CharField()


class ContextCapabilitiesSerializer(serializers.Serializer):
    permissionCodes = serializers.ListField(child=serializers.CharField())
    membershipRole = serializers.CharField()


class CurrentContextSerializer(serializers.Serializer):
    user = AuthenticatedUserSerializer()
    tenants = TenantOptionSerializer(many=True)
