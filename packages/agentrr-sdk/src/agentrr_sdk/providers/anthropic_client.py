"""Anthropic client wrapper — concrete first."""

from __future__ import annotations

import uuid
from functools import wraps
from typing import Any

from agentrr_core.schema.events import ErrorPayload
from agentrr_sdk import runtime
from agentrr_sdk.boundaries.llm import record_llm_result
from agentrr_sdk.providers._shared import (
    llm_request_dict,
    llm_response_dict,
)
from anthropic import Anthropic


def wrap_anthropic_client(client: Anthropic) -> Anthropic:
    original = client.messages.create

    @wraps(original)
    def create(*args: Any, **kwargs: Any) -> Any:
        mode = runtime.get_mode()
        model = kwargs.get("model") or "unknown"
        messages = kwargs.get("messages", [])
        max_tokens = kwargs.get("max_tokens", 1024)
        req = llm_request_dict(
            model,
            messages,
            max_tokens=max_tokens,
            **{k: v for k, v in kwargs.items() if k not in ("messages", "model", "max_tokens")},
        )

        if mode == "replay":
            engine = runtime.get_engine()
            if engine is None:
                raise RuntimeError("replay without engine")
            payload = engine.serve_llm(req)
            return _mock_anthropic_message(model, payload)

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
            content = ""
            tool_calls: list[dict[str, Any]] = []
            for block in result.content:
                if hasattr(block, "text"):
                    content += block.text
                elif getattr(block, "type", None) == "tool_use":
                    tool_calls.append(
                        {
                            "name": block.name,
                            "arguments": block.input,
                        }
                    )
            resp = llm_response_dict(
                content,
                finish_reason=getattr(result, "stop_reason", "end_turn") or "stop",
                tool_calls=tool_calls,
            )
            meta = {"provider_request_id": getattr(result, "id", None), "retry_count": 0}
            record_llm_result(event_id, req, resp, meta=meta)
        return result

    client.messages.create = create  # type: ignore[method-assign]
    return client


def _mock_anthropic_message(model: str, payload: dict[str, Any]) -> Any:
    from anthropic.types import Message

    content: list[dict[str, Any]] = [{"type": "text", "text": payload.get("content", "")}]
    return Message.model_validate(
        {
            "id": "replay",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": payload.get("finish_reason", "end_turn"),
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
    )
