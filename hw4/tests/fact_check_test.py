"""Proves the fact-check output validator catches wrong prices/stock and forces a correction (Problem 9).

Uses a scripted stand-in for the AI model (PydanticAI's FunctionModel), so the test can make the
"model" state a wrong price on purpose. No API key or server needed. From the HOME WORK 4 folder:
    ../.venv/Scripts/python.exe tests/fact_check_test.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from pydantic_ai.exceptions import UnexpectedModelBehavior  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart  # noqa: E402
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

from agent import build_agent  # noqa: E402
from tools import AgentDeps, fact_check_reply  # noqa: E402

WRONG = "The Basic Hoodie Big Yale is $58.00, and there are 9 left in M."  # real: $68.00, 5 in M
RIGHT = "The Basic Hoodie Big Yale is $68.00, and there are 5 left in M."
feedback_seen: list[str] = []


def answer(text: str) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("final_result", {"reply": text, "product_ids": ["basic-hoodie-big-yale"]})])


def wrong_then_right(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    retries = [p for m in messages for p in getattr(m, "parts", []) if isinstance(p, RetryPromptPart)]
    if retries:
        feedback_seen.append(str(retries[-1].content))
        return answer(RIGHT)
    return answer(WRONG)


def always_wrong(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return answer(WRONG)


async def main() -> int:
    results = []

    checked, problems = fact_check_reply(WRONG, [], set())
    results.append(("Checker finds both mistakes in the wrong reply", len(problems) == 2))
    print("problems found:", problems)

    deps = AgentDeps()
    result = await build_agent(FunctionModel(wrong_then_right)).run("How much is the Basic Hoodie Big Yale?", deps=deps)
    print("final reply:", result.output.reply)
    print("feedback the model got:", feedback_seen[0] if feedback_seen else "(none)")
    results.append(("Wrong reply was sent back to the model", deps.fact_corrections == 1))
    results.append(("Shopper only sees the corrected reply", result.output.reply == RIGHT))
    results.append(("Corrected reply's facts were verified", deps.facts_checked == 2))

    try:
        await build_agent(FunctionModel(always_wrong)).run("How much is it?", deps=AgentDeps())
        results.append(("A reply that stays wrong is never shown", False))
    except UnexpectedModelBehavior:
        results.append(("A reply that stays wrong is never shown", True))

    for name, ok in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    passed = sum(ok for _, ok in results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
