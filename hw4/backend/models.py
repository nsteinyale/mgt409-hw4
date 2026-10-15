"""Structured types shared by the API (main.py) and the agent (agent.py)."""

from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 1000
MAX_HISTORY_MESSAGES = 20


# ---- What the website sends -------------------------------------------------


class ChatMessage(BaseModel):
    """One earlier message in the conversation, as shown in the chat window."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


PageType = Literal["home", "catalogue", "product", "search_results", "about", "account", "other"]


class PageContext(BaseModel):
    """What the shopper is looking at when they send a message, so "this" and "these" make sense.

    Product names, prices, and colors are NOT sent by the browser; the backend looks them up
    from the IDs, so a tampered request can't feed the agent fake product facts.
    """

    path: str = Field(default="/", max_length=200)
    page_type: PageType = "other"
    product_id: str | None = Field(default=None, max_length=100, description="The product on a product page")
    selected_size: str | None = Field(default=None, max_length=10, description="Size picked on the product page")
    title: str | None = Field(default=None, max_length=120, description="Heading of a results or filtered list")
    product_ids: list[str] = Field(default_factory=list, max_length=12, description="Products visible on screen, in order")


class ChatRequest(BaseModel):
    """POST /api/chat body: the new message, recent history (used for guests), and page context."""

    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ChatMessage] = Field(default_factory=list, max_length=MAX_HISTORY_MESSAGES)
    page: PageContext | None = None


# ---- What the tools return (read straight from campus_customs.db) ------------


class SizeStock(BaseModel):
    """Units on hand for one size of one product (inventory table)."""

    size: str
    quantity: int
    in_stock: bool


class ProductSummary(BaseModel):
    """One search hit: enough to recommend an item and decide whether to look closer."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]
    sizes_in_stock: list[str]
    total_in_stock: int
    requested_size_quantity: int | None = Field(
        default=None, description="Units in the size the shopper asked for, when a size was given"
    )


class ProductSearchResult(BaseModel):
    """search_products output."""

    query: str
    total_matches: int
    exact_match: bool = Field(description="False when nothing matched every keyword and these are the closest partial matches")
    unmatched_keywords: list[str] = Field(
        default_factory=list, description="Keywords no returned product matched, e.g. a color we don't carry"
    )
    products: list[ProductSummary]


class ProductDetails(BaseModel):
    """get_product_details output: everything the product page shows."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str]
    sizes: list[SizeStock]
    total_in_stock: int


class StockCheck(BaseModel):
    """check_stock output for one product, optionally one size."""

    product_id: str
    name: str
    price: float
    size: str | None = Field(description="The size checked, or None when all sizes were checked")
    quantity: int = Field(description="Units on hand: for the size checked, or across all sizes")
    in_stock: bool
    sizes: list[SizeStock] = Field(description="Every size with its quantity, so out-of-stock answers can offer other sizes")


class SimilarProduct(ProductSummary):
    """One alternative from find_similar_products, with the reasons it was picked."""

    match_reasons: list[str] = Field(description="e.g. ['same type (hoodie)', 'Saybrook', 'comes in gray', 'cheaper']")


class SimilarProductsResult(BaseModel):
    """find_similar_products output."""

    base_product_id: str
    base_name: str
    base_price: float
    base_colors: list[str]
    requested_color: str | None
    base_has_requested_color: bool | None = Field(
        description="Whether the original product itself comes in the requested color (None if no color was asked for)"
    )
    total_matches: int
    products: list[SimilarProduct]


class SavedPreference(BaseModel):
    """remember_my_size / forget_my_size output."""

    ok: bool
    preferred_size: str | None
    message: str


class WaitlistResult(BaseModel):
    """join_waitlist output."""

    ok: bool
    product_id: str
    name: str
    size: str
    message: str


class LookupFailed(BaseModel):
    """Returned instead of a result when a product or size doesn't exist."""

    error: str


# ---- What the agent returns -------------------------------------------------


class AgentReply(BaseModel):
    """The agent's structured output (its output_type)."""

    reply: str = Field(description="The message shown to the shopper. Short, friendly, plain text.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=8,
        description="Catalogue product_id values to show as product cards in the chat. Only IDs returned by a tool.",
    )
    update_page: bool = Field(
        default=False,
        description="True when the shopper is browsing for a kind of item and the matches from your latest "
        "search_products call should be shown on the website. False for one specific item, stock questions, or small talk.",
    )
    results_title: str | None = Field(
        default=None,
        max_length=80,
        description="Short heading for the page results when update_page is true, e.g. 'Navy hoodies under $70 in M'.",
    )


# ---- What the website receives ----------------------------------------------


class ProductCard(BaseModel):
    """A product tile for the chat or the page. Every field comes from the database, not from the model."""

    product_id: str
    name: str
    price: float
    image_url: str
    garment_type: str
    short_description: str = Field(description="The catalogue description, trimmed to about 100 characters")
    sizes_in_stock: list[str]
    in_stock: bool


class PageResults(BaseModel):
    """Search matches the website shows on the Products page (the chat-to-page contract)."""

    title: str = Field(description="Heading, written by the agent")
    query: str = Field(description="The keywords the agent searched for")
    total_matches: int
    products: list[ProductCard] = Field(description="Every match from the agent's search, up to 30, in catalogue order")


class SavedMessage(BaseModel):
    """One message from a logged-in customer's saved history (GET /api/chat/history)."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list["ProductCard"] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    messages: list[SavedMessage]


class ChatReply(BaseModel):
    """POST /api/chat response."""

    reply: str
    products: list[ProductCard] = Field(default_factory=list, description="The agent's picks, shown in the chat panel")
    page_results: PageResults | None = Field(
        default=None, description="When present, the website shows these matches on the Products page"
    )
    fact_check: "FactCheckInfo | None" = Field(default=None, description="What the fact-check verified in this reply")
    preferred_size: str | None = Field(
        default=None, description="The customer's saved size after this turn (the agent can save or forget it)"
    )


class FactCheckInfo(BaseModel):
    """Shown under a reply as 'Checked against live inventory'."""

    facts_checked: int = Field(description="Prices and stock numbers in the reply that were verified against the database")
    corrections: int = Field(description="How many times the reply was sent back to the model to fix a wrong fact")


class WaitlistEntry(BaseModel):
    product_id: str
    name: str
    size: str
    created_at: str
    back_in_stock: bool = Field(description="True once that size has stock again")


class SizeRequest(BaseModel):
    size: str = Field(max_length=20)


class WaitlistRequest(BaseModel):
    product_id: str = Field(max_length=100)
    size: str = Field(max_length=20)
