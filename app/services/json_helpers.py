import json
from typing import Any


def dumps_list(items: list[str] | None) -> str:
    return json.dumps([item.strip() for item in items or [] if item and item.strip()])


def loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed if str(item).strip()] if isinstance(parsed, list) else []


def dumps_dict(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, default=str, sort_keys=True)
