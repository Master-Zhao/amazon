from rest_framework import serializers

from apps.reports.models import (
    ImportRowError,
    ImportTask,
    ReportType,
)


class ReportUploadRequestSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=ReportType.choices)
    file = serializers.FileField()


class ReportUploadSummarySerializer(serializers.Serializer):
    id = serializers.CharField()
    report_type = serializers.CharField()
    original_filename = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    sha256 = serializers.CharField()
    duplicate_of_id = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class ImportTaskSerializer(serializers.ModelSerializer):
    upload = ReportUploadSummarySerializer(read_only=True)
    reprocessed_from_id = serializers.CharField(allow_null=True)

    class Meta:
        model = ImportTask
        fields = (
            "id",
            "status",
            "celery_task_id",
            "total_rows",
            "success_rows",
            "error_rows",
            "error_code",
            "error_message",
            "reprocessed_from_id",
            "created_at",
            "started_at",
            "finished_at",
            "upload",
        )


class ImportRowErrorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRowError
        fields = (
            "id",
            "row_number",
            "error_code",
            "message",
            "field_name",
            "rejected_value",
            "created_at",
        )
