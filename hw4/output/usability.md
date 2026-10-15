# Campus Customs: usability improvements (Problem 9)

The assignment asks for **2 front-end** and **2 agent/backend** usability improvements. We built those four as the headline features, plus two extras on each side. Every item below is visible in the running app; the "Where to see it" line says exactly where.

All eight were tested in a real Chromium browser (`tests/browser_usability_test.py`, **18/18 checks passed**), and the fact-check also has its own test (`tests/fact_check_test.py`, **5/5**). Screenshots are in `output/browser_proof/usability-*.png`.

| # | Improvement | Side | Where to see it |
|---|---|---|---|
| 1 | Suggested-question chips | Front end (required) | Open the chat on any page |
| 2 | Recently viewed strip | Front end (required) | Open two products, then any product page or the Products page |
| 3 | "Find a similar one" tool | Backend (required) | Product page, chat chip "Do you have this in gray?" |
| 4 | Fact-check every reply | Backend (required) | Green "✓ … checked against live inventory" line under replies |
| 5 | "Ask about this item" button | Front end (extra) | Every product page, under the price |
| 6 | Clickable colors | Front end (extra) | Product page, "Colors" section |
| 7 | Remember my size (opt-in) | Backend (extra) | Log in, tell the chat "remember I'm a medium" |
| 8 | Back-in-stock waitlist | Backend (extra) | Log in, click a crossed-out size on a product page |

## Our principle: personalize from what shoppers do and say here, not from guesses about who they are

Before choosing features we asked what's fair to use about a shopper:

| Idea | Decision | Reasoning |
|---|---|---|
| Read their searches on other shopping sites | **No** | Our site can't see them without third-party tracking or spyware. It's invasive, legally risky (state privacy laws, FTC), and would cost the trust of the Yale community the shop depends on. |
| Look at photos on their computer | **No** | Websites can't open files unless the shopper picks one, and anything that tried would behave like malware. An opt-in "upload a photo to find similar gear" feature would be the acceptable version (future idea). |
| Sort them into demographic groups (age, gender, income) | **No** | The guesses are often wrong (students buy "Yale Mom" gifts), they stereotype, and they can drift into discrimination. Asking or listening works better. |
| What they're doing on our site: the product on screen, the size they picked, items they viewed, a size they told us | **Yes** | First-party, expected, and useful. We make it visible and easy to clear. |
| Understand "this one" and "I want a gray one" | **Yes** | Page context (Problem 8) tells the agent what "this" is; the new similar-item tool finds "a gray one". |

## Ideas we considered and decided against

| Idea | Why we decided against it |
|---|---|
| **Reading shoppers' past searches on other shopping sites** to guess what clothing they want | Needs third-party tracking data or spyware; invasive, legally risky under privacy laws and FTC rules, and a breach of trust with the Yale community. |
| **Scanning photos on the shopper's computer** to see what they might need | Browsers can't open files the shopper didn't choose, and anything that tried would be malware. Even if it were possible, it's a serious privacy violation. |
| **Putting shoppers into demographic categories** (age, gender, income, etc.) to target products | Often wrong, stereotyping, and a discrimination risk. It also isn't needed: the shopper's own words and clicks are better signals. |
| **Opt-in "upload a photo to find similar gear"** | Acceptable because the shopper chooses the photo, but it needs an image-reading model and a policy for handling uploaded photos. Left as a future idea, not built now. |
| **Saving "recently viewed" on our server** | Not needed. Keeping it in the shopper's own browser gives the same convenience with no tracking, and it's cleared with one click. |
| **Saving a shopper's size automatically** whenever they mention it | Saving without asking feels like surveillance. We made it opt-in: the size is saved only when the shopper asks the assistant to remember it, and it's always visible and removable. |
| **Emailing shoppers when a size is back in stock** | The site has no email system, and promising a notification we can't send would mislead people. The waitlist only records the request, and the site says so honestly. |
| **Remembering guests' chats** (e.g. by cookie) | Guests haven't agreed to an account. Their chat stays in the open window only; logging in is the clear opt-in for memory. |

## Headline improvements (the required 2 + 2)

### 1. Front end: suggested-question chips in the chat

**What it is.** Above the chat box, one-tap questions that change with the page:

| Page | Chips |
|---|---|
| Product page | "Is this in stock in M?" (or "What sizes are in stock?" if no size is saved or picked), "Do you have this in gray?", "Something similar but cheaper?", and, for a logged-in shopper who picked a size, "Remember M as my size" |
| Chat search results | "Which of these are in stock in M?", "Show me cheaper options", "Any of these in gray?" |
| Products page | "Hoodies under $70", "Gifts for a Yale parent", "What should I wear to The Game?" |
| Home and other pages | "Show me your hoodies", "Anything for Saybrook?", "Gifts for a Yale mom" |

**Why it helps.** Most shoppers don't know what a chatbot can do, and typing on a phone is slow. Chips show what to ask in one tap, and they quietly teach the features that matter (stock by size, other colors, gift ideas). For the business, more shoppers who actually use the assistant means more questions answered, and more sales, instead of shoppers leaving.

**Where to see it.** Open the chat on any page; move between Home, Products, and a product page and the chips change. Code: `suggestionsFor()` in `frontend/src/components/ChatWidget.tsx`.

**Tested.** "Product page shows page-specific suggestion chips" and "Products page shows different chips" both pass; clicking "Do you have this in gray?" sends it and gets an answer.

### 2. Front end: "Recently viewed" strip

**What it is.** The last 8 products you opened, as small photo cards, on every product page (below the item) and on the Products page (above the grid), newest first. It's stored **only in your browser** (localStorage), never sent to our server, and the strip has a **Clear** button and the note "Saved only in this browser".

**Why it helps.** Shoppers compare: two hoodies, then a crewneck, then back to the first hoodie. The strip makes going back one click instead of searching again. For the business, people who return to items they viewed are likely buyers, so making that easy helps conversion. Keeping it on the shopper's device gives the convenience without tracking.

**Where to see it.** Open any two products; the strip appears on the second one and on the Products page. Code: `frontend/src/recentlyViewed.ts`, `frontend/src/components/RecentlyViewed.tsx`.

**Tested.** Strip shows the earlier product; Products page lists them newest first; data is in localStorage; "Clear" removes it (4 checks pass). Screenshot `usability-01-recently-viewed.png`.

### 3. Agent/backend: "Find a similar one" tool (`find_similar_products`)

**What it is.** A new agent tool that takes the product on screen and finds close alternatives, optionally **in another color**, **cheaper**, under a **price**, or **in stock in a size**. It scores every catalogue item by:

- same garment type, e.g. hoodie (+4)
- same college, sport, school, or family theme (+3)
- shared keywords (up to +3)
- similar price (+1)

It understands color families ("gray" also finds "heather gray" and "charcoal"), skips anything sold out, and says *why* each item matched ("same type (hoodie)", "comes in gray", "$26.00 cheaper", "12 in stock in XL"). Like search, its matches can also fill the Products page.

**Why it helps.** "Do you have this in gray?" and "this is sold out in my size" are dead ends on most sites. Now the shopper gets real alternatives instead of a "no", which keeps a sale that would otherwise be lost. It's also more accurate: the agent no longer guesses what's "similar".

**Where to see it.** On the Basic Hoodie Big Yale page (navy and white only), click the chip "Do you have this in gray?". Code: `find_similar_products` in `backend/tools.py`.

**Tested.** Reply: "This Basic Hoodie Big Yale doesn't come in gray. It's available in navy blue and white. Similar gray hoodie options include District Vit Hoodie Vintage Bulldog, District Vit Hoodie Vintage Sailor Bulldog, Yale Sports Hoodie Baseball, and Yale Sports Hoodie Diving…" The test checks that every suggested card really comes in gray in the database. Screenshot `usability-03-chip-gray-similar.png`.

### 4. Agent/backend: fact-check every reply

**What it is.** A PydanticAI **output validator** (`fact_check` in `backend/agent.py`) runs on every answer *before* the shopper sees it. `fact_check_reply()` in `backend/tools.py`:

- finds each catalogue product name in the reply;
- checks the price written after it against the database;
- checks stock claims like "5 left in M", "S (15)", and "out of stock in XL" against the inventory;
- checks that every product card ID is real.

If anything is wrong, the reply is sent back to the model with the exact problem ("you wrote Basic Hoodie Big Yale costs $58.00, but the database price is $68.00…") and it must fix it, up to 2 times. If it still can't, the shopper gets a safe message pointing to the product page, **never the wrong answer**. Dollar amounts the shopper typed (a budget like "under $70") aren't treated as prices.

**Why it helps.** Wrong prices or stock from a chatbot cost money and trust: a shopper who's quoted $58 and charged $68 doesn't come back. The prompt already says "don't invent numbers", and this turns that from a request into a rule the code enforces. Each checked reply shows a small green line, **"✓ 5 price/stock facts checked against live inventory"**, so shoppers can see the answer was verified.

**Where to see it.** Ask any price or stock question; the green line appears under the reply. Code: `fact_check` (agent.py) and `fact_check_reply` (tools.py).

**Tested.**

- `tests/fact_check_test.py` (5/5) uses a scripted stand-in model that deliberately says the wrong price and stock. The checker catches both, the model gets the correction, the shopper only sees the corrected "$68.00 … 5 left in M", and a model that stays wrong is never shown.
- In the browser, the line "✓ 5 price/stock facts checked against live inventory" appears (screenshot `usability-02-ask-about-this-fact-check.png`).
- All 7 earlier price and stock checks (`agent_tools_check.py`) still pass with the validator on.

## Extra improvements

### 5. Front end: "Ask about this item" button

**What it is.** A button on every product page, under the price, that opens the chat and asks "Tell me about this one. What sizes are in stock?". The agent knows which item "this one" is from the page context.

**Why it helps.** Shoppers on a product page often have one question about *that* item. One click gets a summary, price, and stock by size, with no typing.

**Where to see it.** Any product page.

**Tested.** The reply names the right product (Baseball Left Chest Crewneck) with its exact stock.

### 6. Front end: clickable colors

**What it is.** The product's colors appear as color swatches. Under them, "Want this style in another color?" shows clickable swatches for common colors the item *doesn't* come in. Clicking one asks the chat "Do you have this in green?", which uses the similar-item tool.

**Why it helps.** Colors are easier to scan as dots than as a comma list, and the "another color" swatches turn a missing color into a one-click search instead of a lost shopper.

**Where to see it.** "Colors" on any product page.

**Tested.** The swatches match the database colors, and clicking "green" got an honest "isn't available in green… I couldn't find a similar green hoodie" with an offer to search all green apparel. Screenshot `usability-04-color-swatch.png`.

### 7. Agent/backend: remember my size (opt-in)

**What it is.** New tools `remember_my_size` and `forget_my_size`, a `customer_preferences` table (user_id, preferred_size, updated_at), and `PUT`/`DELETE /api/me/size`.

- **Opt-in only:** the prompt says to save a size only when the shopper asks or agrees, never just because they mentioned one.
- **What a saved size does:**
  - shows as a chip in the chat ("Your saved size: M", with an × to remove it);
  - is pre-selected and outlined on every product page;
  - goes into the agent's context, so "is this in stock in my size?" just works.
- **Other ways to save:** a "Remember M as my size" link on product pages.

**Why it helps.** Shoppers stop re-picking their size on every item, and stock answers fit them automatically. Because it's opt-in, visible, and one click to remove, it's personal without feeling creepy.

**Where to see it.** Log in and tell the chat "Please remember that I'm a medium."

**Tested.**

- The agent saved M to the database.
- M was pre-selected on the next product page.
- "Is this in stock in my size?" got "your saved size, M, is in stock… There are 5 left in M."
- The chip's × deleted it.

Screenshot `usability-05-saved-size.png`.

### 8. Agent/backend: back-in-stock waitlist

**What it is.** A `stock_requests` table (user, product, size, date; one row per user, product, and size) and `GET`/`POST`/`DELETE /api/waitlist`.

- **On a product page:** sold-out sizes stay crossed out but can now be clicked. Logged-in shoppers get "Join the waitlist for XL", then "You're on the waitlist for XL · Leave waitlist". Guests get "Log in to join the back-in-stock waitlist".
- **In the chat:** the agent's `join_waitlist` tool does the same when a shopper asks. It refuses if the size is actually in stock.

**Why it helps.** Shoppers aren't left at a dead end, and the store gets **real demand data** (which sizes of which items people are waiting for) to plan restocks:

```sql
SELECT c.name, r.size, COUNT(*) AS waiting
FROM stock_requests r JOIN catalogue c USING (product_id)
GROUP BY r.product_id, r.size ORDER BY waiting DESC;
```

**Honesty:** the site has no email system, so neither the page nor the agent promises a notification. Both say "no email is sent; check this page".

**Where to see it.** Log in, open the Baseball Left Chest Crewneck, and click **XL**.

**Tested.**

- The button saved (product, XL).
- Asking the chat "put me on the waitlist for XS on this one" saved (product, XS).
- The agent said "no email or text is sent, so please check the product page later".

Screenshot `usability-06-waitlist.png`.

## What changed in the code

| Area | Files |
|---|---|
| Agent tools | `backend/tools.py`: `find_similar_products`, `remember_my_size`, `forget_my_size`, `join_waitlist`, `fact_check_reply` |
| Agent wiring | `backend/agent.py`: tools registered, `fact_check` output validator (2 retries), saved size added to "Who you're talking to" |
| Prompt | `backend/prompts/prompt.md`: similar-item, saved-size (opt-in), waitlist (no email), and fact-check rules |
| API and database | `backend/main.py`: `customer_preferences` and `stock_requests` tables (created on startup), size and waitlist endpoints, `fact_check` and `preferred_size` in the chat reply |
| Front end | `ChatWidget.tsx` (chips, fact-check line, size chip), `ProductPage.tsx` (Ask button, swatches, waitlist, saved size, recently viewed), `RecentlyViewed.tsx`, `recentlyViewed.ts`, `chatControl.tsx` (lets pages open the chat and ask it something) |
| Tests | `tests/browser_usability_test.py` (18 checks), `tests/fact_check_test.py` (5 checks) |

All earlier tests still pass after these changes: `agent_tools_check.py` 7/7, `browser_chat_search_test.py` 11/11, `browser_memory_test.py` 10/10, `browser_auth_test.py` 12/12.
