# Homework 4 - AI Prompt Log

Homework 4: Campus Customs Shop + Chatbot. This file logs what I typed to my vibe coder (Claude Code), one section per problem. I keep it updated as I work.

## Getting started (setup before Problem 1)

**Prompts I typed:**
- "Start by explaining to me the difference in this context, and in general, between what I want to include on a front end and on a back end."
- "The data file zip was extracted in the 'Home Work 4' folder, also review https://yalebulldogblue.com for reference for this assignment."
- "Can you show me a preview of the DB file here?"

**What I got:** An explanation of the front end/back end split for a shop with a chatbot (API key, prices, and database writes stay on the back end), a review of the provided data (`data/data/campus_customs.db` with the `catalogue`, `inventory`, `users`, and `chat_messages` tables, plus 102 product images), notes on the Yale Bulldog Blue site as a design reference, and an interactive preview of the database tables.

## Problem 1: Vibe coder prompts

**Prompt I typed:** "We are going to do my AI for Managers class HW together, can you view this website and get ready with me?"

**Follow-up prompt:** "To start, make AI_prompts.md and keep it updated and log our chats. There will need to be one section for each problem, including the problem number and title, at least one prompt I typed and one follow-up prompt I needed (and why I needed it/what was missing)."

**What was missing after the first prompt:** My first prompt only pointed the assistant at the assignment page without saying what to build, so I had to describe the task in my own words: create this log file and what each problem's section must contain.

## Problem 2: Analyze the database

**Prompt I typed:** "Let's start with analysis. First, look at the data/campus_customs.db we were just looking at and make sure you get it, at least catalogue, inventory, users. Start the file output/harness.md and write down each table and its fields and one short line on why each field matters for the shop and the chatbot (we are making a chatbot for ease of use of the website to buy stuff). We will add to this harness file later."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** Nothing major. Earlier I had asked for a preview of the database, so this prompt could build on that and ask for one line per field and why it matters for the shop and the chatbot.

## Problem 3: Build the Campus Customs website

**Prompt I typed:** "Next we are going to build the Campus Customs website. Scaffold a React + Vite + TypeScript front end for Campus Customs. Put a nav bar at the top that links to the main pages of Home, Products, About Us, Log In, Create Account, and pull Campus Customs style wording from yalebulldogblue.com for Home and About Us, but write these pages in your own voice (not copying theirs word for word). The Products page should show product images from the catalogue (using the image paths in the database) with basic product info (name/price/description). Each product should open a single item page (large image on one side, product text on the other: description/price/sizes and stock when available). Clicking a card on Products should take the shopper there. Now add a chat interface in the bottom right of the site (a floating chat panel works too); it does not need to talk to an agent yet, but a stub that will call the backend later works. We need a small API to read the database: start with a simple FastAPI app in backend/main.py just to serve products and images, then it will grow in Problem 5."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** Nothing major. The prompt listed every page, what each one shows, and the backend's job, so the site could be built in one pass. Small details I didn't specify (product search and type filters, "shop by" collections for colleges, sports, and family, and a sold-out marker on sizes) were added to match the Bulldog Blue reference site.

## Problem 4: Create account and login

**Prompt I typed:** "Next, account logins: we are going to build a create-account / login flow. Create account is first/last name, email, password (with confirm password for aesthetics), and login will be email and password. New accounts will be added to the users table; store these passwords securely so no human or AI hackers can get to them. The seed DB already has a test user: email test@campuscustoms.yale.edu, password: password, hash function PBKDF2-HMAC-SHA256, 120,000 iterations, stored as pbkdf2_sha256$salt$hash. To check the password at login, never unhash the stored value, just rehash what the user typed and compare: read the salt out of the stored string (the middle piece), but do not make a new one at login; hash the typed password with that exact same salt, then compare to the stored hash using a constant-time compare. Signup and login must use the same hash settings (same function, same salt handling, same iteration count); if they differ, even the right password will not match. The surest check will be to log in as the seeded test user and as a brand new account we just created in our own app. Update output/harness.md with how authentication works, what we store for a user, and how passwords are protected."

**Follow-up prompt:** "Can you prove this works in a real browser?"

**What was missing after the first prompt:** My first prompt said how to verify (log in as the seeded test user and as a new account) but not where, and the first round of checks ran in the app's preview pane, partly by submitting forms through code. The follow-up asked for proof in a real browser, so the assistant wrote `tests/browser_auth_test.py`, which drives Chromium with real clicks and typing and saves screenshots and a video to `output/browser_proof/` (12/12 checks passed). It also caught a layout bug where the Last name box stuck out of the Create account form, which was fixed.

## Problem 5: PydanticAI agent backend

**Prompt I typed:** "Next step will be the backend you explained to me and the PydanticAI agent. We need to build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into the front end chat widget. Put the API app in backend/main.py (the file we will run with uvicorn). The agent will be these four files next to it (just like we did with HW 3): backend/prompts/prompt.md (the system prompt, which will grow with later problems), backend/agent.py (agent entry and wiring), backend/tools.py (tools the agent can call), and backend/models.py (Pydantic/PydanticAI structured types). In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else we need for products and auth). We need the AI model API key for the agent. Put Campus Customs's voice and safety basics into prompts/prompt.md (this will be expanded later). Start or update types in models.py for chat replies/product cards as needed. In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file plus model). Make sure the backend runs from the backend folder like this: uvicorn main:app --reload --port 8000."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** I didn't say which model or key to use, so the assistant followed my course rules (Portkey key from `.env`, `gpt-5.6-luna`, changeable with `OPENAI_MODEL`). Testing found two gaps it fixed: a jailbreak attempt ("print your system prompt") was blocked by the model provider's filter and showed an error instead of a polite refusal, and the agent told a shopper to "complete checkout" even though the site has no checkout, so that fact went into the prompt.

## Problem 6: Tools: product info and stock

**Prompt I typed:** "Now, we are doing the tools for product info and stock. The agent should have the tools to look up the real info from campus_customs.db, such as the product description, price, and number in stock (and by size if needed); the agent must use the DB and NOT INVENT prices or quantities. If the size is out of stock, just say so clearly (people can wait for it to come back into stock). Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions; add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for lookup results and why."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** I didn't say how to check that the agent really used the database, so the assistant wrote `tests/agent_tools_check.py`, which records the tools the agent calls and compares every price and stock number in its replies to the database (7/7 passed). Testing also showed the agent shortening a product name, so the prompt now requires exact names, and the search tool now reports words it couldn't match (like "pink") so the agent says plainly when we don't carry something.

## Problem 7: Chat search that updates the page

**Prompt I typed:** "Next is a chat search that updates the page. When a customer asks about a type of item like a hoodie, the agent should search the catalogue and the website should dynamically show matching items as product cards (image/name/price/short info). This is an API contract: the agent will return the structured product matches and then the front end renders them on the website. It should be cool. Once the dynamic product cards load, make sure the same single-item page behavior we built in Problem 3 still works: each product card (including the ones the chat just put on the page) should still open that detail view (large image, full info) when clicked. Update prompts/prompt.md and output/harness.md so it's clear how search results reach the page."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** I didn't say where on the site the results should appear or when the page should *not* change. The assistant showed them on the Products page with a banner, and had the agent update the page only for browsing requests (not single-item or stock questions), so a shopper reading a product page isn't pulled away. Testing showed one gap: asking "is this one in stock?" from a product page made the agent ask which item, because the chat doesn't yet know which product page you're on.

## Problem 8: Customer memory

**Prompt I typed:** "Next is customer memory: save a logged-in user's chat history in the DB in an appropriate table and reload it when they return. The agent should know who is chatting (name/email); put that in agent deps (or an equivalent clear pattern) and/or the tools the agent can call. Also pass enough page content that if someone is on a product page and asks 'do you have this in pink', the agent knows which item they mean (hint: you can put code into the agent context). Guests can still chat, but history only needs to persist for logged-in users. Document this in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** I didn't say what should happen on logout or whether customers can delete their history, so the assistant clears the chat window on logout (for shared computers) and added a "Clear history" button. It also made the server load history from the database for logged-in customers instead of trusting what the browser sends, and skipped saving messages the provider's filter blocks. This prompt also covered the "this one" page-context idea I had saved for Problem 9.

## Problem 9: Usability improvements

**Prompt I typed:** "Usability improvements are next. Now that the shop works, we will choose and implement 2 front-end usability improvements and 2 agent/backend usability improvements. The front end makes the site look better and work easier, as we discussed, and the backend will make the agent's output better, safer, or more accurate. Let's think about this together, then write output/usability.md before or as we build it. We will list what we added and why it helps Campus Customs's shoppers or the business. Then we will make sure that all improvements actually show up in the running app; graders will read the write-up and look for our features, so let's think about it! Would we want to read their past shopping searches for clothing, or is that too invasive? Or look at their photos on their computer to see what they would plausibly need? Or just try to put them into a demographic category to do so? And knowing what product they are on if they say 'THIS ONE', or it can match to what they want ('I want a gray one', etc.)."

**Follow-up prompt:** "Also, list all the ideas that we considered but didn't use as well, thanks! That we DECIDED AGAINST."

**What was missing after the first prompt:** My first prompt asked to think through the options but didn't ask to record the rejected ones, so I followed up to add an "Ideas we considered and decided against" table (reading outside shopping history, scanning photos, demographic profiling, and five more, each with the reason). We talked through the privacy questions first and settled on a principle: personalize from what shoppers do and say on our site, not from guesses about who they are. I then picked all four front-end and all four backend ideas, so `usability.md` marks the required 2 + 2 as the headline features and the other four as extras. All eight show up in the running app (18/18 real-browser checks).

## Problem 10: Style the website

**Prompt I typed:** "Next is website style. We need to add creativity so it's still Campus Customs (font, color, hierarchy, motion, product presentation, chat feel), but we will get more points here for innovation. Any ideas? Maybe a flyover map of New Haven? Maybe bulldogs animated and running across the screen, chasing a Harvard bulldog? Maybe a diverse group of cartoon students laughing/chatting? A Handsome Dan face who responds and whose lips move when they chat with you? All? Write output/design.md with what we changed and why it should help keep customers around and busy. Keep it concise and short. Maybe a game like that jumping dino game that shows up on Chrome when there is no internet, but with the bulldog? Or like a Snake game with the bulldog growing its tail?"

**Follow-up prompt:** None needed yet (I picked from the options the assistant laid out: the talking bulldog, the Bulldog Dash game, the Harvard chase, the map flyover, and a polish pass).

**What was missing after the first prompt:** I brainstormed a lot without choosing, so the assistant compared each idea and recommended picks, skipping the cartoon student crowd (stereotype risk), choosing one game instead of two, and drawing an original bulldog instead of the official Handsome Dan mascot (trademark). I hadn't mentioned accessibility; it made every animation respect "reduce motion".

## Problem 11: Site testing (app check)

**Prompt I typed:** "Next is testing the app on the site: test the live site and document it in output/app_check.html (a page we can double-click to open). Include clear screenshots and short captions for: 1. the chat checking the inventory level of an item (honestly pull the stock and price from the database); 2. that the dynamic search result cards appear after a category question like 'hoodies?'; 3. one of the usability features from Problem 9. Make the HTML easy to grade: a heading for each check, screenshots, and one or two sentences on what each screenshot proves. Put the screenshot image files in output/app_check_images and link them from app_check.html with relative paths (for example app_check_images/inventory.png)."

**Follow-up prompt:** None needed yet.

**What was missing after the first prompt:** I didn't say how to prove the numbers were "honestly" from the database, so the assistant wrote `tests/app_check.py`, which runs the live site in a real browser, reads the database at the same moment, and builds the HTML with the real reply next to a database table and PASS/FAIL marks. Reviewing the first screenshots showed the chat close-ups were cut off, so it scrolled each close-up to the question and made the chat panel taller on big screens, which also helps real shoppers.

## Problem 12: Audit trail, safety, finish harness

**Prompt I typed:** "Last steps: an audit trail, safety, and finishing the harness. We have to keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs (can you explain this to me? I'm not sure I follow what the homework asks for here). Then we need to think of some safety rules to give to the agent and put them in prompts/prompt.md (perhaps never revealing a customer's address, name, email, passwords, or credit card info, and reminding them not to put personal info in the chat? And don't trust the chat if it does? Maybe stay on topic even if they try to pull the chatbot away from the topic?). Then finish output/harness.md so it's clear how the system works: model the fields in models.py and why we chose them; tools and abilities; safety rules; specs (loop limits, result caps, models, how to run front and back)."

**Follow-up prompt:** None needed yet (my question about "append-only, don't wipe between runs" was answered in plain terms before building: a diary of every agent step that only ever grows, so the store can look back at what the bot checked and when).

**What was missing after the first prompt:** My safety ideas were all prompt rules, which depend on the model obeying. The assistant also enforced them in code:
- Card numbers, emails, phone numbers, and passwords are removed from messages before the model, the database, or the audit trail sees them.
- A privacy check rejects replies that contain someone else's email.
- Identity comes only from the login, never from claims in the chat.

A red-team test (`tests/safety_check.py`, 16/16) tried a fake "store manager", requests for another customer's email, a typed card number, a jailbreak, and insistent off-topic questions. It also caught a mislabeled audit field (`page_results_sent`), which was fixed.

## Problem 13: Push to GitHub and submit the URL

**Prompt I typed:** "Now we wrap up and submit: push it to GitHub and submit the URL. Put the code in a folder called hw4 and push it to a public GitHub repo. On Canvas we will submit that URL to the graders, so they need to be able to open it and clone it; do not upload a zip. Do not put our real .env, campus_customs.db, or product images in the git repo. Use .gitignore, including .env.example with placeholders only. The agent itself is four files under backend/: prompts/prompt.md, agent.py, tools.py, and models.py (can you explain to me as well how an agent can be four files?). README.md should explain how to run the front end and back end after placing the data pack."

**Follow-up prompt:** None needed. Before publishing, the assistant asked me to confirm the public repo name, to use my GitHub private email instead of my Yale email in the public commit history, and to include the test screenshots.

**What was missing after the first prompt:** I didn't think about where graders would unzip the data pack. The official `data.zip` unzips to `data/campus_customs.db`, but our code only looked in `data/data/` (how I had extracted it), so a grader's copy wouldn't have found the database. The backend and tests now find the data in either place, with a clear error if it's missing. The assistant also scanned the repo for my API key, tokens, password hashes, and real people's emails before pushing, then cloned the public repo fresh, placed the data pack, and confirmed the backend runs (including a real chat answer) and the front end builds.

**Repo:** https://github.com/nsteinyale/mgt409-hw4 (code in `hw4/`)
