"""Real-browser test of customer memory and page context (Problem 8).

Guests can chat but nothing is saved; a logged-in customer's chat is saved to the database and
reloaded when they come back; and on a product page, "this" means that product.

From the HOME WORK 4 folder, with both servers running:
    ../.venv/Scripts/python.exe tests/browser_memory_test.py [--headless]
Screenshots go to output/browser_proof/memory-*.png.
"""

import sqlite3
import sys
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

SITE = "http://localhost:5180"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "browser_proof"
from _paths import DB_PATH  # noqa: E402  (finds data/ or data/data/)
SEED_EMAIL = "test@campuscustoms.yale.edu"
SEED_PASSWORD = "password"
REPLY_TIMEOUT_MS = 90_000

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{f'  ({detail})' if detail else ''}")


def saved_rows(user_id: int | None = None) -> int:
    with sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True) as conn:
        if user_id is None:
            return conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)).fetchone()[0]


def ask(page: Page, question: str) -> str:
    before = page.locator(".chat-bubble.assistant:not(.typing)").count()
    page.get_by_label("Message").press_sequentially(question, delay=8)
    page.get_by_role("button", name="Send").click()
    reply = page.locator(".chat-bubble.assistant:not(.typing)").nth(before)
    expect(reply).to_be_visible(timeout=REPLY_TIMEOUT_MS)
    text = reply.inner_text()
    print(f"   Q: {question}\n   A: {text}")
    return text


def open_chat(page: Page) -> None:
    if page.locator(".chat-panel").count() == 0:
        page.get_by_role("button", name="Open chat").click()
    expect(page.locator(".chat-panel")).to_be_visible()


def main(headless: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=0 if headless else 60)
        page = browser.new_page(viewport={"width": 1280, "height": 860})

        # 1. Guest: can chat, nothing saved, gone after reload
        page.goto(f"{SITE}/products/yale-mom-crewneck")
        open_chat(page)
        expect(page.locator(".chat-bubble.assistant").first).to_contain_text("Log in to have me remember")
        rows_before = saved_rows()
        reply = ask(page, "Does this come in navy?")
        check("Guest can chat, and 'this' means the product on the page", "Yale Mom Crewneck" in reply)
        check("Guest chat is not saved to the database", saved_rows() == rows_before)
        page.reload()
        open_chat(page)
        check("Guest chat is gone after a reload", page.locator(".chat-bubble.user").count() == 0)

        # 2. Log in: saved history comes back
        page.goto(f"{SITE}/login")
        page.get_by_label("Email").press_sequentially(SEED_EMAIL, delay=8)
        page.get_by_label("Password").press_sequentially(SEED_PASSWORD, delay=8)
        page.get_by_role("button", name="Log in").click()
        expect(page.locator(".nav-account")).to_contain_text("Hi, Test")
        open_chat(page)
        expect(page.locator(".chat-bubble.assistant").first).to_contain_text("Welcome back, Test")
        restored = page.locator(".chat-turn.restored").count()
        check("Logged-in customer's saved chat is reloaded", restored == min(saved_rows(1), 50), f"{restored} messages")
        page.screenshot(path=str(OUT / "memory-01-history-restored.png"))

        # 3. Product page context: "this in pink", then a selected size
        page.locator(".chat-close").click()
        page.goto(f"{SITE}/products/basic-hoodie-big-yale")
        expect(page.locator(".product-detail-info h1")).to_have_text("Basic Hoodie Big Yale")
        open_chat(page)
        rows_before = saved_rows(1)
        reply = ask(page, "do you have this in pink?")
        check("'this in pink' is answered about the product on the page", "Basic Hoodie Big Yale" in reply and "pink" in reply.lower())
        check("Logged-in exchange is saved (2 rows)", saved_rows(1) == rows_before + 2)
        page.screenshot(path=str(OUT / "memory-02-this-in-pink.png"))

        page.locator(".size-btn", has_text="M").first.click()
        reply = ask(page, "is it in stock in the size I picked?")
        check("Selected size is understood (M, 5 left)", ("M" in reply or "medium" in reply.lower()) and "5" in reply)

        # 4. Leave and come back: the new messages are still there
        page.reload()
        open_chat(page)
        expect(page.locator(".chat-bubble.user").last).to_have_text("is it in stock in the size I picked?")
        check("New messages survive a page reload", True)

        # 5. Log out: chat is cleared from the screen; log back in: it's back
        page.locator(".chat-close").click()
        page.get_by_role("button", name="Log out").click()
        expect(page.locator(".nav-account")).to_contain_text("Log in")
        open_chat(page)
        check("Logging out clears the chat window", page.locator(".chat-bubble.user").count() == 0)
        page.locator(".chat-close").click()
        page.goto(f"{SITE}/login")
        page.get_by_label("Email").press_sequentially(SEED_EMAIL, delay=8)
        page.get_by_label("Password").press_sequentially(SEED_PASSWORD, delay=8)
        page.get_by_role("button", name="Log in").click()
        expect(page.locator(".nav-account")).to_contain_text("Hi, Test")
        open_chat(page)
        expect(page.locator(".chat-bubble.user").last).to_have_text("is it in stock in the size I picked?")
        check("Logging back in restores the conversation", True)
        page.screenshot(path=str(OUT / "memory-03-back-after-login.png"))

        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(headless="--headless" in sys.argv))
