from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        max_length=128,
        trim_whitespace=False,
        write_only=True,
    )


class AuthenticatedUserSerializer(serializers.Serializer):
    id = serializers.CharField()
    email = serializers.EmailField()
    username = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()


class LoginResultSerializer(serializers.Serializer):
    accessToken = serializers.CharField()
    user = AuthenticatedUserSerializer()


class AccessTokenResultSerializer(serializers.Serializer):
    accessToken = serializers.CharField()


class EmptyDataSerializer(serializers.Serializer):
    pass


class LoginResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = LoginResultSerializer()
    requestId = serializers.CharField()


class AccessTokenResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = AccessTokenResultSerializer()
    requestId = serializers.CharField()


class CurrentUserResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = AuthenticatedUserSerializer()
    requestId = serializers.CharField()


class EmptyResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = EmptyDataSerializer()
    requestId = serializers.CharField()
