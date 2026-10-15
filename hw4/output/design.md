# Campus Customs: design and style (Problem 10)

**Goal:** still unmistakably Campus Customs (Yale navy, collegiate, friendly), but with playful touches that make shoppers stay, explore, and come back. *(Our course default is a black-and-pink theme; we kept the Campus Customs navy because the brand matters more here.)*

## What we changed and why

| Change | What it is | Why it keeps customers around |
|---|---|---|
| **Collegiate type and color** | Libre Baskerville serif headings, Yale navy with a gold accent (gold rules under titles, on the hero, nav, and tiles) | Feels like a Yale shop, not a template. A clear hierarchy makes pages faster to scan. |
| **Product presentation** | On hover the photo zooms and a "View details →" label slides up. Color dots sit next to each price. | Shoppers see colors without clicking and know every card opens. Fewer dead clicks, more product views. |
| **Gentle motion** | Pages fade in. Everything respects the "reduce motion" setting. | Smooth without being distracting, and accessible to people who get motion-sick. |
| **Dan, the talking bulldog** | An original cartoon bulldog in the chat. He blinks, tilts his head while thinking, and his mouth moves while a reply "plays". The chat button says "Chat with Dan". | A face and a name make the assistant feel friendly, so more shoppers try it. Shoppers who chat find products faster. |
| **Bulldog Dash** | A Chrome-dino-style runner: the bulldog jumps Harvard pennants and "H" blocks, with a saved high score. It appears on the 404 page, when the internet drops, and at "Play Bulldog Dash" in the footer. | Turns dead ends (wrong link, lost connection) into a reason to stay instead of leaving. A high score brings people back. |
| **Harvard chase easter egg** | A Yale bulldog in a "Y" sweater chases a Harvard dog across the screen ("Boola boola!"). It plays once per visit on the home page, and when someone searches "Harvard", opens The Game tee, or mentions it in chat. | A delightful surprise that's very shareable, rewards exploring, and plays on the Harvard-Yale rivalry. |
| **Campus map flyover** | An illustrated map of New Haven's nine-square grid (Old Campus, the Green, Broadway). When scrolled into view it zooms toward 57 Broadway as a gold path draws from Old Campus, with a "Get directions" link. | Makes the physical store feel close and easy to find, and nudges online visitors to visit in person. |

## Choices we made

- **Our own bulldog, not the official Handsome Dan.** He's inspired by the Yale bulldog tradition but drawn from scratch, to avoid copying a trademark. The prompt tells the agent never to claim to be the official mascot.
- **Friendly rivalry only.** The Harvard dog is chased, never mocked.
- **One game, not two.** We chose the runner over Snake because it's quicker to learn and works with a tap on phones.
- **No cartoon "student crowd".** Generic or AI-drawn people risk looking stereotyped. We spent the effort on Dan and the map instead.
- **Accessible.** Shoppers with "reduce motion" turned on get no chase and a still map. The game is keyboard-playable. Gold text uses a darker shade that passes contrast rules.

## Verified

`tests/browser_style_test.py`, real Chromium, **19/19 checks passed**:
- serif headings;
- chase on the first visit and on a "harvard" search, but not twice per visit and never with reduced motion;
- map zoom and callout;
- card hover zoom and color dots;
- Dan thinking, talking, then stopping;
- game score and high score;
- the game on 404 and offline pages.

All earlier tests still pass. Screenshots: `output/browser_proof/style-*.png`.
