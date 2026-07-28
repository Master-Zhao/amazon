from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="system")


def set_request_id(request_id: str):
    return _request_id.set(request_id)


def reset_request_id(token) -> None:
    _request_id.reset(token)


def current_request_id() -> str:
    return _request_id.get()
