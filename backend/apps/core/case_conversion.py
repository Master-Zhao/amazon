import re
from collections.abc import Mapping
from typing import Any

_FIRST_CAP_RE = re.compile(r"(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile(r"([a-z0-9])([A-Z])")
_SNAKE_TO_CAMEL_RE = re.compile(r"_([a-zA-Z0-9])")


def to_camel_key(value: str) -> str:
    return _SNAKE_TO_CAMEL_RE.sub(lambda match: match.group(1).upper(), value)


def to_snake_key(value: str) -> str:
    first_pass = _FIRST_CAP_RE.sub(r"\1_\2", value)
    return _ALL_CAP_RE.sub(r"\1_\2", first_pass).replace("-", "_").lower()


def convert_keys(value: Any, converter) -> Any:
    if isinstance(value, Mapping):
        return {
            converter(str(key)): convert_keys(item, converter)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [convert_keys(item, converter) for item in value]
    if isinstance(value, tuple):
        return [convert_keys(item, converter) for item in value]
    return value


def to_camel_case(value: Any) -> Any:
    return convert_keys(value, to_camel_key)


def to_snake_case(value: Any) -> Any:
    return convert_keys(value, to_snake_key)
