"""Tools the Campus Customs agent can call, plus the per-request context they share.

Product, price, and stock tools read campus_customs.db directly (read-only), so every
fact the agent quotes comes from the database rather than the model's memory.
"""

import json
import os
import re
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    LookupFailed,
    PageContext,
    ProductDetails,
    ProductSearchResult,
    ProductSummary,
    SavedPreference,
    SimilarProduct,
    SimilarProductsResult,
    SizeStock,
    StockCheck,
    WaitlistResult,
)

def find_data_dir() -> Path:
    """Where the data pack lives: $CAMPUS_CUSTOMS_DATA, else hw4/data/ (data.zip unzipped in hw4/),
    else hw4/data/data/ (data.zip unzipped into a folder named data)."""
    root = Path(__file__).resolve().parent.parent
    candidates = [Path(p) for p in [os.environ.get("CAMPUS_CUSTOMS_DATA")] if p] + [root / "data", root / "data" / "data"]
    return next((d for d in candidates if (d / "campus_customs.db").is_file()), candidates[0])


DATA_DIR = find_data_dir()
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_SEARCH_RESULTS = 8  # products the model sees per search
MAX_PAGE_RESULTS = 30  # products the website can show on the page per search


@dataclass
class SearchCapture:
    """The full result of the latest search_products call, kept for the website."""

    query: str
    total_matches: int
    product_ids: list[str] = field(default_factory=list)


@dataclass
class Customer:
    """The logged-in shopper, as the agent sees them. Never includes the password hash."""

    id: int
    first_name: str
    last_name: str
    email: str
    member_since: str  # date the account was created, YYYY-MM-DD
    preferred_size: str | None = None  # only if the customer asked us to remember it


@dataclass
class AgentDeps:
    """Context for one chat request, available to tools as ctx.deps and to the dynamic instructions."""

    customer: Customer | None = None  # None for guests
    # Plain-text description of what's on the shopper's screen, built by describe_page()
    page_description: str | None = None
    # Set by search_products / find_similar_products. If the agent says update_page, main.py sends
    # these matches to the website.
    last_search: SearchCapture | None = None
    # Filled in by the fact-check output validator in agent.py
    facts_checked: int = 0
    fact_corrections: int = 0
    # Kinds of personal details removed from the shopper's message before the agent saw it (safety.py)
    pii_removed: list[str] = field(default_factory=list)


# ---- Database helpers ---------------------------------------------------------


def write_db() -> sqlite3.Connection:
    """Read-write connection, used ONLY by the preference and waitlist tools (never for catalogue or stock)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def read_db() -> sqlite3.Connection:
    """Open the shop database read-only, so tools can never change prices or stock."""
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def sizes_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    sizes = [SizeStock(size=r["size"], quantity=r["quantity"], in_stock=r["quantity"] > 0) for r in rows]
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else len(SIZE_ORDER))


SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx large": "XXL", "double xl": "XXL", "extra extra large": "XXL",
}


def normalize_size(size: str | None) -> str | None:
    """Turn 'medium', 'Med', 'm' into 'M'. Returns None for an empty size, raises ValueError for an unknown one."""
    if size is None or not size.strip():
        return None
    key = re.sub(r"[-_.]", " ", size.strip().lower())
    key = re.sub(r"\s+", " ", key)
    if key in SIZE_ALIASES:
        return SIZE_ALIASES[key]
    raise ValueError(f"Unknown size '{size}'. Sizes are {', '.join(SIZE_ORDER)}.")


# ---- Search helpers -----------------------------------------------------------

STOPWORDS = {
    "a", "an", "and", "any", "do", "for", "have", "i", "in", "is", "me", "of", "on", "or", "show",
    "some", "the", "to", "with", "you", "your", "yale", "gear", "item", "items", "something", "size",
}
# Shopper words -> the word stem used in the catalogue
SYNONYMS = {
    "hoodie": "hood", "hoody": "hood", "hooded": "hood", "sweatshirt": "sweatshirt",
    "tee": "shirt", "tshirt": "shirt", "t": "shirt",
    "quarter": "quarter", "quarterzip": "quarter", "zip": "zip",
    "fleece": "fleece", "jacket": "jacket", "crew": "crew", "crewneck": "crewneck",
    "grey": "gray", "blue": "blue",
}


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def keywords(query: str) -> list[str]:
    words = []
    for w in normalize_text(query).split():
        if w in STOPWORDS or w in SIZE_ALIASES:  # sizes belong in the size argument, not the keywords
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # hoodies -> hoodie, crewnecks -> crewneck
        words.append(SYNONYMS.get(w, w))
    return list(dict.fromkeys(words))


def haystack(row: sqlite3.Row) -> str:
    parts = [row["name"], row["garment_type"], row["description"], " ".join(json.loads(row["colors"] or "[]")),
             " ".join(json.loads(row["search_tags"] or "[]"))]
    return normalize_text(" ".join(parts))


def matches(word: str, text: str) -> bool:
    # Match at the start of a word, so "hood" finds "hoodie" and "hooded" but "tan" doesn't match "standing".
    return re.search(rf"\b{re.escape(word)}", text) is not None


# ---- Tools ------------------------------------------------------------------------


def search_products(
    ctx: RunContext[AgentDeps],
    query: str,
    size: str | None = None,
    max_price: float | None = None,
    in_stock_only: bool = False,
) -> ProductSearchResult | LookupFailed:
    """Search the Campus Customs catalogue. Use this to find products before talking about them.

    Args:
        query: Short keywords about the item, e.g. "navy hoodie", "Saybrook", "baseball crewneck", "fleece".
            Put sizes and prices in the other arguments, not here.
        size: Optional size the shopper wants (XS, S, M, L, XL, XXL, or words like "medium").
            Results then include how many are in stock in that size.
        max_price: Optional highest price in dollars.
        in_stock_only: If true, only return items that have stock (in the requested size, if one is given).
    """
    try:
        wanted_size = normalize_size(size)
    except ValueError as e:
        return LookupFailed(error=str(e))

    words = keywords(query)
    with closing(read_db()) as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        scored = []
        for row in rows:
            if max_price is not None and row["price"] > max_price:
                continue
            text = haystack(row)
            score = sum(matches(w, text) for w in words) if words else 0
            scored.append((score, row))

        best = max((s for s, _ in scored), default=0)
        exact = bool(words) and best == len(words)
        if not words:
            hits = [row for _, row in scored]
        elif best == 0:
            hits = []
        else:
            # Everything that matched every keyword; if nothing did, the closest partial matches.
            hits = [row for s, row in sorted(scored, key=lambda x: -x[0]) if s == best]
        unmatched = [w for w in words if not any(matches(w, haystack(row)) for row in hits)]

        products = []
        for row in hits:
            sizes = sizes_for(conn, row["product_id"])
            size_qty = next((s.quantity for s in sizes if s.size == wanted_size), 0) if wanted_size else None
            total = sum(s.quantity for s in sizes)
            if in_stock_only and ((size_qty or 0) == 0 if wanted_size else total == 0):
                continue
            products.append(
                ProductSummary(
                    product_id=row["product_id"],
                    name=row["name"],
                    garment_type=row["garment_type"],
                    price=row["price"],
                    colors=json.loads(row["colors"] or "[]"),
                    sizes_in_stock=[s.size for s in sizes if s.in_stock],
                    total_in_stock=total,
                    requested_size_quantity=size_qty,
                )
            )

    if ctx is not None:
        # Remember every match (not just the 8 the model sees) so the website can show them all.
        ctx.deps.last_search = SearchCapture(
            query=query,
            total_matches=len(products),
            product_ids=[p.product_id for p in products[:MAX_PAGE_RESULTS]],
        )

    return ProductSearchResult(
        query=query,
        total_matches=len(products),
        exact_match=exact,
        unmatched_keywords=unmatched,
        products=products[:MAX_SEARCH_RESULTS],
    )


def get_product_details(ctx: RunContext[AgentDeps], product_id: str) -> ProductDetails | LookupFailed:
    """Get the full record for one product: description, price, colors, and stock for every size.

    Args:
        product_id: The product_id from search_products, e.g. "basic-hoodie-big-yale".
    """
    with closing(read_db()) as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return LookupFailed(error=f"No product with id '{product_id}'. Use search_products to find the right id.")
        sizes = sizes_for(conn, product_id)
    return ProductDetails(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        price=row["price"],
        colors=json.loads(row["colors"] or "[]"),
        sizes=sizes,
        total_in_stock=sum(s.quantity for s in sizes),
    )


def check_stock(ctx: RunContext[AgentDeps], product_id: str, size: str | None = None) -> StockCheck | LookupFailed:
    """Check how many units of a product are in stock, for one size or all sizes. Always use this before
    answering a stock or availability question.

    Args:
        product_id: The product_id from search_products.
        size: Optional size (XS, S, M, L, XL, XXL, or words like "medium"). Leave empty to check every size.
    """
    try:
        wanted_size = normalize_size(size)
    except ValueError as e:
        return LookupFailed(error=str(e))
    with closing(read_db()) as conn:
        row = conn.execute("SELECT product_id, name, price FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return LookupFailed(error=f"No product with id '{product_id}'. Use search_products to find the right id.")
        sizes = sizes_for(conn, product_id)
    quantity = (
        next((s.quantity for s in sizes if s.size == wanted_size), 0) if wanted_size else sum(s.quantity for s in sizes)
    )
    return StockCheck(
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
        size=wanted_size,
        quantity=quantity,
        in_stock=quantity > 0,
        sizes=sizes,
    )


# ---- Similar products ("a gray one", "something cheaper") -------------------------

# Color families, so "gray" also finds "heather gray" and "charcoal", and "blue" finds "navy".
COLOR_FAMILIES = {
    "gray": ["gray", "grey", "heather", "charcoal", "silver"],
    "grey": ["gray", "grey", "heather", "charcoal", "silver"],
    "navy": ["navy"],
    "blue": ["blue", "navy", "royal"],
    "light blue": ["light blue"],
    "white": ["white", "ivory", "cream"],
    "cream": ["cream", "ivory"],
    "black": ["black"],
    "red": ["red"],
    "green": ["green"],
    "yellow": ["yellow", "gold"],
    "gold": ["gold", "yellow"],
    "pink": ["pink", "rose"],
    "coral": ["coral"],
    "orange": ["orange", "coral"],
}

# Themes that make two products "the same kind of gear" beyond garment type
THEME_WORDS = [
    "benjamin franklin", "berkeley", "branford", "davenport", "ezra stiles", "grace hopper", "jonathan edwards",
    "morse", "pauli murray", "pierson", "saybrook", "silliman", "timothy dwight", "trumbull",
    "baseball", "basketball", "football", "field hockey", "hockey", "soccer", "tennis", "track", "diving",
    "swimming", "golf", "volleyball", "lacrosse", "fencing", "sailing", "squash",
    "mom", "dad", "grandma", "grandpa", "aunt", "uncle", "brother", "sister", "cousin",
    "architecture", "school of art", "engineering", "management", "medicine", "music", "nursing",
    "public health", "law school", "divinity", "forest", "bulldog", "harvard",
]


def garment_category(garment_type: str) -> str:
    """Group the catalogue's inconsistent garment_type labels (same rules as the website's type filter)."""
    t = garment_type.lower()
    if "t-shirt" in t:
        return "T-shirt"
    if "quarter-zip" in t:
        return "quarter-zip"
    if "hood" in t:
        return "hoodie"
    if "jacket" in t or "fleece" in t:
        return "jacket/fleece"
    if "long-sleeve" in t:
        return "long-sleeve shirt"
    return "crewneck"


def themes(name: str) -> set[str]:
    lower = name.lower()
    return {w for w in THEME_WORDS if re.search(rf"\b{re.escape(w)}\b", lower)}


def color_matches(requested: str, colors: list[str]) -> bool:
    key = requested.lower().strip()
    family = COLOR_FAMILIES.get(key, [key])
    return any(re.search(rf"\b{re.escape(f)}\b", c.lower()) for c in colors for f in family)


def tag_words(row: sqlite3.Row) -> set[str]:
    return set(keywords(row["name"] + " " + " ".join(json.loads(row["search_tags"] or "[]"))))


def find_similar_products(
    ctx: RunContext[AgentDeps],
    product_id: str,
    color: str | None = None,
    max_price: float | None = None,
    cheaper: bool = False,
    size: str | None = None,
) -> SimilarProductsResult | LookupFailed:
    """Find catalogue items similar to one product, optionally in another color, cheaper, or in stock in a size.
    Use for "do you have this in gray?", "I want a gray one", "something like this but cheaper", or
    "this is sold out in my size, what else is there?".

    Args:
        product_id: The product to compare against (usually the one on the shopper's screen).
        color: Optional color the shopper wants, e.g. "gray", "navy", "white".
        max_price: Optional highest price in dollars.
        cheaper: If true, only items cheaper than the original.
        size: Optional size that must be in stock (XS, S, M, L, XL, XXL, or words like "medium").
    """
    try:
        wanted_size = normalize_size(size)
    except ValueError as e:
        return LookupFailed(error=str(e))

    with closing(read_db()) as conn:
        base = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if base is None:
            return LookupFailed(error=f"No product with id '{product_id}'. Use search_products to find the right id.")
        base_colors = json.loads(base["colors"] or "[]")
        base_category = garment_category(base["garment_type"])
        base_themes = themes(base["name"])
        base_words = tag_words(base)

        scored = []
        for row in conn.execute("SELECT * FROM catalogue WHERE product_id != ?", (product_id,)).fetchall():
            colors = json.loads(row["colors"] or "[]")
            if color and not color_matches(color, colors):
                continue
            if max_price is not None and row["price"] > max_price:
                continue
            if cheaper and row["price"] >= base["price"]:
                continue
            sizes = sizes_for(conn, row["product_id"])
            total = sum(s.quantity for s in sizes)
            size_qty = next((s.quantity for s in sizes if s.size == wanted_size), 0) if wanted_size else None
            if total == 0 or (wanted_size and not size_qty):
                continue

            score, reasons = 0, []
            if garment_category(row["garment_type"]) == base_category:
                score += 4
                reasons.append(f"same type ({base_category})")
            shared = base_themes & themes(row["name"])
            if shared:
                score += 3
                reasons.append("also " + ", ".join(sorted(t.title() for t in shared)))
            if score < 3:  # must share the garment type or a theme to count as "similar"
                continue
            score += min(len(base_words & tag_words(row)), 3)
            if abs(row["price"] - base["price"]) <= 10:
                score += 1
            if color:
                reasons.append(f"comes in {color}")
            if row["price"] < base["price"]:
                reasons.append(f"${base['price'] - row['price']:.2f} cheaper")
            if wanted_size:
                reasons.append(f"{size_qty} in stock in {wanted_size}")
            scored.append(
                (
                    -score,
                    row["price"],
                    SimilarProduct(
                        product_id=row["product_id"],
                        name=row["name"],
                        garment_type=row["garment_type"],
                        price=row["price"],
                        colors=colors,
                        sizes_in_stock=[s.size for s in sizes if s.in_stock],
                        total_in_stock=total,
                        requested_size_quantity=size_qty,
                        match_reasons=reasons,
                    ),
                )
            )

    scored.sort(key=lambda x: (x[0], x[1]))
    products = [p for _, _, p in scored]
    if ctx is not None:
        # Like search_products: remember the full list so the website can show it on the page
        ctx.deps.last_search = SearchCapture(
            query=f"like {base['name']}" + (f" in {color}" if color else ""),
            total_matches=len(products),
            product_ids=[p.product_id for p in products[:MAX_PAGE_RESULTS]],
        )
    return SimilarProductsResult(
        base_product_id=base["product_id"],
        base_name=base["name"],
        base_price=base["price"],
        base_colors=base_colors,
        requested_color=color,
        base_has_requested_color=color_matches(color, base_colors) if color else None,
        total_matches=len(products),
        products=products[:6],
    )


# ---- Fact-check (used by the output validator in agent.py) -----------------------

SIZE_TOKEN = r"(XXL|XL|XS|S|M|L|extra small|extra large|small|medium|large)"
PRICE_RE = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
STOCK_PATTERNS = [
    # "S (15 left)", "M (5)"
    re.compile(rf"\b{SIZE_TOKEN}\s*\((\d+)(?:\s+left)?\)", re.I),
    # "5 left in M", "12 in stock in XL", "2 in size L"
    re.compile(rf"\b(\d+)\s+(?:left\s+|in stock\s+|available\s+)?in\s+(?:size\s+)?{SIZE_TOKEN}\b", re.I),
]
OUT_OF_STOCK_RE = re.compile(rf"\b(?:out of stock|sold out)\s+in\s+(?:size\s+)?{SIZE_TOKEN}\b", re.I)
PRICE_REACH = 150  # a price must appear within this many characters after the product name to count as its price


def fact_check_reply(reply: str, product_ids: list[str], allowed_amounts: set[float]) -> tuple[int, list[str]]:
    """Check the prices and stock numbers written next to each product name in a reply against the database.

    Returns (number of facts checked, list of problems). allowed_amounts are dollar figures the shopper
    used themselves (e.g. a budget like "under $70"), which aren't product prices.
    """
    with closing(read_db()) as conn:
        catalogue = {r["name"].lower(): r for r in conn.execute("SELECT product_id, name, price FROM catalogue")}
        stock: dict[str, dict[str, int]] = {}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]

    problems = [f"product_ids contains '{pid}', which is not a real catalogue product" for pid in product_ids
                if pid not in {r["product_id"] for r in catalogue.values()}]

    # Find every product name mentioned, longest names first so "Champion Reverse Weave Hoodie 1" wins
    lower = reply.lower()
    mentions: list[tuple[int, int, sqlite3.Row]] = []
    for name in sorted(catalogue, key=len, reverse=True):
        for m in re.finditer(re.escape(name), lower):
            if not any(m.start() < end and start < m.end() for start, end, _ in mentions):
                mentions.append((m.start(), m.end(), catalogue[name]))
    mentions.sort(key=lambda x: x[0])

    checked = 0
    for i, (_, end, row) in enumerate(mentions):
        window = reply[end : mentions[i + 1][0] if i + 1 < len(mentions) else len(reply)]
        # The first dollar amount after the name (skipping the shopper's own budget figures) is its price
        amounts = [float(a) for a in PRICE_RE.findall(window[:PRICE_REACH])]
        amount = next((a for a in amounts if a not in allowed_amounts or a == row["price"]), None)
        if amount is not None:
            checked += 1
            if amount != row["price"]:
                problems.append(f"you wrote {row['name']} costs ${amount:.2f}, but the database price is ${row['price']:.2f}")
        sizes = stock.get(row["product_id"], {})
        for pattern in STOCK_PATTERNS:
            for m in pattern.finditer(window):
                size_text, qty_text = (m.group(1), m.group(2)) if pattern is STOCK_PATTERNS[0] else (m.group(2), m.group(1))
                size = normalize_size(size_text)
                if size in sizes:
                    checked += 1
                    if int(qty_text) != sizes[size]:
                        problems.append(f"you wrote {row['name']} has {qty_text} in {size}, but the database has {sizes[size]}")
        for m in OUT_OF_STOCK_RE.finditer(window):
            size = normalize_size(m.group(1))
            if size in sizes:
                checked += 1
                if sizes[size] > 0:
                    problems.append(f"you wrote {row['name']} is out of stock in {size}, but the database has {sizes[size]}")
    return checked, problems


# ---- Remember my size (opt-in) and back-in-stock waitlist ------------------------
# These are the only tools that write to the database, and only to the customer's own rows.


def remember_my_size(ctx: RunContext[AgentDeps], size: str) -> SavedPreference | LookupFailed:
    """Save the logged-in shopper's clothing size to their account. ONLY call this when the shopper
    explicitly asks you to remember their size, or says yes after you offer to.

    Args:
        size: XS, S, M, L, XL, XXL, or words like "medium".
    """
    c = ctx.deps.customer
    if c is None:
        return LookupFailed(error="Not logged in. Tell the shopper to log in or create an account to save a size.")
    try:
        normalized = normalize_size(size)
    except ValueError as e:
        return LookupFailed(error=str(e))
    if normalized is None:
        return LookupFailed(error="No size given.")
    save_preferred_size(c.id, normalized)
    c.preferred_size = normalized
    return SavedPreference(ok=True, preferred_size=normalized, message=f"Saved {normalized} as {c.first_name}'s size.")


def forget_my_size(ctx: RunContext[AgentDeps]) -> SavedPreference | LookupFailed:
    """Delete the logged-in shopper's saved size, when they ask you to forget it."""
    c = ctx.deps.customer
    if c is None:
        return LookupFailed(error="Not logged in.")
    save_preferred_size(c.id, None)
    c.preferred_size = None
    return SavedPreference(ok=True, preferred_size=None, message="Saved size removed.")


def save_preferred_size(user_id: int, size: str | None) -> None:
    with closing(write_db()) as conn, conn:
        if size is None:
            conn.execute("DELETE FROM customer_preferences WHERE user_id = ?", (user_id,))
        else:
            conn.execute(
                "INSERT INTO customer_preferences (user_id, preferred_size, updated_at) VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(user_id) DO UPDATE SET preferred_size = excluded.preferred_size, updated_at = excluded.updated_at",
                (user_id, size),
            )


def add_to_waitlist(user_id: int, product_id: str, size: str) -> WaitlistResult | LookupFailed:
    """Shared by the join_waitlist tool and the website's waitlist button."""
    try:
        normalized = normalize_size(size)
    except ValueError as e:
        return LookupFailed(error=str(e))
    if normalized is None:
        return LookupFailed(error="Pick a size to join the waitlist for.")
    with closing(write_db()) as conn, conn:
        row = conn.execute("SELECT product_id, name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return LookupFailed(error=f"No product with id '{product_id}'.")
        qty = conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", (product_id, normalized)
        ).fetchone()
        if qty and qty["quantity"] > 0:
            return LookupFailed(error=f"{row['name']} is in stock in {normalized} ({qty['quantity']} left), so no waitlist is needed.")
        conn.execute(
            "INSERT OR IGNORE INTO stock_requests (user_id, product_id, size) VALUES (?, ?, ?)",
            (user_id, product_id, normalized),
        )
    return WaitlistResult(
        ok=True,
        product_id=row["product_id"],
        name=row["name"],
        size=normalized,
        message="Added to the back-in-stock waitlist. The store uses waitlists to decide what to restock. "
        "No email is sent; the shopper can check the product page to see when it's back.",
    )


def join_waitlist(ctx: RunContext[AgentDeps], product_id: str, size: str) -> WaitlistResult | LookupFailed:
    """Add the logged-in shopper to the back-in-stock waitlist for a size that is OUT of stock. Only when they
    ask for it (e.g. "let me know when XL is back", "put me on the waitlist"). No email is sent.

    Args:
        product_id: The out-of-stock product.
        size: The out-of-stock size.
    """
    c = ctx.deps.customer
    if c is None:
        return LookupFailed(error="Not logged in. The shopper needs to log in to join a waitlist.")
    return add_to_waitlist(c.id, product_id, size)


# ---- Page context ---------------------------------------------------------------

PAGE_LABELS = {
    "home": "the home page",
    "catalogue": "the Products page (the catalogue)",
    "product": "a product page",
    "search_results": "the Products page showing search results from this chat",
    "about": "the About us page",
    "account": "the log in / create account page",
    "other": "a page on the site",
}


def clean(text: str, limit: int) -> str:
    """Flatten browser-supplied text to one short line so it can't pose as instructions."""
    return re.sub(r"\s+", " ", text).strip()[:limit]


def describe_page(page: PageContext | None) -> str | None:
    """Turn the browser's page context into a description for the agent.

    Product facts come from the database, looked up by ID; only the IDs, page type,
    size, and title come from the browser.
    """
    if page is None:
        return None
    lines = [f"The shopper is on {PAGE_LABELS[page.page_type]} ({clean(page.path, 120)})."]
    with closing(read_db()) as conn:
        if page.product_id:
            row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (page.product_id,)).fetchone()
            if row:
                colors = ", ".join(json.loads(row["colors"] or "[]")) or "not listed"
                in_stock = [s.size for s in sizes_for(conn, row["product_id"]) if s.in_stock]
                lines.append(
                    f'They are looking at "{row["name"]}" (product_id: {row["product_id"]}, {row["garment_type"]}, '
                    f'${row["price"]:.2f}, colors: {colors}, sizes in stock: {", ".join(in_stock) or "none"}). '
                    'When they say "this", "it", or "this one", they mean this product.'
                )
                try:
                    size = normalize_size(page.selected_size)
                except ValueError:
                    size = None
                if size:
                    lines.append(f"They have size {size} selected on the page.")
        if page.title:
            lines.append(f'The list on screen is titled "{clean(page.title, 80)}".')
        ids = [pid for pid in dict.fromkeys(page.product_ids) if pid != page.product_id][:12]
        if ids:
            rows = conn.execute(
                f"SELECT product_id, name, price FROM catalogue WHERE product_id IN ({','.join('?' * len(ids))})", ids
            ).fetchall()
            by_id = {r["product_id"]: r for r in rows}
            shown = [f'{by_id[i]["name"]} ({i}, ${by_id[i]["price"]:.2f})' for i in ids if i in by_id]
            if shown:
                lines.append(
                    "Products visible on screen, in order (\"these\", \"the first one\", etc. refer to them): "
                    + "; ".join(shown) + "."
                )
    return " ".join(lines)


def get_my_account(ctx: RunContext[AgentDeps]) -> dict[str, str] | LookupFailed:
    """Get the logged-in shopper's own account details (name, email, member since).
    Only use this when the shopper asks about their own account."""
    c = ctx.deps.customer
    if c is None:
        return LookupFailed(error="The shopper is not logged in.")
    return {"first_name": c.first_name, "last_name": c.last_name, "email": c.email, "member_since": c.member_since}


STORE_INFO = {
    "name": "Campus Customs (Yale Bulldog Blue)",
    "address": "57 Broadway, New Haven, CT",
    "sells": "Officially licensed Yale apparel: hoodies, crewnecks, quarter-zips, T-shirts, long-sleeve shirts, and fleece jackets",
    "collections": "Residential colleges, Yale sports teams, graduate and professional schools, and family gear (Yale Mom, Dad, Grandpa, and more)",
    "sizes": "XS, S, M, L, XL, XXL (stock varies by item and size)",
    "price_range": "$32 for T-shirts up to $98 for fleece and jackets",
    "website_help": "The Products page has search, a type filter, and collection buttons. Each product page shows sizes and stock.",
    "how_to_buy": "The website doesn't have online checkout yet. To buy, visit the store at 57 Broadway.",
    "chat_limits": "The assistant can't place orders, take payments, or change accounts.",
}


def get_store_info(ctx: RunContext[AgentDeps]) -> dict[str, str]:
    """Get basic facts about the Campus Customs store: address, what it sells, collections, sizes, and price range."""
    return STORE_INFO
