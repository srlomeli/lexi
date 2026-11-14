# Lexi's Word Game: Design Summary

AI 380: Human-AI Interaction, HW3, Fall 2026
Salvador Lomeli Rodriguez

_Target length: 2–3 pages. Export to PDF for submission._

## 1. Design concepts

### Target players and barriers in standard Wordle

**Lexi's Word Game** is a relaxing, accessible Wordle-style word puzzle designed for older adults (age 60+). While New York Times (NYT) Wordle is a widely enjoyed daily ritual, its interface assumes perceptual, motor, and cognitive baselines that create friction or exclusion for many older players (W3C WCAG 2.1; National Institute on Aging; Nielsen Norman Group, *Usability for Senior Citizens*):

| NYT Wordle barrier | Impact on older adults | How Lexi's Word Game removes it |
|---|---|---|
| **Color-only tile feedback** (green, yellow, gray) | Age-related lens yellowing and color-vision deficiencies make hues hard to tell apart. | Every scored tile pairs color with a **symbol** (`✓`, `●`, `✕`), a **plain-English label** (`Right`, `In word`, `Not in`), a **distinct border style** (solid, dashed, dotted), and strikethrough on absent letters, plus a zero-hue monochrome mode. |
| **Small, fixed typography and tight keys** | Presbyopia, low vision, and mild hand tremor make small text and closely packed keys tiring or error-prone. | Uses **Atkinson Hyperlegible** at `112.5%` base size with `Large` (`1.2×`) and `Extra large` (`1.4×`) settings, fluid `rem` scaling at 200% zoom, and controls $\ge 44 \times 44\text{ px}$ in QWERTY or alphabetical (`A–Z`) order. |
| **Keyboard/touch-only entry** | Arthritis, tremor, or unfamiliarity with on-screen keyboards can make typing slow or uncomfortable. | Multi-modal input: players can type on a physical keyboard, tap large on-screen keys, press **Speak**, or use hands-free **Voice mode** to say a word (`"crane"`) or spell it out (`"C, R, A, N, E"`). |
| **High working-memory load** | Remembering which duplicate letters are already accounted for or why a tile was scored a certain way taxes working memory. | Clicking or arrow-keying to any scored tile opens the **"Why this letter?"** explainer (in text and speech), alongside a persistent **Letter notebook** and full conversation log. |
| **Unforgiving daily format and streak pressure** | One puzzle a day, win-streak counters, and no graceful exit when stuck can turn a casual puzzle into a test. | Unlimited games with **no timers and no streaks**, curated everyday answers, zero penalty for unknown or mistyped words, and a gentle **"I give up"** option that kindly reveals the word. |

### Core design philosophy and AI boundary

Lexi is framed as a patient, encouraging companion rather than a judge. Following the **Microsoft Guidelines for Human-AI Interaction** (clear capabilities, graceful error recovery, and appropriate division of control), the architecture strictly separates **conversational understanding** from **game rules**:

```
Player (types, taps, or speaks a guess or question)
   │
   ▼
Web interface (web/index.html) ──► Deepgram Nova-3 STT & Aura-2 TTS (/webhooks/deepgram/*)
   │  REST webhook (/webhooks/rest/webhook)
   ▼
Rasa Pro (SearchReadyLLMCommandGenerator + Gemini 3.1 Flash-Lite)
   │  maps natural language to flows (start_wordle, make_wordle_guess, give_up_wordle,
   │  wordle_rules, voice_mode) and extracts the raw wordle_guess slot
   ▼
Custom actions (actions/action_wordle.py) + pure Python rules (game/wordle.py)
   │  deterministic answer selection, english.py validation, two-pass duplicate scoring,
   │  and controlled game slots (wordle_answer, wordle_guesses, wordle_active)
   ▼
Plain-language reply + wordle_board JSON ──► Web board, screen reader live region, & audio
```

- **Where AI helps:** Rasa Pro's `SearchReadyLLMCommandGenerator` (powered by `gemini-3.1-flash-lite` with automatic retry configuration) interprets flexible natural language—such as `"my guess is crane"`, `"how do I play?"`, or `"can I talk to you?"`—so players never have to learn rigid commands.
- **Where AI never takes control:** The language model never chooses the secret word, checks dictionary validity, counts turns, or scores letters. All game state lives in Rasa `controlled` slots (`wordle_answer`, `wordle_guesses`, `wordle_active`) updated exclusively by deterministic Python in `actions/action_wordle.py` and `game/wordle.py`. In addition, the rephraser prompt (`prompts/rephraser_demo_personality_prompt.jinja2`) enforces a strict rule never to invent word validity, letter counts, letter positions, remaining guesses, or the answer.

---

## 2. Core achievements

### Core game (G1–G7)

All seven core requirements are implemented in `game/wordle.py`, `game/curate.py`, and `actions/action_wordle.py`:

- **G1 — Hidden five-letter answer at game start:** `wordle.new_answer()` selects a random 5-letter word from `game/answers.txt` when `ActionStartWordle` runs. On the web page, a new game starts automatically on first load, and the secret word is omitted from the `wordle_board` JSON payload until `status` changes from `"playing"` to `"won"` or `"lost"`.
- **G2 — Fixed, justified number of guesses:** `MAX_GUESSES = 6`. Keeping six guesses preserves familiarity for players who have seen NYT Wordle with family members, while pairing those six turns with a curated common-word pool, zero penalty for invalid or repeated guesses, and a no-shame `"I give up"` button so six tries feel supportive rather than restrictive.
- **G3 — Validation against `english.py`:** `ALLOWED` precomputes a Python `set` of all 8,548 five-letter alphabetic words in `ENGLISH_WORDS` from `game/english.py` for $O(1)$ lookup while keeping every valid 5-letter word in `english.py` playable as a guess.
- **G4 — Forgiving handling of invalid guesses:** `wordle.normalize()` strips spaces and hyphens and lowercases input so `"C R A N E"` and `"crane"` work identically. `wordle.validate()` checks for empty input, non-letter characters, words shorter than 5 letters, words longer than 5 letters, and words not in `ALLOWED`. `score_guess()` also catches duplicate guesses already tried in the same game. Invalid or repeated guesses return a clear, polite explanation, leave `wordle_guesses` unchanged, keep typed letters in the input box for easy editing, and append a spelling tip (`"try spelling the word one letter at a time, like C, R, A, N, E"`) when on a voice channel.
- **G5 — Accurate repeated-letter scoring:** `wordle.score(guess, answer)` uses a deterministic two-pass algorithm adapted from an earlier Wordle implementation. Pass 1 marks exact position matches as `correct` and replaces matched letters in a working copy of `answer` with `"*"`. Pass 2 marks non-correct letters as `present` only if an unmatched copy remains in the working list, crossing off each matched copy as it is used. For example, guessing `SPEED` against `ABIDE` marks only the first `E` as `present` and the second `E` as `absent`. `wordle.keyboard_state()` tracks the highest rank seen per letter (`absent < present < correct`) so a key never downgrades once found in the right spot.
- **G6 — Clear win/loss message and restart:** `wordle.end_message()` announces wins with the answer and guess count (`"You got it! The word was SPENT, solved in 4 guesses. Would you like to play again?"`) and losses gently (`"Good effort! The word was MANLY. Would you like to play again?"`). The web page also opens a game-over summary modal (`#end-dlg`) with a miniature board recap and a focused **Play again** button, and players can restart any time by clicking **New game** or saying `"yes"` / `"new game"`.
- **G7 — Curated answer pool:** Because `english.py` contains 8,548 five-letter words—including obscure terms, inflections, proper nouns, and slurs—`game/curate.py` builds `game/answers.txt` through a reproducible four-step pipeline:

| Step | Filter applied in `game/curate.py` | Words remaining |
|---|---|---:|
| 1 | All 5-letter alphabetic words in `english.py` (`ALLOWED`) | 8,548 |
| 2 | Keep common everyday words with `wordfreq` Zipf frequency $\ge 3.5$ (~3+ occurrences per million words) | 1,740 |
| 3 | Drop simple plurals (`-s`, `-es`, `-ies`) and regular past tenses (`-ed`, `-ied`) whose base word is in `english.py` (`is_inflection()`) | 1,248 |
| 4 | Remove 105 manually reviewed words in `REMOVE`: slurs/crude terms, upsetting violent/medical words (`death`, `tumor`, `abort`), first/last names, places/brands, and British spellings/slang | **1,143** |

All 8,548 words in `english.py` remain valid guesses; only the secret answers are restricted to the 1,143 familiar words in `game/answers.txt`.

### Accessible feedback and interaction

The web front end (`web/index.html`, documented in `web/README.md`) implements all three accessibility priorities following WCAG 2.1 Level AA/AAA criteria:

- **Perceivable feedback without color:**
  - **Four-way redundant encoding:** Every scored tile shows (1) background fill, (2) a distinct icon (`✓`, `●`, `✕`), (3) an explicit word label on the tile (`Right`, `In word`, `Not in`), and (4) a distinct border (`4px solid` for Right, `4px dashed` for In word, `3px dotted` plus strikethrough letter text for Not in). On-screen keyboard keys also display the icon badge and `aria-label` state.
  - **Three visual themes:** Players can switch between **Colors, symbols, and words** (`standard`), **Symbols and words only** (`mono`, which uses zero color hue and serves as a built-in grayscale verification), and **High contrast, dark background** (`dark`).
  - **Verified WCAG 2.1 contrast ratios:** Every foreground/background pair and UI border was checked using the WCAG 2.1 relative luminance formula (`web/README.md`). Across all three themes, text contrast meets or exceeds the 4.5:1 AA threshold (ranging from **6.17:1** on green `Right` tiles up to **16.48:1** in `standard`, **9.94:1–18.88:1** in `mono`, and **8.21:1–21.00:1** in `dark`), and non-text indicators (tile borders, empty tiles, control borders, and focus rings) exceed the 3:1 threshold (**4.28:1–21.00:1**).
  - **Screen-reader and audio announcements:** `wordle.describe()` generates full plain-language sentences for every turn (e.g., `"CRANE: First letter C is not in the word..."`), announced via an `aria-live="polite"` status region (`#status`), while each board row includes a concise `.sr-only` summary and each scored tile exposes its position, state, and `"Select to hear why"` in `aria-label`.
- **Operable, forgiving interaction:**
  - **Full keyboard navigation and visible focus:** Players can type letters anywhere on the page without clicking an input box first, press `Backspace` to delete, and press `Enter` to submit. Scored tiles use a roving `tabIndex` pattern so `Tab` enters the board in a single stop and arrow keys (`ArrowUp`/`Down`/`Left`/`Right`) move across individual letters. Every interactive element has a `4px solid` `:focus-visible` outline with a `3px` offset and a `"Skip to the guess box"` link at the top of the page.
  - **Large target sizes and confirmation safeguards:** All buttons, radio controls, and on-screen keyboard keys enforce `min-height: 2.75rem; min-width: 2.75rem` ($\ge 44 \times 44\text{ px}$). Destructive actions (**I give up** and **Start fresh for a new player**) open confirmation dialogs before acting.
- **Readable, supportive design:**
  - **Legible typography and 200% zoom:** The interface uses **Atkinson Hyperlegible** (designed by the Braille Institute to disambiguate similar characters such as `I`/`l`/`1` and `O`/`0`), fluid `rem` sizing, and `clamp()` board dimensions that reflow from a two-column desktop view to a single column at 200% zoom without horizontal scrolling.
  - **Memory support and persistent preferences:** All prior guesses remain on the board, the full conversation log stays visible beside the board with a **Repeat last message** button, a **How to play** modal with a live tile legend opens automatically on first visit and remains accessible via **Help**, and all settings persist in `localStorage`.

### Enhancements beyond NYT

Lexi's Word Game implements **seven enhancements across Categories A, B, and C** (exceeding the requirement of three enhancements across two categories):

1. **Category A (Cognitive Support) — "Why this letter?" explainer:**
   - *User problem:* Older adults and novice players are frequently confused by Wordle's duplicate-letter rules (e.g., why one `E` in a guess is marked `Right` or `In word` while a second `E` in the same word is marked `Not in`).
   - *Implementation & evidence:* Clicking or pressing `Enter`/`Space` on any scored board tile calls `explainTile(r, c)`, which writes and speaks a plain-language explanation tailored to that exact tile—explicitly naming when a second copy of a letter is marked `Not in` because the secret word's only copy is already counted at another position.
2. **Category A (Cognitive Support) — Private letter notebook:**
   - *User problem:* Holding candidate letters and word fragments in working memory across six turns increases cognitive fatigue (Nielsen Norman Group).
   - *Implementation & evidence:* A dedicated **My letter notebook** panel (`#notebook`) with a **Clear notebook** button lets players jot down candidate letters or patterns right next to the board without affecting gameplay, persisted automatically in `localStorage`.
3. **Category B (Flexible Input and Output) — Voice play, spelled-letter entry, and hands-free Voice mode:**
   - *User problem:* Typing on small keyboards can be tiring for players with arthritis, tremor, or visual impairment, while standard browser speech recognition often cuts off slower speakers mid-word.
   - *Implementation & evidence:* `channels/deepgram_voice.py` proxies audio through the Rasa server to **Deepgram Nova-3** (`/webhooks/deepgram/listen`) and streams natural **Deepgram Aura-2** (`aura-2-thalia-en`) speech back (`/webhooks/deepgram/speak`, starting playback at `0.95×` speed in ~0.3 seconds). The microphone analyser waits until the player actually speaks and pauses for 1.2 seconds (up to 15 seconds total) before stopping, and regex normalization joins spelled-out letters (`"C, R, A, N, E"` $\rightarrow$ `"CRANE"`). The header **🎙️ Voice mode** button enables a continuous hands-free loop where Lexi reads each reply aloud and automatically listens for the player's next guess or question.
4. **Category B (Flexible Input and Output) — Large on-screen keyboard with QWERTY and A–Z layouts:**
   - *User problem:* Older adults who did not spend decades typing on QWERTY keyboards can struggle to locate letters quickly on a computer-layout grid.
   - *Implementation & evidence:* Players can switch the large on-screen keyboard between **QWERTY** and **Alphabetical (A to Z)** order in Settings, and each key updates with both color and symbol badges (`✓`, `●`, `✕`) as clues accumulate.
5. **Category B (Flexible Input and Output) — Adjustable pace, text size, feedback style, and motion:**
   - *User problem:* Visual and vestibular needs vary widely across older adults.
   - *Implementation & evidence:* Settings provides instant toggles for three feedback themes, three text sizes (`Normal`, `Large`, `Extra large`), read-aloud output, and animation reduction (`data-motion="reduce"` and `@media (prefers-reduced-motion: reduce)`).
6. **Category C (Emotional and Social Meaning) — Gentle tone and confirmable "I give up":**
   - *User problem:* Getting stuck on an unfamiliar word in NYT Wordle forces players to either burn random guesses in frustration or abandon the page without learning the answer.
   - *Implementation & evidence:* Lexi uses warm, non-judgmental phrasing throughout (`"That's completely fine. The word was WOMAN. This one was a tricky one! Would you like to play again?"`), never tracks losing streaks, and offers an **I give up** button (with a confirmation dialog) so players can always see the word kindly and start fresh.
7. **Category C (Emotional and Social Meaning) — Automatic save/resume and "New player" reset:**
   - *User problem:* Accidental tab closures or taking a break mid-puzzle should not erase progress, while shared workshop devices need a clean one-click reset between participants.
   - *Implementation & evidence:* Rasa stores conversation trackers and slots in SQLite (`rasa_tracker.db` in `endpoints.yml`) keyed by an anonymous UUID (`rwg.sender`), while the browser saves the board, conversation log, settings, and notebook in `localStorage`. Reloading the page restores the exact mid-game state; **Settings → Start fresh for a new player** clears local state and generates a fresh anonymous ID for the next workshop participant.

---

## 3. Reflection and remaining improvements

### Evaluation and lessons from the November usability sessions

We evaluated the game using **live usability playtesting** (with anonymous interaction logs captured in `rasa_tracker.db` across multiple play sessions on November 12–13 following our pre-workshop demo script) combined with **simulated-impairment and heuristic checks** (grayscale/monochrome verification, WCAG 2.1 contrast calculation, 200% zoom reflow, keyboard-only navigation, and Microsoft Human-AI Interaction guidelines).

**What worked well:**
- **Forgiving validation reduced anxiety:** Playtest logs showed players routinely testing spelling variations when narrowing down the last one or two letters (for example, trying `SEPNO`, `SWENE`, and `SENNE` before solving `SCENE` $\rightarrow$ `SPENT`, or testing `BAFLY`, `TARLY`, and `BARLY` while searching for `MANLY`). Because invalid words never cost a guess and immediately showed a brief toast note over the board, players could experiment freely and win games (`SPENT` in 4 guesses, `DEALT` in 5, `VIDEO` in 5) without frustration.
- **Wordle-first layout with conversational backup:** Putting the board and on-screen keyboard front and center—where typing anywhere fills the current row's tiles directly—made the core loop immediately recognizable, while keeping the Lexi chat panel beside it for rules, encouragement, and voice questions.
- **No-shame "I give up" and instant restart:** When players hit tricky words (`CHEAT`, `WOMAN`, `IRONY`, `MAYBE`), they used **I give up** and immediately replied `"Yes"` or clicked **Play again** to start another round, confirming that a kind exit keeps engagement high.

**Issues discovered during testing and how we fixed them:**
1. **Conversational speech mistaken for a 5-letter guess:** During voice testing, a participant said `"hello can you hear me"` (`rasa_tracker.db`, Nov 12 14:45), and the LLM extracted `"HELLO"` as a 5-letter guess, costing a turn—prompting the tester to reply, `"you shouldn't just take the first word no should you"`.
   - *Fix:* We tightened `make_wordle_guess` in `data/wordle/play.yml` so multi-word sentences or questions (`"hello can you hear me"`, `"you shouldn't take the first word"`) are never treated as guesses unless the player explicitly names a word to guess, while a lone word like `"HELLO"` on its own remains a valid guess.
2. **Valid 5-letter guesses hijacked by "give up" or "new game" intents:** When a player guessed the valid 5-letter word `"ABORT"` (`Nov 12 15:20`), the LLM routed it to `give_up_wordle`, prematurely ending the game and revealing `"AMONG"`. Similarly, typing `"Really"` (`15:13`) triggered `start_wordle`.
   - *Fix:* We added `lone_word_guess(tracker)` in `actions/action_wordle.py` as a deterministic guard inside `ActionStartWordle` and `ActionGiveUp`: whenever a game is active and the user's entire message is a single 5-letter alphabetic word, Python intercepts it and scores it as a guess. We also removed `"abort"` from the secret answer list (`REMOVE` in `game/curate.py`) while keeping it valid as a guess.
3. **Discoverability of voice features:** A tester typed `"is there a voice mode"` in chat (`Nov 12 14:39`) and hit the fallback message because voice controls were only in the UI.
   - *Fix:* We added the `voice_mode` flow (`data/wordle/play.yml` and `utter_voice_mode` in `domain/wordle.yml`) with interactive chat buttons (**🎙️ Start voice mode** and **🔊 Read aloud only**) that directly toggle the web page's voice state, and placed a prominent **🎙️ Voice mode** toggle button in the top navigation bar.
4. **Stray punctuation/numbers and default text scaling:** Logs showed stray symbols (`"--=-"`, `",,,bravt"`) and speech-to-text number homophones (`"80 I e u"` for `"ADIEU"`). In addition, starting at `Large` text size pushed the bottom of the keyboard below the fold on 13-inch laptop screens.
   - *Fix:* We restricted keyboard tile input to letters only (`currentLetters()`), added the voice spelling tip (`SPELL_TIP`) when spoken input fails validation, and set the default text size to `Normal` (`112.5%` / `18px`) while keeping `Large` and `Extra large` one click away in Settings.

### Remaining improvements for future iterations

If we had another sprint after the November 16 workshop, we would prioritize four improvements:

1. **Spoken homophone normalization for voice guesses:** When a player says `"adieu"` out loud, speech-to-text occasionally transcribes it as `"80 I e u"` or `"a view"`. Adding a phonetic fallback table (or matching spoken phrases against `ALLOWED` using pronunciation similarity before rejecting) would make single-word voice guessing even more forgiving without requiring the player to spell the word out.
2. **Tiered player-controlled hints (Category A):** While `"Why this letter?"` explains past guesses and `"I give up"` ends the game, players who have one or two guesses left (`_ E A _ T`) sometimes want a small nudge rather than the full answer. We would add an optional **Hint** button offering two gentle, deterministic tiers computed in `game/wordle.py`: a vowel/category clue first (e.g., `"The word has 2 vowels"`), followed by revealing one unguessed position if requested.
3. **Post-game word definitions and vocabulary journal (Category D):** Showing a brief, plain-English definition and example sentence in the game-over dialog (`#end-dlg`) and saving solved words to a local "Words I've Found" journal would add lasting educational value after each round.
4. **Per-player guess limit setting (Category C):** `game/wordle.py` already notes that `MAX_GUESSES` can be raised per game; exposing a choice of **6 guesses (Standard)**, **8 guesses (Relaxed)**, or **Unlimited guesses** in Settings would support players who want to solve every puzzle at their own pace without ever running out of turns.
