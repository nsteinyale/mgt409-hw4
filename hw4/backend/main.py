"""Campus Customs API.

A FastAPI app that reads the shop database and serves products, product images,
customer accounts (signup, login, logout), and the shopping chatbot (agent.py)
to the React front end.

Run from the backend folder:
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import re
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded

from agent import run_chat
from auth import (
    DUMMY_HASH,
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    create_session_token,
    make_password_hash,
    read_session_token,
    verify_password,
)
from models import (
    MAX_HISTORY_MESSAGES,
    AgentReply,
    ChatHistory,
    ChatMessage,
    ChatReply,
    ChatRequest,
    FactCheckInfo,
    PageResults,
    ProductCard,
    SavedMessage,
    SizeRequest,
    WaitlistEntry,
    WaitlistRequest,
)
from safety import redact_pii
from tools import (
    DB_PATH,
    IMAGES_DIR,
    AgentDeps,
    Customer,
    LookupFailed,
    add_to_waitlist,
    describe_page,
    normalize_size,
    read_db,
    save_preferred_size,
    sizes_for,
)

logger = logging.getLogger("campus_customs")

HISTORY_PAGE_SIZE = 50  # messages shown when a customer reopens the chat

# The data pack (campus_customs.db + products/) is found by tools.find_data_dir()
if not DB_PATH.is_file() or not IMAGES_DIR.is_dir():
    raise RuntimeError(
        f"Campus Customs data pack not found (looked for {DB_PATH}). Unzip data.zip inside the hw4 folder "
        "so you have hw4/data/campus_customs.db and hw4/data/products/, or set CAMPUS_CUSTOMS_DATA to that folder."
    )

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: index chat history by customer, so loading their latest messages stays fast as the table grows.
    # Also create the two Problem 9 tables (saved sizes, back-in-stock waitlist) if they don't exist yet.
    with closing(get_db()) as conn, conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS customer_preferences (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                preferred_size TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS stock_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                product_id TEXT NOT NULL REFERENCES catalogue(product_id),
                size TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, product_id, size)
            )"""
        )
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)

# The Vite dev server runs on a different port, so allow it to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Product photos are served at /images/<file>.jpg
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def product_from_row(row: sqlite3.Row) -> dict:
    """Turn a catalogue row into the JSON shape the front end uses."""
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"] or "[]"),
        "search_tags": json.loads(row["search_tags"] or "[]"),
        # Database stores "products/<file>.jpg"; the API serves it at /images/<file>.jpg
        "image_url": "/images/" + Path(row["image_file_path"]).name,
        "price": row["price"],
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/products")
def list_products() -> list[dict]:
    with closing(get_db()) as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock = {
            r["product_id"]: r["total"]
            for r in conn.execute(
                "SELECT product_id, SUM(quantity) AS total FROM inventory GROUP BY product_id"
            )
        }
    return [{**product_from_row(r), "in_stock": stock.get(r["product_id"], 0) > 0} for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with closing(get_db()) as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    sizes = sorted(
        ({"size": r["size"], "quantity": r["quantity"]} for r in inventory),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER),
    )
    product = product_from_row(row)
    product["sizes"] = sizes
    product["in_stock"] = any(s["quantity"] > 0 for s in sizes)
    return product


# ---- Accounts ---------------------------------------------------------------

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def preferred_size_for(user_id: int) -> str | None:
    with closing(get_db()) as conn:
        row = conn.execute("SELECT preferred_size FROM customer_preferences WHERE user_id = ?", (user_id,)).fetchone()
    return row["preferred_size"] if row else None


def public_user(row: sqlite3.Row) -> dict:
    """The user fields that are safe to send to the browser (never the password hash)."""
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "name": row["name"],
        "email": row["email"],
        "preferred_size": preferred_size_for(row["id"]),
    }


def start_session(response: Response, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=SESSION_MAX_AGE,
        httponly=True,  # JavaScript (and any injected script) can't read it
        samesite="lax",  # not sent on cross-site form posts
        secure=False,  # local development runs on http; set True behind https
    )


def find_user_by_email(conn: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()


@app.post("/api/signup", status_code=201)
def signup(body: SignupRequest, response: Response) -> dict:
    first_name = body.first_name.strip()
    last_name = body.last_name.strip()
    email = body.email.strip().lower()

    if not first_name or not last_name:
        raise HTTPException(status_code=400, detail="Enter your first and last name.")
    if len(first_name) > 50 or len(last_name) > 50:
        raise HTTPException(status_code=400, detail="Names must be 50 characters or fewer.")
    if not EMAIL_PATTERN.match(email) or len(email) > 254:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if not MIN_PASSWORD_LENGTH <= len(body.password) <= MAX_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Passwords must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters.",
        )

    with closing(get_db()) as conn:
        if find_user_by_email(conn, email):
            raise HTTPException(status_code=409, detail="An account with that email already exists. Try logging in.")
        try:
            with conn:  # commits the insert
                cursor = conn.execute(
                    "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
                    (f"{first_name} {last_name}", email, make_password_hash(body.password), first_name, last_name),
                )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with that email already exists. Try logging in.")
        user = conn.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()

    start_session(response, user["id"])
    return public_user(user)


@app.post("/api/login")
def login(body: LoginRequest, response: Response) -> dict:
    email = body.email.strip().lower()
    with closing(get_db()) as conn:
        user = find_user_by_email(conn, email)

    # Always run one hash check, even for unknown emails, so timing doesn't reveal which emails exist.
    stored = user["password_hash"] if user else DUMMY_HASH
    if not verify_password(body.password, stored) or user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    start_session(response, user["id"])
    return public_user(user)


@app.post("/api/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, samesite="lax")
    return {"ok": True}


@app.get("/api/me")
def me(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    user = current_user(session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    return public_user(user)


# ---- Chatbot -----------------------------------------------------------------


def current_user(session: str | None) -> sqlite3.Row | None:
    user_id = read_session_token(session)
    if user_id is None:
        return None
    with closing(get_db()) as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def short_text(text: str, limit: int = 100) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Build cards from the database, so the model can't invent a product, price, image, or stock."""
    unique_ids = list(dict.fromkeys(product_ids))
    if not unique_ids:
        return []
    with closing(read_db()) as conn:
        rows = {
            r["product_id"]: r
            for r in conn.execute(
                f"SELECT * FROM catalogue WHERE product_id IN ({','.join('?' * len(unique_ids))})", unique_ids
            )
        }
        cards = []
        for pid in unique_ids:  # keep the given order; silently drop IDs that don't exist
            if pid not in rows:
                continue
            p = product_from_row(rows[pid])
            in_stock = [s.size for s in sizes_for(conn, pid) if s.in_stock]
            cards.append(
                ProductCard(
                    product_id=pid,
                    name=p["name"],
                    price=p["price"],
                    image_url=p["image_url"],
                    garment_type=p["garment_type"],
                    short_description=short_text(p["description"]),
                    sizes_in_stock=in_stock,
                    in_stock=bool(in_stock),
                )
            )
    return cards


def page_results(output: AgentReply, deps: AgentDeps) -> PageResults | None:
    """The chat-to-page contract: if the agent asked to update the page, send its latest search matches."""
    search = deps.last_search
    if not output.update_page or search is None or not search.product_ids:
        return None
    return PageResults(
        title=(output.results_title or search.query).strip(),
        query=search.query,
        total_matches=search.total_matches,
        products=product_cards(search.product_ids),
    )


def customer_from_row(user: sqlite3.Row) -> Customer:
    return Customer(
        id=user["id"],
        first_name=user["first_name"] or user["name"].split(" ")[0],
        last_name=user["last_name"] or "",
        email=user["email"],
        member_since=(user["created_at"] or "")[:10],
        preferred_size=preferred_size_for(user["id"]),
    )


def load_history(conn: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    """The customer's most recent saved messages, oldest first."""
    rows = conn.execute(
        "SELECT id, role, content, products_json, created_at FROM chat_messages "
        "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return list(reversed(rows))


def saved_product_ids(products_json: str | None) -> list[str]:
    """Product IDs from a saved message (works for the seed data's format and ours)."""
    try:
        items = json.loads(products_json) if products_json else []
        return [item["product_id"] for item in items if isinstance(item, dict) and "product_id" in item]
    except (ValueError, TypeError):
        return []


def save_exchange(user_id: int, message: str, reply: ChatReply) -> None:
    """Store the customer's message and the assistant's reply together (one transaction)."""
    products = json.dumps([card.model_dump() for card in reply.products]) if reply.products else None
    with closing(get_db()) as conn, conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply.reply, products),
        )


@app.get("/api/chat/history")
def chat_history(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> ChatHistory:
    """A logged-in customer's saved chat, so the widget can show it when they return. Guests get 401."""
    user = current_user(session)
    if user is None:
        raise HTTPException(status_code=401, detail="Log in to see your saved chat.")
    with closing(get_db()) as conn:
        rows = load_history(conn, user["id"], HISTORY_PAGE_SIZE)
    return ChatHistory(
        messages=[
            SavedMessage(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                # Rebuild cards from today's catalogue so prices and stock are current
                products=product_cards(saved_product_ids(r["products_json"])),
                created_at=r["created_at"],
            )
            for r in rows
            if r["role"] in ("user", "assistant")
        ]
    )


@app.delete("/api/chat/history")
def clear_chat_history(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    user = current_user(session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    with closing(get_db()) as conn, conn:
        deleted = conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user["id"],)).rowcount
    return {"deleted": deleted}


@app.post("/api/chat")
async def chat(body: ChatRequest, session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> ChatReply:
    user = current_user(session)
    # Safety: strip card numbers, emails, phone numbers, passwords, etc. before the model sees the
    # message, before it's saved, and before it's audited (safety.py)
    message, pii_removed = redact_pii(body.message.strip())
    deps = AgentDeps(
        customer=customer_from_row(user) if user else None,
        page_description=describe_page(body.page),
        pii_removed=pii_removed,
    )

    if user:
        # Logged in: the conversation comes from the database, not from the browser
        with closing(get_db()) as conn:
            rows = load_history(conn, user["id"], MAX_HISTORY_MESSAGES)
        history = [ChatMessage(role=r["role"], content=r["content"]) for r in rows if r["role"] in ("user", "assistant")]
    else:
        # Guest: use what's on screen in the chat window (redacted too); nothing is saved
        history = [ChatMessage(role=m.role, content=redact_pii(m.content)[0]) for m in body.history]

    try:
        output = await run_chat(message, history, deps)
    except UsageLimitExceeded:
        return ChatReply(reply="Sorry, that question took me too many steps. Could you ask it a simpler way?")
    except UnexpectedModelBehavior:
        # The fact-check rejected the reply more times than allowed: never show an unverified answer.
        logger.warning("Reply failed the fact-check after retries")
        return ChatReply(
            reply="Sorry, I couldn't double-check those details just now. The product page always shows the current price and stock."
        )
    except ModelHTTPError as e:
        if "content_filter" in str(e.body):
            # The model provider's safety filter blocked the message (e.g. a jailbreak attempt).
            # Not saved to history, so it can't trip the filter again on every later message.
            logger.warning("Chat message blocked by the model provider's content filter")
            return ChatReply(reply="Sorry, I can't help with that. I'm here to help you find Yale gear at Campus Customs!")
        logger.exception("Chat agent failed")
        raise HTTPException(status_code=502, detail="The shopping assistant is unavailable right now. Try again in a moment.")
    except Exception:
        # Log the details on the server only; never send errors (which could include config) to the browser.
        logger.exception("Chat agent failed")
        raise HTTPException(status_code=502, detail="The shopping assistant is unavailable right now. Try again in a moment.")

    reply = ChatReply(
        reply=output.reply,
        products=product_cards(output.product_ids),
        page_results=page_results(output, deps),
        fact_check=FactCheckInfo(facts_checked=deps.facts_checked, corrections=deps.fact_corrections),
        preferred_size=deps.customer.preferred_size if deps.customer else None,
    )
    if user:
        save_exchange(user["id"], message, reply)
    return reply


# ---- Saved size (opt-in) ----------------------------------------------------------------


def require_user(session: str | None) -> sqlite3.Row:
    user = current_user(session)
    if user is None:
        raise HTTPException(status_code=401, detail="Log in first.")
    return user


@app.put("/api/me/size")
def set_my_size(body: SizeRequest, session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    user = require_user(session)
    try:
        size = normalize_size(body.size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if size is None:
        raise HTTPException(status_code=400, detail="Pick a size.")
    save_preferred_size(user["id"], size)
    return {"preferred_size": size}


@app.delete("/api/me/size")
def forget_my_size_route(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    user = require_user(session)
    save_preferred_size(user["id"], None)
    return {"preferred_size": None}


# ---- Back-in-stock waitlist --------------------------------------------------------------


@app.get("/api/waitlist")
def my_waitlist(session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> list[WaitlistEntry]:
    user = require_user(session)
    with closing(get_db()) as conn:
        rows = conn.execute(
            """SELECT r.product_id, c.name, r.size, r.created_at, COALESCE(i.quantity, 0) AS quantity
               FROM stock_requests r
               JOIN catalogue c ON c.product_id = r.product_id
               LEFT JOIN inventory i ON i.product_id = r.product_id AND i.size = r.size
               WHERE r.user_id = ? ORDER BY r.id DESC""",
            (user["id"],),
        ).fetchall()
    return [
        WaitlistEntry(
            product_id=r["product_id"],
            name=r["name"],
            size=r["size"],
            created_at=r["created_at"],
            back_in_stock=r["quantity"] > 0,
        )
        for r in rows
    ]


@app.post("/api/waitlist", status_code=201)
def join_waitlist_route(body: WaitlistRequest, session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    user = require_user(session)
    result = add_to_waitlist(user["id"], body.product_id, body.size)
    if isinstance(result, LookupFailed):
        raise HTTPException(status_code=400, detail=result.error)
    return result.model_dump()


@app.delete("/api/waitlist/{product_id}/{size}")
def leave_waitlist(product_id: str, size: str, session: str | None = Cookie(default=None, alias=SESSION_COOKIE)) -> dict:
    user = require_user(session)
    with closing(get_db()) as conn, conn:
        deleted = conn.execute(
            "DELETE FROM stock_requests WHERE user_id = ? AND product_id = ? AND size = ?",
            (user["id"], product_id, size),
        ).rowcount
    return {"deleted": deleted}
