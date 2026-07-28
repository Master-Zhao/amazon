from rest_framework import serializers


class PermissionOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    code = serializers.CharField()
    name = serializers.CharField()


class RoleOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField()
    isSystem = serializers.BooleanField()
    permissionCodes = serializers.ListField(child=serializers.CharField())


class CreateRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    code = serializers.RegexField(r"^[a-z][a-z0-9_.-]{2,95}$")
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=96),
        allow_empty=True,
    )


class CopyRoleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    code = serializers.RegexField(r"^[a-z][a-z0-9_.-]{2,95}$")


class StoreAccessGrantSerializer(serializers.Serializer):
    store_id = serializers.CharField()
    user_id = serializers.CharField(required=False, allow_null=True)
    team_id = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        if bool(attrs.get("user_id")) == bool(attrs.get("team_id")):
            raise serializers.ValidationError(
                "userId 与 teamId 必须且只能提供一个"
            )
        return attrs


class ProfileAccessGrantSerializer(serializers.Serializer):
    profile_id = serializers.CharField()
    access_level = serializers.ChoiceField(
        choices=["VIEW", "OPERATE", "APPROVE", "EXECUTE", "MANAGE"]
    )
    user_id = serializers.CharField(required=False, allow_null=True)
    team_id = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        if bool(attrs.get("user_id")) == bool(attrs.get("team_id")):
            raise serializers.ValidationError(
                "userId 与 teamId 必须且只能提供一个"
            )
        return attrs
