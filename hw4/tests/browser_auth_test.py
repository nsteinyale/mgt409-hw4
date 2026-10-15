"""Real-browser test of create account and login (Problem 4).

Drives Chromium with real mouse clicks and keystrokes through the running site,
saving a screenshot at each step plus a video to output/browser_proof/.

Needs both servers running (API on :8000, site on :5180). From the HOME WORK 4 folder:
    ../.venv/Scripts/python.exe tests/browser_auth_test.py          # watch it in a window
    ../.venv/Scripts/python.exe tests/browser_auth_test.py --headless
"""

import secrets
import sqlite3
import sys
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

SITE = "http://localhost:5180"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "browser_proof"
from _paths import DB_PATH  # noqa: E402  (finds data/ or data/data/)

# Seeded test account (from the homework's starter database)
SEED_EMAIL = "test@campuscustoms.yale.edu"
SEED_PASSWORD = "password"

# A brand new account is made on every run, with a fresh email and a random password
NEW_FIRST, NEW_LAST = "Eli", "Yale"
NEW_EMAIL = f"eli.yale.{int(time.time())}@example.com"  # example.com is reserved for testing
NEW_PASSWORD = secrets.token_urlsafe(12)

results: list[tuple[str, bool]] = []


def check(name: str, passed: bool) -> None:
    results.append((name, passed))
    print(f"[{'PASS' if passed else 'FAIL'}] {name}")


def main(headless: bool) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    step = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, slow_mo=0 if headless else 120)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, record_video_dir=str(OUT))
        page = context.new_page()
        nav = page.locator(".nav-account")

        def shot(label: str) -> None:
            nonlocal step
            step += 1
            page.screenshot(path=str(OUT / f"{step:02d}-{label}.png"))

        def submit_login(email: str, password: str) -> None:
            page.get_by_label("Email").click()
            page.get_by_label("Email").fill("")
            page.get_by_label("Email").press_sequentially(email, delay=15)
            page.get_by_label("Password").click()
            page.get_by_label("Password").fill("")
            page.get_by_label("Password").press_sequentially(password, delay=15)
            page.get_by_role("button", name="Log in").click()

        # 1. Start logged out
        page.goto(SITE)
        expect(nav).to_contain_text("Log in")
        check("Site loads logged out", True)
        shot("home-logged-out")

        # 2. Seeded test user, wrong password
        nav.get_by_role("link", name="Log in").click()
        submit_login(SEED_EMAIL, "not-the-password")
        error = page.locator(".form-error")
        expect(error).to_have_text("Incorrect email or password.")
        check("Wrong password is rejected", page.url.endswith("/login"))
        shot("test-user-wrong-password")

        # 3. Seeded test user, right password
        submit_login(SEED_EMAIL, SEED_PASSWORD)
        expect(nav).to_contain_text("Hi, Test")
        check("Seeded test user logs in", True)
        shot("test-user-logged-in")

        # 4. Session survives a reload, and the cookie is HttpOnly (hidden from JavaScript)
        page.reload()
        expect(nav).to_contain_text("Hi, Test")
        cookie = next((c for c in context.cookies() if c["name"] == "cc_session"), None)
        check("Still logged in after reload", True)
        check("Session cookie is HttpOnly", bool(cookie and cookie["httpOnly"]))
        check("JavaScript cannot read the session cookie", "cc_session" not in page.evaluate("document.cookie"))
        shot("test-user-after-reload")

        # 5. Log out
        nav.get_by_role("button", name="Log out").click()
        expect(nav).to_contain_text("Log in")
        check("Log out works", True)

        # 6. Create a brand new account
        nav.get_by_role("link", name="Create account").click()
        page.get_by_label("First name").press_sequentially(NEW_FIRST, delay=15)
        page.get_by_label("Last name").press_sequentially(NEW_LAST, delay=15)
        page.get_by_label("Email").press_sequentially(NEW_EMAIL, delay=15)
        page.get_by_label("Password", exact=True).press_sequentially(NEW_PASSWORD, delay=15)
        page.get_by_label("Confirm password").press_sequentially(NEW_PASSWORD, delay=15)
        shot("create-account-filled")
        page.get_by_role("button", name="Create account").click()
        expect(nav).to_contain_text(f"Hi, {NEW_FIRST}")
        check("New account is created and logged in", True)
        shot("new-account-created")

        # 7. Log out, then log back in as the new account
        nav.get_by_role("button", name="Log out").click()
        expect(nav).to_contain_text("Log in")
        nav.get_by_role("link", name="Log in").click()
        submit_login(NEW_EMAIL, NEW_PASSWORD)
        expect(nav).to_contain_text(f"Hi, {NEW_FIRST}")
        check("New account logs back in with its password", True)
        shot("new-account-logged-back-in")

        video_path = page.video.path() if page.video else None
        context.close()
        browser.close()

    # 8. The new row is in the users table with a PBKDF2 hash, not the password
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        row = conn.execute(
            "SELECT id, name, email, password_hash FROM users WHERE email = ?", (NEW_EMAIL,)
        ).fetchone()
    check("New user saved in the users table", row is not None)
    if row:
        print(f"       users row: id={row[0]}, name={row[1]!r}, email={row[2]!r}, hash={row[3][:36]}...")
        check("Stored as pbkdf2_sha256$salt$hash", row[3].startswith("pbkdf2_sha256$") and row[3].count("$") == 2)
        check("Plain password is not stored", NEW_PASSWORD not in row[3])

    if video_path:
        final = OUT / "login-flow.webm"
        final.unlink(missing_ok=True)
        Path(video_path).rename(final)
        print(f"Video: {final}")
    print(f"Screenshots: {OUT}")

    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(headless="--headless" in sys.argv))
