def test_celery_smoke_task_is_deterministic():
    from apps.core.tasks import smoke_task

    result = smoke_task.apply(args=["req_test_smoke"]).get()

    assert result["status"] == "ok"
    assert result["request_id"] == "req_test_smoke"
    assert isinstance(result["task_id"], str)
