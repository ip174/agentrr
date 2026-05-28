"""Golden-path agent: shims + mocked LLM + registered tools."""

from __future__ import annotations

from agentrr_sdk import record, register_tool, step
from agentrr_sdk.providers.openai_client import wrap_openai_client
from agentrr_sdk.shims import clock, ids, rng
from openai import OpenAI

_TOOL_EXECUTIONS = 0


@register_tool
def get_order(order_id: str) -> dict[str, object]:
    global _TOOL_EXECUTIONS
    _TOOL_EXECUTIONS += 1
    return {"order_id": order_id, "total": 49.99, "status": "shipped"}


def _mock_client() -> OpenAI:
    class FakeCompletions:
        def create(self, model: str, messages: list[dict[str, str]], **kwargs: object) -> object:
            from openai.types.chat import ChatCompletion

            user = messages[-1]["content"]
            if "tool" in user.lower() or "order" in user.lower():
                return ChatCompletion.model_validate(
                    {
                        "id": "fake",
                        "object": "chat.completion",
                        "created": 0,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "done",
                                    "tool_calls": [
                                        {
                                            "id": "c1",
                                            "type": "function",
                                            "function": {
                                                "name": "get_order",
                                                "arguments": '{"order_id": "123"}',
                                            },
                                        }
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                    }
                )
            return ChatCompletion.model_validate(
                {
                    "id": "fake",
                    "object": "chat.completion",
                    "created": 0,
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "Your order is shipped."},
                            "finish_reason": "stop",
                        }
                    ],
                }
            )

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    return wrap_openai_client(FakeClient())  # type: ignore[arg-type]


def main() -> str:
    _ = clock.time()
    _ = rng.random()
    ticket = ids.uuid4()
    client = _mock_client()
    with step("reasoning_step_1"):
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Look up order 123 ticket={ticket}"}],
        )
        get_order("123")
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Summarize for customer"}],
        )
    return "ok"


if __name__ == "__main__":
    from agentrr_sdk import record

    _, log_path = record("deterministic_support", main)
    print(f"run_id: {log_path.stem}")
    print(f"log: {log_path}")
