"""OpenAI client wrapper — concrete first."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from agentrr_core.schema.events import ErrorPayload
from agentrr_sdk import runtime
from agentrr_sdk.boundaries.llm import record_llm_result
from agentrr_sdk.providers._shared import (
    llm_request_dict,
    llm_response_dict,
)
from openai import OpenAI

F = TypeVar("F", bound=Callable[..., Any])


def wrap_openai_client(client: OpenAI) -> OpenAI:
    original = client.chat.completions.create

    @wraps(original)
    def create(*args: Any, **kwargs: Any) -> Any:
        mode = runtime.get_mode()
        model = kwargs.get("model") or (args[0] if args else "unknown")
        messages = kwargs.get("messages", [])
        req = llm_request_dict(model, messages, **{k: v for k, v in kwargs.items() if k not in ("messages", "model")})

        if mode == "replay":
            engine = runtime.get_engine()
            if engine is None:
                raise RuntimeError("replay without engine")
            payload = engine.serve_llm(req)
            return _mock_openai_completion(client, model, payload)

        event_id = f"e-{uuid.uuid4().hex[:12]}"
        try:
            result = original(*args, **kwargs)
        except Exception as exc:
            if mode == "record":
                record_llm_result(
                    event_id,
                    req,
                    None,
                    error=ErrorPayload(type=type(exc).__name__, message=str(exc)),
                )
            raise

        if mode == "record":
            tool_calls = []
            msg = result.choices[0].message
            if msg.tool_calls:
                tool_calls = [
                    {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in msg.tool_calls
                ]
            resp = llm_response_dict(
                msg.content or "",
                finish_reason=result.choices[0].finish_reason or "stop",
                tool_calls=tool_calls,
            )
            meta = {
                "provider_request_id": getattr(result, "id", None),
                "retry_count": 0,
                "chunk_count": 0,
            }
            record_llm_result(event_id, req, resp, meta=meta)
        return result

    client.chat.completions.create = create  # type: ignore[method-assign]
    return client


def _mock_openai_completion(client: OpenAI, model: str, payload: dict[str, Any]) -> Any:
    """Reconstruct ChatCompletion-like object from stored dict."""
    from openai.types.chat import ChatCompletion

    return ChatCompletion.model_validate(
        {
            "id": "replay",
            "object": "chat.completion",
            "created": 0,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": payload.get("content", ""),
                        "tool_calls": _tool_calls_to_openai(payload.get("tool_calls", [])),
                    },
                    "finish_reason": payload.get("finish_reason", "stop"),
                }
            ],
        }
    )


def _tool_calls_to_openai(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    if not tool_calls:
        return None
    out = []
    for i, tc in enumerate(tool_calls):
        out.append(
            {
                "id": f"call_{i}",
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc.get("arguments", "{}")},
            }
        )
    return out
