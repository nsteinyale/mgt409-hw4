"""Real-browser test of the Problem 9 usability improvements (all eight show up in the running app).

Front end: suggestion chips, recently viewed, "Ask about this item", clickable colors.
Backend:   find-similar tool, fact-check badge, remember my size, back-in-stock waitlist.

Creates a fresh test account with an @example.com address (reserved for testing, never a real inbox).
From the HOME WORK 4 folder, with both servers running:
    ../.venv/Scripts/python.exe tests/browser_usability_test.py [--headless]
Screenshots go to output/browser_proof/usability-*.png.
"""

import secrets
import sqlite3
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

SITE = "http://localhost:5180"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "browser_proof"
from _paths import DB_PATH  # noqa: E402  (finds data/ or data/data/)
REPLY_TIMEOUT_MS = 90_000
EMAIL = f"usability.{int(time.time())}@example.com"
PASSWORD = secrets.token_urlsafe(12)

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{f'  ({detail})' if detail else ''}")


def db(sql: str, *args):
    with sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True) as conn:
        return conn.execute(sql, args).fetchall()


def wait_for_reply(page: Page, before: int) -> str:
    reply = page.locator(".chat-bubble.assistant:not(.typing)").nth(before)
    expect(reply).to_be_visible(timeout=REPLY_TIMEOUT_MS)
    text = reply.inner_text()
    print(f"   A: {text}")
    return text


def replies(page: Page) -> int:
    return page.locator(".chat-bubble.assistant:not(.typing)").count()


def open_chat(page: Page) -> None:
    """Open the chat panel (if closed) and let any saved history finish loading."""
    if page.locator(".chat-panel").count() == 0:
        page.get_by_role("button", name="Open chat").click()
    expect(page.locator(".chat-panel")).to_be_visible()
    page.wait_for_load_state("networkidle")


def type_and_send(page: Page, question: str) -> str:
    before = replies(page)
    print(f"   Q: {question}")
    page.get_by_label("Message").press_sequentially(question, delay=8)
    page.get_by_role("button", name="Send").click()
    return wait_for_reply(page, before)


def main(headless: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=0 if headless else 60)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # ---- Front end 2: Recently viewed (guest, stored only in the browser) ----
        page.goto(f"{SITE}/products/basic-hoodie-big-yale")
        expect(page.locator(".product-detail-info h1")).to_have_text("Basic Hoodie Big Yale")
        page.goto(f"{SITE}/products/saybrook-college-crewneck")
        strip = page.locator(".recently-viewed")
        expect(strip).to_be_visible()
        check("Recently viewed shows the hoodie on the next product page", "Basic Hoodie Big Yale" in strip.inner_text())
        page.goto(f"{SITE}/products")
        names = page.locator(".recently-viewed .recent-name").all_inner_texts()
        check("Recently viewed on the Products page, newest first", names[:2] == ["Saybrook College Crewneck", "Basic Hoodie Big Yale"], ", ".join(names))
        page.screenshot(path=str(OUT / "usability-01-recently-viewed.png"))
        stored = page.evaluate("localStorage.getItem('cc_recently_viewed')") or ""
        check("Recently viewed is stored only in the browser (localStorage)", "saybrook-college-crewneck" in stored)
        page.locator(".recently-viewed").get_by_role("button", name="Clear").click()
        check("'Clear' removes the recently viewed strip", page.locator(".recently-viewed").count() == 0)

        # Fresh test account
        page.goto(f"{SITE}/create-account")
        page.get_by_label("First name").fill("Una")
        page.get_by_label("Last name").fill("Bility")
        page.get_by_label("Email").fill(EMAIL)
        page.get_by_label("Password", exact=True).fill(PASSWORD)
        page.get_by_label("Confirm password").fill(PASSWORD)
        page.get_by_role("button", name="Create account").click()
        expect(page.locator(".nav-account")).to_contain_text("Hi, Una")
        user_id = db("SELECT id FROM users WHERE email = ?", EMAIL)[0][0]

        # ---- Front end 3: "Ask about this item" + Backend 2: fact-check badge ----
        page.goto(f"{SITE}/products/baseball-left-chest-crewneck")
        expect(page.locator(".product-detail-info h1")).to_have_text("Baseball Left Chest Crewneck")
        open_chat(page)
        page.locator(".chat-close").click()  # start closed: the button should open it
        before = 1 + len(db("SELECT id FROM chat_messages WHERE user_id = ? AND role = 'assistant'", user_id))
        page.get_by_role("button", name="Ask about this item").click()
        expect(page.locator(".chat-panel")).to_be_visible()
        reply = wait_for_reply(page, before)
        check("'Ask about this item' opens the chat about this product", "Baseball Left Chest Crewneck" in reply)
        badge = page.locator(".fact-check").last
        expect(badge).to_be_visible()
        check("Fact-check badge shows under the reply", "checked against live inventory" in badge.inner_text(), badge.inner_text())
        page.screenshot(path=str(OUT / "usability-02-ask-about-this-fact-check.png"))

        # ---- Front end 1: suggestion chips + Backend 1: find-similar ("a gray one") ----
        page.goto(f"{SITE}/products/basic-hoodie-big-yale")
        expect(page.locator(".product-detail-info h1")).to_have_text("Basic Hoodie Big Yale")
        open_chat(page)
        chips = page.locator(".suggestion-chip").all_inner_texts()
        check("Product page shows page-specific suggestion chips", "Do you have this in gray?" in chips, " | ".join(chips))
        before = replies(page)
        page.locator(".suggestion-chip", has_text="Do you have this in gray?").click()
        reply = wait_for_reply(page, before)
        cards = page.locator(".chat-turn.assistant").nth(before).locator(".chat-product strong").all_inner_texts()
        gray_ids = {r[0] for r in db("SELECT product_id FROM catalogue WHERE lower(colors) LIKE '%gray%' OR lower(colors) LIKE '%grey%'")}
        name_to_id = {r[1]: r[0] for r in db("SELECT product_id, name FROM catalogue")}
        alternatives = [c for c in cards if c != "Basic Hoodie Big Yale"]  # the original may be shown too
        all_gray = bool(alternatives) and all(name_to_id.get(c) in gray_ids for c in alternatives)
        check("'A gray one' finds real gray alternatives (find_similar_products)", "gray" in reply.lower() and all_gray, ", ".join(alternatives))
        page.screenshot(path=str(OUT / "usability-03-chip-gray-similar.png"))

        # Chips change with the page
        page.goto(f"{SITE}/products")
        open_chat(page)
        catalogue_chips = page.locator(".suggestion-chip").all_inner_texts()
        check("Products page shows different chips", "Hoodies under $70" in catalogue_chips, " | ".join(catalogue_chips))

        # ---- Front end 4: clickable colors ----
        page.goto(f"{SITE}/products/basic-hoodie-big-yale")
        expect(page.locator(".swatch-label").first).to_be_visible()
        own = page.locator(".swatch-label").all_inner_texts()
        check("Product colors shown as swatches", [c.lower() for c in own] == ["navy blue", "white"], ", ".join(own))
        open_chat(page)
        before = replies(page)
        page.locator(".chat-close").click()  # the open panel covers the swatches; clicking one reopens it
        page.locator(".swatch-button", has_text="green").click()
        reply = wait_for_reply(page, before)
        check("Clicking a color swatch asks the assistant for that color", "green" in reply.lower())
        page.screenshot(path=str(OUT / "usability-04-color-swatch.png"))

        # ---- Backend 3: remember my size (opt-in, via chat) ----
        reply = type_and_send(page, "Please remember that I'm a medium.")
        expect(page.locator(".size-chip")).to_contain_text("M", timeout=10_000)
        saved = db("SELECT preferred_size FROM customer_preferences WHERE user_id = ?", user_id)
        check("Asking to remember a size saves it to the account", saved == [("M",)], str(saved))
        page.goto(f"{SITE}/products/baseball-left-chest-crewneck")
        expect(page.locator(".size-btn.saved")).to_have_text("M")
        check("Saved size is pre-selected on product pages", "selected" in (page.locator(".size-btn.saved").get_attribute("class") or ""))
        open_chat(page)
        reply = type_and_send(page, "Is this in stock in my size?")
        check("Agent uses the saved size for 'my size'", ("M" in reply or "medium" in reply.lower()) and "5" in reply)
        page.screenshot(path=str(OUT / "usability-05-saved-size.png"))

        # ---- Backend 4: back-in-stock waitlist (button and chat) ----
        page.locator(".chat-close").click()
        page.locator(".size-btn", has_text="XL").first.click()
        expect(page.locator(".stock-note")).to_contain_text("Out of stock in XL")
        page.get_by_role("button", name="Join the waitlist for XL").click()
        expect(page.locator(".waitlist")).to_contain_text("You're on the waitlist for XL")
        rows = db("SELECT product_id, size FROM stock_requests WHERE user_id = ?", user_id)
        check("Waitlist button saves the request", ("baseball-left-chest-crewneck", "XL") in rows, str(rows))
        page.screenshot(path=str(OUT / "usability-06-waitlist.png"))
        open_chat(page)
        reply = type_and_send(page, "Can you put me on the waitlist for XS on this one?")
        rows = db("SELECT product_id, size FROM stock_requests WHERE user_id = ?", user_id)
        check("Agent adds a waitlist request through the join_waitlist tool", ("baseball-left-chest-crewneck", "XS") in rows, str(rows))
        check("Agent doesn't promise an email", "no email" in reply.lower() or "won't" in reply.lower() or "check back" in reply.lower() or "not send" in reply.lower())

        # Forget the size with the chip
        page.locator(".size-chip button").click()
        expect(page.locator(".size-chip")).to_have_count(0)
        check("Removing the size chip deletes the saved size", db("SELECT preferred_size FROM customer_preferences WHERE user_id = ?", user_id) == [])

        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(headless="--headless" in sys.argv))
