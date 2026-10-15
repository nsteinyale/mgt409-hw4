# Campus Customs shop + chatbot (MGT 409 Homework 4)

A Campus Customs (Yale Bulldog Blue) web shop with "Dan", a PydanticAI shopping assistant that looks up real prices and stock, updates the page with search results, remembers logged-in customers, and is fact-checked and audited.

| Folder or file | What's in it |
|---|---|
| `backend/` | FastAPI app (`main.py`) and the **agent: `prompts/prompt.md`, `agent.py`, `tools.py`, `models.py`**, plus `auth.py` (passwords and sessions) and `safety.py` (personal-info redaction) |
| `frontend/` | React + Vite + TypeScript website |
| `output/harness.md` | **How the whole system works:** models, tools, safety rules, audit trail, specs |
| `output/audit_trail.json` | Append-only log of every agent-loop step |
| `output/usability.md`, `output/design.md`, `output/app_check.html` | Problem 9, 10, and 11 write-ups (open `app_check.html` by double-clicking it) |
| `tests/` | Real-browser (Playwright) and API tests |
| `AI_prompts.md` | The prompts I typed for each problem |

The data pack, API keys, and product images are **not** in this repo. You add them in step 1 and step 3 below.

## Run it

You need **Python 3.11+**, **Node.js 20+**, a **Portkey API key**, and the course **data pack** (`data.zip`).

### 1. Place the data pack

Unzip `data.zip` inside this `hw4` folder, so you get:

```
hw4/
  data/
    campus_customs.db
    products/          (102 product .jpg images)
  backend/
  frontend/
  ...
```

The backend also accepts `hw4/data/data/…` (if the zip was extracted into a folder named `data`), or any folder you point to with `CAMPUS_CUSTOMS_DATA=/path/to/data`. On first start it adds three tables to the database for saved sizes, the waitlist, and a history index.

### 2. Install the backend

From the `hw4` folder:

```bash
python -m venv .venv
```

Activate it (Windows: `.venv\Scripts\activate`, macOS/Linux: `source .venv/bin/activate`), then:

```bash
pip install -r backend/requirements.txt
```

### 3. Add your API key

Copy `.env.example` to `.env` (in `hw4/` or `hw4/backend/`) and fill in `PORTKEY_API_KEY`. `OPENAI_MODEL` (default `gpt-5.6-luna`) and `SESSION_SECRET` are optional. Never commit `.env`; it's in `.gitignore`.

### 4. Start the backend (terminal 1)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Check http://localhost:8000/api/health shows `{"status":"ok"}`.

### 5. Start the front end (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5180**. The front end forwards `/api` and `/images` to the backend on port 8000.

**Test account** (from the seed database): `test@campuscustoms.yale.edu` / `password`, or create your own on the site.

**Try:** "hoodies?", "Is the Baseball Left Chest Crewneck in stock in XL?", or on a product page, the chips "Do you have this in gray?" and "Ask about this item". The footer has "Play Bulldog Dash".

## API

| Endpoint | Returns |
|---|---|
| `GET /api/health` | `{"status": "ok"}` |
| `GET /api/products`, `GET /api/products/{product_id}` | Catalogue products; one product with stock by size |
| `GET /images/{file}.jpg` | Product photo (from the data pack) |
| `POST /api/signup`, `POST /api/login`, `POST /api/logout`, `GET /api/me` | Accounts with PBKDF2 passwords and an HttpOnly session cookie |
| `POST /api/chat` | `{message, history, page}` → `{reply, products, page_results, fact_check, preferred_size}`. Saves the exchange for logged-in customers. |
| `GET /api/chat/history`, `DELETE /api/chat/history` | A logged-in customer's saved chat |
| `PUT /api/me/size`, `DELETE /api/me/size` | Opt-in saved size |
| `GET /api/waitlist`, `POST /api/waitlist`, `DELETE /api/waitlist/{product_id}/{size}` | Back-in-stock waitlist (no emails are sent) |

## Tests (optional)

Install the test tools once:

```bash
pip install playwright
playwright install chromium
```

Run these from the `hw4` folder with both servers running. Browser tests accept `--headless`. Screenshots go to `output/browser_proof/`. Some tests add test accounts (with `@example.com` addresses) or chat messages to your local database.

| Command | Checks |
|---|---|
| `python tests/app_check.py` | Rebuilds `output/app_check.html` from the live site: inventory answer vs. database, "hoodies?" page results, a usability feature |
| `python tests/browser_auth_test.py` | Seeded login, brand new account, logout and login, password hashing |
| `python tests/browser_chat_test.py` | Chat answers, follow-ups, off-topic refusal, out-of-stock, product cards |
| `python tests/browser_chat_search_test.py` | "hoodies?" fills the page; cards open the detail page |
| `python tests/browser_memory_test.py` | Guest vs. saved history; "do you have this in pink?" on a product page |
| `python tests/browser_usability_test.py` | All eight Problem 9 improvements |
| `python tests/browser_style_test.py` | Problem 10 style features (Dan, Bulldog Dash, chase, map) |
| `python tests/safety_check.py` | Red-team of the safety rules; audit trail only grows |
| `python tests/agent_tools_check.py` | Agent answers price and stock questions from the database (needs the API key, not the servers) |
| `python tests/fact_check_test.py` | Fact-check catches and corrects a wrong price (no key or server needed) |
