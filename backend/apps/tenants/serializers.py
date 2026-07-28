from rest_framework import serializers


class MembershipOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    userId = serializers.CharField()
    email = serializers.EmailField()
    membershipRole = serializers.CharField()
    isActive = serializers.BooleanField()


class TeamOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    memberIds = serializers.ListField(child=serializers.CharField())


class CreateTeamSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)


class AddTeamMemberSerializer(serializers.Serializer):
    membership_id = serializers.CharField()


class AssignRoleSerializer(serializers.Serializer):
    membership_id = serializers.CharField()
    role_id = serializers.CharField()
