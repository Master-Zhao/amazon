from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class ExecutionAdapterRequest:
    tenant_id: str
    profile_id: str
    action_type: str
    object_id: str
    before_value: Mapping[str, object]
    after_value: Mapping[str, object]
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class ExecutionAdapterResult:
    status: str
    external_operation_id: str = ""
    evidence: Mapping[str, object] | None = None


class ExecutionAdapterError(RuntimeError):
    retryable = False


class ExecutionAdapterUnavailable(ExecutionAdapterError):
    pass


class ExecutionAdapterTimeout(ExecutionAdapterError):
    retryable = True


class AmazonAdsExecutionAdapter(Protocol):
    timeout_seconds: int
    max_retries: int

    def execute(self, request: ExecutionAdapterRequest) -> ExecutionAdapterResult: ...


class ManualExecutionAdapter:
    """V1 adapter: preserve scope and idempotency while requiring a human action."""

    timeout_seconds = 0
    max_retries = 0

    def execute(self, request: ExecutionAdapterRequest) -> ExecutionAdapterResult:
        return ExecutionAdapterResult(
            status="REQUIRES_MANUAL",
            evidence={
                "tenantId": request.tenant_id,
                "profileId": request.profile_id,
                "idempotencyKey": request.idempotency_key,
            },
        )


class ReservedAmazonAdsExecutionAdapter:
    capability = {"available": False, "mode": "reserved", "code": "AMAZON_ADS_EXECUTION"}
    timeout_seconds = 30
    max_retries = 0

    def execute(self, request: ExecutionAdapterRequest) -> ExecutionAdapterResult:
        raise ExecutionAdapterUnavailable(
            "Real Amazon Ads execution is prohibited in V1"
        )
