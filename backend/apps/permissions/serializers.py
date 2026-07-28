from rest_framework import serializers


class RoleCreateSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    code = serializers.RegexField(r"^[a-z][a-z0-9_.-]{1,62}$")
    name = serializers.CharField(max_length=128)
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=64), allow_empty=True
    )


class RoleAssignmentSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    user_id = serializers.IntegerField()


class UserStoreGrantSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    user_id = serializers.IntegerField()


class UserProfileGrantSerializer(UserStoreGrantSerializer):
    level = serializers.ChoiceField(
        choices=["VIEW", "OPERATE", "APPROVE", "EXECUTE", "MANAGE"]
    )


class PermissionSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()


class RoleSerializer(serializers.Serializer):
    id = serializers.CharField()
    tenantId = serializers.CharField(allow_null=True)
    code = serializers.CharField()
    name = serializers.CharField()
    isSystem = serializers.BooleanField()
    permissionCodes = serializers.ListField(child=serializers.CharField())


class PermissionListDataSerializer(serializers.Serializer):
    items = PermissionSerializer(many=True)


class RoleListDataSerializer(serializers.Serializer):
    items = RoleSerializer(many=True)


class AssignmentDataSerializer(serializers.Serializer):
    id = serializers.CharField()


class PermissionListResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = PermissionListDataSerializer()
    requestId = serializers.CharField()


class RoleListResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = RoleListDataSerializer()
    requestId = serializers.CharField()


class RoleResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = RoleSerializer()
    requestId = serializers.CharField()


class AssignmentResponseSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    data = AssignmentDataSerializer()
    requestId = serializers.CharField()
