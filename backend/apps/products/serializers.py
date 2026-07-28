from rest_framework import serializers


class ProductListingInputSerializer(serializers.Serializer):
    store_marketplace_id = serializers.CharField()
    seller_sku = serializers.CharField(max_length=128)
    asin = serializers.CharField(
        max_length=32,
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    catalog_title = serializers.CharField(
        max_length=500,
        allow_blank=True,
        required=False,
        default="",
    )


class ProductCreateSerializer(ProductListingInputSerializer):
    name = serializers.CharField(max_length=255)


class ProductListingRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    store_marketplace_id = serializers.CharField()
    store_name = serializers.CharField()
    marketplace_code = serializers.CharField()
    seller_sku = serializers.CharField()
    asin = serializers.CharField(allow_null=True)
    catalog_title = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()


class ProductRowSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    listings = ProductListingRowSerializer(many=True)
