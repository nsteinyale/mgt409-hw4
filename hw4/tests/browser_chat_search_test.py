"""Real-browser test: chat search updates the page, and cards still open the detail page (Problem 7).

From the HOME WORK 4 folder, with both servers running:
    ../.venv/Scripts/python.exe tests/browser_chat_search_test.py [--headless]
Screenshots go to output/browser_proof/search-*.png.
"""

import sys
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

SITE = "http://localhost:5180"
OUT = Path(__file__).resolve().parent.parent / "output" / "browser_proof"
REPLY_TIMEOUT_MS = 90_000

results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{f'  ({detail})' if detail else ''}")


def ask(page: Page, question: str) -> str:
    before = page.locator(".chat-bubble.assistant:not(.typing)").count()
    page.get_by_label("Message").press_sequentially(question, delay=8)
    page.get_by_role("button", name="Send").click()
    reply = page.locator(".chat-bubble.assistant:not(.typing)").nth(before)
    expect(reply).to_be_visible(timeout=REPLY_TIMEOUT_MS)
    text = reply.inner_text()
    print(f"   Q: {question}\n   A: {text}")
    return text


def main(headless: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=0 if headless else 60)
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        catalogue = {c["product_id"]: c for c in page.request.get(f"{SITE}/api/products").json()}

        # 1. Ask for a type of item from the home page
        page.goto(SITE)
        page.get_by_role("button", name="Open chat").click()
        ask(page, "Show me your hoodies")
        banner = page.locator(".chat-results-banner")
        expect(banner).to_be_visible(timeout=10_000)
        check("Page switched to chat results", "/products?view=chat" in page.url, page.url)
        cards = page.locator(".chat-results .product-card")
        expect(cards.first).to_be_visible()
        page.wait_for_timeout(1200)  # let the card animation finish for the screenshot
        count = cards.count()
        print(f"   banner: {banner.inner_text().splitlines()[1:3]}")
        check("Hoodie cards rendered on the page", count >= 20, f"{count} cards")

        # Every card's name and price must match the catalogue
        mismatches = []
        for i in range(count):
            card = cards.nth(i)
            pid = card.get_attribute("href").rsplit("/", 1)[-1]
            name = card.locator("h3").inner_text()
            price = card.locator(".price").inner_text()
            db = catalogue.get(pid)
            if not db or db["name"] != name or f"${db['price']:.2f}" != price:
                mismatches.append(pid)
        check("Every card's name and price match the database", not mismatches, ", ".join(mismatches))
        page.locator(".chat-close").click()
        page.screenshot(path=str(OUT / "search-01-hoodies-on-page.png"))

        # 2. Click a card the chat put on the page -> single-item page
        target = cards.nth(2)
        target_name = target.locator("h3").inner_text()
        target.click()
        expect(page.locator(".product-detail-info h1")).to_have_text(target_name)
        check("Clicking a chat result opens its detail page", "/products/" in page.url, page.url)
        check("Detail page has the large image", page.locator(".product-detail-image img").is_visible())
        check("Detail page shows sizes", page.locator(".size-btn").count() == 6)
        page.screenshot(path=str(OUT / "search-02-detail-from-results.png"))

        # 3. Back to the results
        page.get_by_role("link", name="Back to").click()
        expect(page.locator(".chat-results-banner")).to_be_visible()
        check("'Back to' link returns to the chat results", page.locator(".chat-results .product-card").count() == count)

        # 4. A card inside the chat panel also opens the detail page
        page.get_by_role("button", name="Open chat").click()
        chat_card = page.locator(".chat-product").first
        if chat_card.count():
            chat_name = chat_card.locator("strong").inner_text()
            chat_card.click()
            expect(page.locator(".product-detail-info h1")).to_have_text(chat_name)
            check("Clicking a card in the chat opens its detail page", True, chat_name)
        else:
            check("Clicking a card in the chat opens its detail page", False, "no chat cards")

        # 5. A single-item stock question should NOT replace the page
        detail_url = page.url
        ask(page, "Is this one in stock in XL?")
        page.wait_for_timeout(500)
        check("Single-item question leaves the detail page alone", page.url == detail_url)
        page.screenshot(path=str(OUT / "search-03-stock-question-stays.png"))

        # 6. A new search replaces the results
        ask(page, "Anything for Saybrook college?")
        expect(page.locator(".chat-results-banner")).to_be_visible(timeout=10_000)
        page.wait_for_timeout(1000)
        saybrook = page.locator(".chat-results .product-card h3").all_inner_texts()
        check("New search updates the page", bool(saybrook) and all("Saybrook" in n for n in saybrook), ", ".join(saybrook))
        page.screenshot(path=str(OUT / "search-04-saybrook.png"))

        # 7. "Show all products" goes back to the full catalogue
        page.locator(".chat-close").click()
        page.get_by_role("button", name="Show all products").click()
        expect(page.locator(".page-head h1")).to_have_text("All products")
        check("'Show all products' returns to the full catalogue", page.locator(".product-card").count() == len(catalogue))

        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(headless="--headless" in sys.argv))
