"""Real-browser test of the Problem 10 style features.

Talking bulldog avatar, Bulldog Dash game (page, 404, offline), Harvard chase easter egg,
campus map flyover, and the polish (serif headings, card hover zoom, color dots, reduced motion).

From the HOME WORK 4 folder, with both servers running:
    ../.venv/Scripts/python.exe tests/browser_style_test.py [--headless]
Screenshots go to output/browser_proof/style-*.png.
"""

import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE = "http://localhost:5180"
OUT = Path(__file__).resolve().parent.parent / "output" / "browser_proof"
results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{f'  ({detail})' if detail else ''}")


def main(headless: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 860})
        page = context.new_page()

        # ---- Polish + Harvard chase on the first home visit ----
        page.goto(SITE)
        font = page.locator(".hero h1").evaluate("el => getComputedStyle(el).fontFamily")
        check("Headings use the collegiate serif", "Libre Baskerville" in font, font)
        chase = page.get_by_test_id("harvard-chase")
        expect(chase).to_be_visible(timeout=5000)
        page.wait_for_timeout(1800)
        check("Harvard chase plays on the first home visit", True)
        page.screenshot(path=str(OUT / "style-01-home-chase.png"))
        expect(chase).to_have_count(0, timeout=8000)
        page.reload()
        page.wait_for_timeout(2500)
        check("Chase plays only once per visit", page.get_by_test_id("harvard-chase").count() == 0)

        # ---- Map flyover ----
        page.locator(".campus-map").scroll_into_view_if_needed()
        page.wait_for_timeout(3200)
        zoom = page.locator(".campus-map .map-zoom").evaluate("el => getComputedStyle(el).transform")
        callout = page.locator(".campus-map .map-callout").evaluate("el => getComputedStyle(el).opacity")
        check("Map flies in toward 57 Broadway when scrolled into view", zoom.startswith("matrix(1.55"), zoom)
        check("Store callout appears after the flyover", callout == "1")
        page.locator(".campus-map").screenshot(path=str(OUT / "style-02-map-flyover.png"))

        # ---- Product presentation ----
        page.goto(f"{SITE}/products")
        card = page.locator(".product-grid .product-card").first
        expect(card).to_be_visible()
        check("Product cards show color dots", card.locator(".color-dot").count() >= 1)
        page.wait_for_timeout(800)  # let the page finish fading in
        card.hover()
        page.wait_for_timeout(500)
        img_t = card.locator("img").evaluate("el => getComputedStyle(el).transform")
        view = card.locator(".card-view").evaluate("el => getComputedStyle(el).opacity")
        check("Hovering a card zooms the photo and shows 'View details'", img_t.startswith("matrix(1.07") and view == "1", img_t)
        page.screenshot(path=str(OUT / "style-03-card-hover.png"))
        page.get_by_label("Search products").fill("harvard")
        expect(page.get_by_test_id("harvard-chase")).to_be_visible(timeout=3000)
        check("Searching 'harvard' sets off the chase", True)

        # ---- Talking bulldog avatar ----
        page.goto(f"{SITE}/products/basic-hoodie-big-yale")
        toggle = page.get_by_role("button", name="Open chat")
        check("Chat button shows Dan the bulldog", toggle.locator("svg.bulldog-face").count() == 1)
        toggle.click()
        face = page.locator(".chat-header svg.bulldog-face")
        expect(face).to_be_visible()
        check("Dan's face is in the chat header", True)
        page.get_by_label("Message").fill("Is this in stock in medium?")
        page.get_by_role("button", name="Send").click()
        expect(face).to_have_class("bulldog-face thinking", timeout=3000)
        check("Dan tilts his head while thinking", True)
        expect(face).to_have_attribute("data-talking", "true", timeout=90_000)
        page.wait_for_timeout(250)
        mouth = page.locator(".chat-header .bd-mouth-open").first.evaluate("el => getComputedStyle(el).animationName")
        check("Dan's mouth moves when the reply arrives", mouth == "bd-talk", mouth)
        page.screenshot(path=str(OUT / "style-04-dan-talking.png"))
        expect(face).to_have_attribute("data-talking", "false", timeout=8000)
        check("Dan stops talking afterwards", True)

        # ---- Bulldog Dash ----
        page.goto(f"{SITE}/play")
        game = page.locator(".bulldog-dash")
        canvas = game.locator("canvas")
        canvas.click()
        expect(game).to_have_attribute("data-phase", "running")
        for _ in range(6):  # a few jumps
            page.wait_for_timeout(700)
            canvas.press("Space")
        score = int(game.get_attribute("data-score") or 0)
        check("Bulldog Dash runs and keeps score", score > 0, f"score {score}")
        page.screenshot(path=str(OUT / "style-05-bulldog-dash.png"))
        expect(game).to_have_attribute("data-phase", "over", timeout=60_000)
        best = page.evaluate("localStorage.getItem('cc_bulldog_dash_hi')")
        check("Game over saves a high score in the browser", best is not None and int(best) > 0, f"best {best}")

        page.goto(f"{SITE}/this-page-does-not-exist")
        check("404 page offers Bulldog Dash", page.locator(".bulldog-dash canvas").count() == 1)

        # ---- Offline: game instead of a dead end ----
        page.goto(SITE)
        context.set_offline(True)
        banner = page.locator(".offline-banner")
        expect(banner).to_be_visible()
        banner.get_by_role("button", name="Play Bulldog Dash while you wait").click()
        expect(banner.locator("canvas")).to_be_visible()
        check("Going offline shows the banner with Bulldog Dash", True)
        page.screenshot(path=str(OUT / "style-06-offline-game.png"))
        context.set_offline(False)
        expect(banner).to_have_count(0)
        check("Banner disappears when back online", True)
        context.close()

        # ---- Reduced motion: no chase ----
        calm = browser.new_context(viewport={"width": 1280, "height": 860}, reduced_motion="reduce")
        calm_page = calm.new_page()
        calm_page.goto(SITE)
        calm_page.wait_for_timeout(3000)
        check("No chase for shoppers who prefer reduced motion", calm_page.get_by_test_id("harvard-chase").count() == 0)
        calm.close()
        browser.close()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(headless="--headless" in sys.argv))
