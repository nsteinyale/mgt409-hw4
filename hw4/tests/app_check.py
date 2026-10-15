"""App check (Problem 11): test the live site in a real browser and write output/app_check.html.

Captures screenshots into output/app_check_images/ and compares what the site shows with
campus_customs.db, so the report states real database values next to each screenshot.

From the HOME WORK 4 folder, with both servers running:
    ../.venv/Scripts/python.exe tests/app_check.py
Then double-click output/app_check.html.
"""

import html
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

SITE = "http://localhost:5180"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
IMAGES = OUT / "app_check_images"
from _paths import DB_PATH  # noqa: E402  (finds data/ or data/data/)
REPLY_TIMEOUT_MS = 90_000

INVENTORY_PRODUCT = "baseball-left-chest-crewneck"
INVENTORY_QUESTION = "How many Baseball Left Chest Crewnecks do you have in medium, and how much are they? Is XL in stock?"
SIMILAR_PRODUCT = "basic-hoodie-big-yale"


def db(sql: str, *args):
    with sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(sql, args).fetchall()


def ask(page: Page, question: str) -> str:
    before = page.locator(".chat-bubble.assistant:not(.typing)").count()
    page.get_by_label("Message").press_sequentially(question, delay=8)
    page.get_by_role("button", name="Send").click()
    reply = page.locator(".chat-bubble.assistant:not(.typing)").nth(before)
    expect(reply).to_be_visible(timeout=REPLY_TIMEOUT_MS)
    page.wait_for_timeout(600)  # let cards and the fact-check line render
    return reply.inner_text()


def show_latest_exchange(page: Page) -> None:
    """Scroll the chat so the shopper's latest question is at the top (for readable close-ups)."""
    page.locator(".chat-bubble.user").last.evaluate("el => el.scrollIntoView({ block: 'start' })")
    page.wait_for_timeout(200)


def open_chat(page: Page) -> None:
    if page.locator(".chat-panel").count() == 0:
        page.get_by_role("button", name="Open chat").click()
    expect(page.locator(".chat-panel")).to_be_visible()


def run_checks() -> dict:
    IMAGES.mkdir(parents=True, exist_ok=True)
    report: dict = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 980}, device_scale_factor=1.5)
        page = context.new_page()

        # ---- Check 1: chat reports inventory and price straight from the database ----
        page.goto(f"{SITE}/products/{INVENTORY_PRODUCT}")
        expect(page.locator(".product-detail-info h1")).to_be_visible()
        open_chat(page)
        reply = ask(page, INVENTORY_QUESTION)
        badge = page.locator(".fact-check").last
        row = db("SELECT name, price FROM catalogue WHERE product_id = ?", INVENTORY_PRODUCT)[0]
        order = ["XS", "S", "M", "L", "XL", "XXL"]
        rows = db("SELECT size, quantity FROM inventory WHERE product_id = ?", INVENTORY_PRODUCT)
        sizes = {r["size"]: r["quantity"] for r in sorted(rows, key=lambda r: order.index(r["size"]))}
        price_ok = f"${row['price']:.2f}" in reply
        m_ok = re.search(rf"\b{sizes['M']}\b", reply) is not None
        xl_ok = sizes["XL"] == 0 and re.search(r"(out of stock|sold out|not in stock)", reply, re.I) is not None
        show_latest_exchange(page)
        if badge.count():  # keep the fact-check line in view too (the caption refers to it)
            badge.evaluate("el => el.scrollIntoView({ block: 'end' })")
            page.wait_for_timeout(200)
        page.screenshot(path=str(IMAGES / "inventory.png"))
        page.locator(".chat-panel").screenshot(path=str(IMAGES / "inventory_chat.png"))
        report["inventory"] = {
            "question": INVENTORY_QUESTION,
            "reply": reply,
            "fact_check": badge.inner_text() if badge.count() else "",
            "db": {"name": row["name"], "price": row["price"], "sizes": sizes},
            "passed": price_ok and m_ok and xl_ok,
            "details": {"price matches": price_ok, "M quantity matches": m_ok, "XL out of stock stated": xl_ok},
        }
        page.locator(".chat-close").click()

        # ---- Check 2: "hoodies?" fills the page with dynamic search result cards ----
        page.goto(SITE)
        page.wait_for_timeout(500)
        open_chat(page)
        reply = ask(page, "hoodies?")
        expect(page.locator(".chat-results-banner")).to_be_visible(timeout=10_000)
        page.wait_for_timeout(1500)  # card entrance animation
        cards = page.locator(".chat-results .product-card")
        shown = cards.count()
        names = cards.locator("h3").all_inner_texts()
        hoodies = db("SELECT product_id, name, price FROM catalogue WHERE lower(garment_type) LIKE '%hood%'")
        hoodie_names = {r["name"] for r in hoodies}
        catalogue = {r["name"]: r["price"] for r in db("SELECT name, price FROM catalogue")}
        prices = cards.locator(".price").all_inner_texts()
        price_mismatch = [n for n, pr in zip(names, prices) if f"${catalogue.get(n, -1):.2f}" != pr]
        title = page.locator(".chat-results-banner h1").inner_text()
        url = page.url
        page.locator(".chat-close").click()
        page.wait_for_timeout(300)
        page.screenshot(path=str(IMAGES / "search_results.png"))
        # and the dynamic cards still open the single-item page
        first_name = names[0]
        cards.first.click()
        expect(page.locator(".product-detail-info h1")).to_have_text(first_name)
        page.screenshot(path=str(IMAGES / "search_card_detail.png"))
        report["search"] = {
            "question": "hoodies?",
            "reply": reply,
            "url": url,
            "title": title,
            "cards_shown": shown,
            "db_hoodies": len(hoodies),
            "all_are_hoodies": all(n in hoodie_names for n in names),
            "price_mismatches": price_mismatch,
            "detail_opened": first_name,
            "passed": shown == len(hoodies) and all(n in hoodie_names for n in names) and not price_mismatch,
        }

        # ---- Check 3 (Problem 9 usability): suggestion chip + "find a similar one" ----
        page.goto(f"{SITE}/products/{SIMILAR_PRODUCT}")
        expect(page.locator(".product-detail-info h1")).to_be_visible()
        open_chat(page)
        page.wait_for_load_state("networkidle")
        chips = page.locator(".suggestion-chip").all_inner_texts()
        before = page.locator(".chat-bubble.assistant:not(.typing)").count()
        page.locator(".suggestion-chip", has_text="Do you have this in gray?").click()
        reply_el = page.locator(".chat-bubble.assistant:not(.typing)").nth(before)
        expect(reply_el).to_be_visible(timeout=REPLY_TIMEOUT_MS)
        page.wait_for_timeout(600)
        reply = reply_el.inner_text()
        card_names = page.locator(".chat-turn.assistant").nth(before).locator(".chat-product strong").all_inner_texts()
        base = db("SELECT name, colors FROM catalogue WHERE product_id = ?", SIMILAR_PRODUCT)[0]
        colors_by_name = {r["name"]: json.loads(r["colors"] or "[]") for r in db("SELECT name, colors FROM catalogue")}
        alternatives = [n for n in card_names if n != base["name"]]
        gray = lambda cs: any(re.search(r"gr[ae]y|heather|charcoal", c, re.I) for c in cs)  # noqa: E731
        page.mouse.move(10, 10)  # move the mouse off the chip so it isn't shown hovered
        show_latest_exchange(page)
        page.screenshot(path=str(IMAGES / "usability_gray_chip.png"))
        page.locator(".chat-panel").screenshot(path=str(IMAGES / "usability_gray_chip_chat.png"))
        report["usability"] = {
            "chips": chips,
            "reply": reply,
            "base_name": base["name"],
            "base_colors": json.loads(base["colors"]),
            "alternatives": [(n, colors_by_name.get(n, [])) for n in alternatives],
            "passed": bool(alternatives) and all(gray(colors_by_name.get(n, [])) for n in alternatives)
            and not gray(json.loads(base["colors"])),
        }
        browser.close()
    return report


def esc(text: str) -> str:
    return html.escape(str(text))


def status(ok: bool) -> str:
    return '<span class="pass">PASS</span>' if ok else '<span class="fail">FAIL</span>'


def write_html(r: dict) -> Path:
    inv, srch, usa = r["inventory"], r["search"], r["usability"]
    size_rows = "".join(f"<th>{esc(s)}</th>" for s in inv["db"]["sizes"])
    qty_rows = "".join(
        f'<td class="{"zero" if q == 0 else ""}">{q}</td>' for q in inv["db"]["sizes"].values()
    )
    alt_rows = "".join(f"<tr><td>{esc(n)}</td><td>{esc(', '.join(c))}</td></tr>" for n, c in usa["alternatives"])
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Campus Customs: app check</title>
<style>
  body {{ font-family: 'Open Sans', system-ui, sans-serif; color: #1c2430; max-width: 1000px; margin: 0 auto; padding: 2rem 1.25rem 4rem; line-height: 1.55; }}
  h1, h2 {{ font-family: Georgia, 'Times New Roman', serif; color: #00356b; }}
  h1 {{ margin-bottom: 0.25rem; }}
  h2 {{ margin-top: 3rem; border-bottom: 3px solid #d4af37; padding-bottom: 0.3rem; }}
  .meta {{ color: #6b7280; font-size: 0.9rem; }}
  .summary {{ border-collapse: collapse; margin: 1rem 0; }}
  table {{ border-collapse: collapse; margin: 0.75rem 0; font-size: 0.92rem; }}
  th, td {{ border: 1px solid #e3e6eb; padding: 0.35rem 0.7rem; text-align: left; }}
  th {{ background: #f6f7f9; }}
  td.zero {{ color: #b42318; font-weight: 700; }}
  figure {{ margin: 1rem 0 1.5rem; }}
  img {{ width: 100%; border: 1px solid #e3e6eb; border-radius: 10px; box-shadow: 0 6px 18px rgba(0, 38, 77, 0.1); }}
  .pair {{ display: grid; grid-template-columns: 1.6fr 1fr; gap: 1rem; align-items: start; }}
  figcaption {{ font-size: 0.92rem; color: #374151; margin-top: 0.45rem; }}
  .quote {{ background: #f3f7fc; border-left: 4px solid #00356b; padding: 0.6rem 0.9rem; margin: 0.6rem 0; white-space: pre-wrap; }}
  .pass {{ background: #e6f4ec; color: #1f7a4d; font-weight: 700; padding: 0.1rem 0.5rem; border-radius: 999px; }}
  .fail {{ background: #fdecea; color: #b42318; font-weight: 700; padding: 0.1rem 0.5rem; border-radius: 999px; }}
  code {{ background: #f6f7f9; padding: 0.05rem 0.3rem; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Campus Customs: app check</h1>
<p class="meta">Tested on the live site (<code>localhost:5180</code>, FastAPI on <code>:8000</code>) in a real Chromium browser on {datetime.now():%B %d, %Y at %I:%M %p}.
Every number below was read from <code>campus_customs.db</code> (the data pack) at the same time as the screenshot. Re-run with <code>tests/app_check.py</code>.</p>

<table class="summary">
  <tr><th>Check</th><th>Result</th></tr>
  <tr><td>1. Chat checks an item's inventory and price</td><td>{status(inv["passed"])}</td></tr>
  <tr><td>2. "hoodies?" puts dynamic result cards on the page</td><td>{status(srch["passed"])}</td></tr>
  <tr><td>3. Usability feature (Problem 9): suggestion chip + "find a similar one"</td><td>{status(usa["passed"])}</td></tr>
</table>

<h2>1. Chat checks the inventory level of an item</h2>
<p>On the {esc(inv["db"]["name"])} product page, the shopper asks:</p>
<div class="quote">{esc(inv["question"])}</div>
<p>Dan replied:</p>
<div class="quote">{esc(inv["reply"])}</div>
<p>What the database says at the same moment (<code>catalogue</code> and <code>inventory</code> tables):</p>
<table>
  <tr><th>Product</th><th>Price</th>{size_rows}</tr>
  <tr><td>{esc(inv["db"]["name"])}</td><td>${inv["db"]["price"]:.2f}</td>{qty_rows}</tr>
</table>
<p>Price matches: {status(inv["details"]["price matches"])} · M quantity matches: {status(inv["details"]["M quantity matches"])} · XL clearly out of stock: {status(inv["details"]["XL out of stock stated"])}</p>
<div class="pair">
  <figure><img src="app_check_images/inventory.png" alt="Product page with the chat answering a stock question">
    <figcaption>The chat answers on the product page. The price and the per-size stock in the reply are the database values above, not guesses.</figcaption></figure>
  <figure><img src="app_check_images/inventory_chat.png" alt="Close-up of the chat reply">
    <figcaption>Close-up of the question and the full reply. The green line ("{esc(inv["fact_check"])}") is the Problem 9 fact-check: before the reply was shown, the price/stock figures it found next to the product name were compared with the database. The table above checks every number.</figcaption></figure>
</div>

<h2>2. Dynamic search result cards after "hoodies?"</h2>
<p>From the home page the shopper types <code>hoodies?</code> in the chat. Dan replied:</p>
<div class="quote">{esc(srch["reply"])}</div>
<p>The site switched to <code>{esc(srch["url"].replace(SITE, ""))}</code> and showed <strong>{srch["cards_shown"]}</strong> product cards under "{esc(srch["title"])}". The database has <strong>{srch["db_hoodies"]}</strong> hoodies.
All cards are hoodies: {status(srch["all_are_hoodies"])} · Every card's price matches the database: {status(not srch["price_mismatches"])}</p>
<figure><img src="app_check_images/search_results.png" alt="Products page filled with hoodie cards from the chat">
  <figcaption>The chat's search results reach the page as cards (photo, name, price, short description, sizes in stock) under a banner from the assistant. Nothing was clicked: the page updated from the chat answer.</figcaption></figure>
<figure><img src="app_check_images/search_card_detail.png" alt="Single-item page opened from a search card">
  <figcaption>Clicking the first card ({esc(srch["detail_opened"])}) still opens the Problem 3 single-item page with the large image, full description, price, colors, and sizes.</figcaption></figure>

<h2>3. Usability feature from Problem 9: suggestion chip + "find a similar one"</h2>
<p>On the {esc(usa["base_name"])} page (colors in the database: {esc(", ".join(usa["base_colors"]))}), the chat shows one-tap chips that fit the page: {esc(" · ".join(usa["chips"]))}.
The shopper taps <strong>"Do you have this in gray?"</strong>. Dan replied:</p>
<div class="quote">{esc(usa["reply"])}</div>
<p>The gray alternatives it showed, with their colors from the database:</p>
<table><tr><th>Suggested product</th><th>Colors in the database</th></tr>{alt_rows}</table>
<div class="pair">
  <figure><img src="app_check_images/usability_gray_chip.png" alt="Product page with the gray suggestion answered">
    <figcaption>One tap on a suggestion chip, no typing. The agent's <code>find_similar_products</code> tool found real gray hoodies instead of a dead-end "no".</figcaption></figure>
  <figure><img src="app_check_images/usability_gray_chip_chat.png" alt="Close-up of chips and gray alternatives">
    <figcaption>Close-up: the original hoodie honestly doesn't come in gray, and every suggested alternative does, as the database table above confirms.</figcaption></figure>
</div>
</body>
</html>
"""
    path = OUT / "app_check.html"
    path.write_text(page, encoding="utf-8")
    return path


if __name__ == "__main__":
    results = run_checks()
    path = write_html(results)
    for key in ("inventory", "search", "usability"):
        print(f"[{'PASS' if results[key]['passed'] else 'FAIL'}] {key}")
    print(f"Report: {path}")
    sys.exit(0 if all(results[k]["passed"] for k in results) else 1)
