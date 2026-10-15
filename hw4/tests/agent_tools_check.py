"""Check that the agent answers price and stock questions from the database (Problem 6).

For each question this prints the tools the agent called and its reply, then checks that
the dollar amounts and stock numbers it quoted match campus_customs.db.

From the HOME WORK 4 folder:
    ../.venv/Scripts/python.exe tests/agent_tools_check.py
"""

import asyncio
import re
import sqlite3
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

from pydantic_ai.messages import ToolCallPart  # noqa: E402

from agent import CHAT_USAGE_LIMITS, get_agent  # noqa: E402
from tools import DB_PATH, AgentDeps  # noqa: E402

# (question, product_id the answer is about, size or None, tool that must be called)
CASES = [
    ("How much is the Basic Hoodie Big Yale?", "basic-hoodie-big-yale", None, "get_product_details|check_stock|search_products"),
    ("Do you have the Baseball Left Chest Crewneck in XL?", "baseball-left-chest-crewneck", "XL", "check_stock|get_product_details"),
    ("How many Baseball Left Chest Crewnecks do you have in medium?", "baseball-left-chest-crewneck", "M", "check_stock|get_product_details"),
    ("Is the T Felt Y Heavyweight tee available in large?", "t-felt-y-heavyweight", "L", "check_stock|get_product_details"),
    ("Do you have any pink hoodies?", None, None, "search_products"),
    ("Show me navy hoodies under $70 that come in medium", None, "M", "search_products"),
    ("What does the Yale Mom Crewneck look like and what colors does it come in?", "yale-mom-crewneck", None, "get_product_details"),
]


def db_facts(product_id: str) -> tuple[float, dict[str, int]]:
    with sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True) as conn:
        price = conn.execute("SELECT price FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()[0]
        sizes = dict(conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall())
    return price, sizes


async def main() -> int:
    agent = get_agent()
    failures = 0
    for question, product_id, size, required_tools in CASES:
        result = await agent.run(question, deps=AgentDeps(), usage_limits=CHAT_USAGE_LIMITS)
        calls = [
            f"{p.tool_name}({p.args_as_dict()})"
            for m in result.all_messages()
            for p in getattr(m, "parts", [])
            if isinstance(p, ToolCallPart) and p.tool_name != "final_result"
        ]
        reply = result.output.reply
        problems = []
        if not any(re.search(rf"^({required_tools})\(", c) for c in calls):
            problems.append(f"expected a call to {required_tools}")

        if product_id:
            price, sizes = db_facts(product_id)
            for amount in re.findall(r"\$(\d+(?:\.\d\d)?)", reply):
                if float(amount) != price:
                    problems.append(f"quoted ${amount} but the database price is ${price:.2f}")
            if size:
                qty = sizes[size]
                says_out = re.search(r"out of stock|sold out|none left|don.t have any|0 left", reply, re.I)
                if qty == 0 and not says_out:
                    problems.append(f"{size} has 0 in stock but the reply doesn't say it's out of stock")
                if qty > 0 and says_out and size in reply and re.search(rf"out of stock in {size}\b", reply):
                    problems.append(f"{size} has {qty} in stock but the reply says it's out")
                if qty > 0 and str(qty) not in reply and "how many" in question.lower():
                    problems.append(f"expected the quantity {qty} for {size}")

        failures += bool(problems)
        print(f"\n[{'PASS' if not problems else 'FAIL'}] {question}")
        print(f"   tools: {'; '.join(calls) or '(none)'}")
        print(f"   reply: {reply}")
        print(f"   cards: {result.output.product_ids}")
        for p in problems:
            print(f"   !! {p}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} questions answered from the database")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
