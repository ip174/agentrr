"""Multi-step LLM → tool → LLM (mocked OpenAI)."""

from __future__ import annotations

from agentrr_sdk import step
from agents.deterministic_support import _mock_client, get_order


def main() -> str:
    client = _mock_client()
    with step("tool_phase"):
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "get order 123"}],
        )
        get_order("123")
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "final answer"}],
        )
    return "done"


if __name__ == "__main__":
    main()
