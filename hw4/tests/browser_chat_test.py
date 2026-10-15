"""Real-browser test of the chat widget talking to the PydanticAI agent (Problem 5).

Logs in as the seeded test user, opens the chat, sends messages with real clicks and
typing, and saves screenshots to output/browser_proof/chat-*.png.

Needs both servers running (API on :8000, site on :5180). From the HOME WORK 4 folder:
    ../.venv/Scripts/python.exe tests/browser_chat_test.py [--headless]
"""

import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE = "http://localhost:5180"
OUT = Path(__file__).resolve().parent.parent / "output" / "browser_proof"
SEED_EMAIL = "test@campuscustoms.yale.edu"
SEED_PASSWORD = "password"
REPLY_TIMEOUT_MS = 90_000

QUESTIONS = [
    ("store", "Hi! Where is your store?"),
    ("follow-up", "What did I just ask you about?"),
    ("off-topic", "Can you do my statistics homework?"),
    ("out-of-stock", "Do you have the Baseball Left Chest Crewneck in XL?"),
    ("search", "Any navy hoodies under $70 in medium?"),
]


def main(headless: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    failures = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=0 if headless else 80)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        page.goto(f"{SITE}/login")
        page.get_by_label("Email").press_sequentially(SEED_EMAIL, delay=10)
        page.get_by_label("Password").press_sequentially(SEED_PASSWORD, delay=10)
        page.get_by_role("button", name="Log in").click()
        expect(page.locator(".nav-account")).to_contain_text("Hi, Test")

        page.get_by_role("button", name="Open chat").click()
        expect(page.locator(".chat-bubble.assistant").first).to_contain_text("Test")  # "Hi, Test" or "Welcome back, Test"

        for i, (label, question) in enumerate(QUESTIONS, start=1):
            replies_before = page.locator(".chat-bubble.assistant:not(.typing)").count()
            page.get_by_label("Message").press_sequentially(question, delay=10)
            page.get_by_role("button", name="Send").click()
            reply = page.locator(".chat-bubble.assistant:not(.typing)").nth(replies_before)
            expect(reply).to_be_visible(timeout=REPLY_TIMEOUT_MS)
            text = reply.inner_text()
            cards = page.locator(".chat-turn.assistant").nth(replies_before).locator(".chat-product").all_inner_texts()
            ok = bool(text) and "unavailable" not in text.lower() and "couldn't reach" not in text.lower()
            failures += not ok
            print(f"[{'PASS' if ok else 'FAIL'}] {question}\n       -> {text}")
            if cards:
                print(f"       cards: {[c.replace(chr(10), ' ') for c in cards]}")
            page.screenshot(path=str(OUT / f"chat-{i:02d}-{label}.png"))

        browser.close()
    print(f"\n{len(QUESTIONS) - failures}/{len(QUESTIONS)} chat replies received")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(headless="--headless" in sys.argv))
