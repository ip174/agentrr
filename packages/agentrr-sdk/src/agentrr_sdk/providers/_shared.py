"""Shared provider helpers."""

from __future__ import annotations

from typing import Any


def normalize_messages(messages: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if hasattr(m, "model_dump"):
            out.append(m.model_dump(mode="json"))
        elif isinstance(m, dict):
            out.append(m)
        else:
            out.append({"role": getattr(m, "role", "user"), "content": str(m)})
    return out


def llm_request_dict(
    model: str,
    messages: Any,
    **params: Any,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": normalize_messages(messages),
        "params": {k: v for k, v in params.items() if v is not None},
    }


def llm_response_dict(content: str, finish_reason: str = "stop", tool_calls: Any = None) -> dict[str, Any]:
    return {
        "content": content,
        "finish_reason": finish_reason,
        "tool_calls": tool_calls or [],
    }
