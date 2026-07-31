from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        required=False,
        max_length=254,
        trim_whitespace=True,
        help_text="推荐字段；可填写用户名、账号编号或邮箱。",
    )
    email = serializers.EmailField(
        required=False,
        max_length=254,
        write_only=True,
        help_text="向后兼容字段；新客户端应使用 identifier。",
    )
    password = serializers.CharField(
        max_length=128,
        trim_whitespace=False,
        write_only=True,
    )

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown_fields = set(data.keys()) - {
                "identifier",
                "email",
                "password",
            }
            if unknown_fields:
                raise serializers.ValidationError(
                    {
                        field: ["不支持的字段。"]
                        for field in sorted(unknown_fields)
                    }
                )
        return super().to_internal_value(data)

    def validate(self, attrs):
        has_identifier = "identifier" in attrs
        has_email = "email" in attrs
        if has_identifier and has_email:
            raise serializers.ValidationError(
                {
                    "identifier": ["不能与 email 同时提供。"],
                    "email": ["不能与 identifier 同时提供。"],
                }
            )
        if not has_identifier and not has_email:
            raise serializers.ValidationError(
                {"identifier": ["请输入账号或邮箱。"]}
            )

        identifier = attrs.pop("email") if has_email else attrs["identifier"]
        attrs["identifier"] = identifier.strip()
        return attrs


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
