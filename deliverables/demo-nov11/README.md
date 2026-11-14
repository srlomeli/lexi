# November 11 Demo

Usability and pre-workshop demo. 

## Demo script (outline)

1. Open https://lexi.salvadorlomeli.com. A new game starts by itself.
2. Type a guess and press **Guess**. Point out the symbol and word on each tile.
3. Make a guess by pressing **Speak**, then one by spelling it ("C, R, A, N, E").
4. Enter a made-up word and show that it doesn't use up a guess.
5. Select a letter on the board to show **Why this letter?**
6. Turn on **Read aloud** and use **Repeat last message**.
7. Use the **Letter notebook**.
8. Open **Settings**: feedback style, text size, keyboard layout.
9. Reload the page to show the game picks up where it left off.
10. Press **I give up**, then start a **New game**.

## Notes and feedback from the session

Anonymous playtest logs from the usability and pre-workshop sessions (captured in `rasa_tracker.db` under random `player-<uuid>` IDs with no personal data) highlighted both what worked well and four concrete issues we fixed immediately afterward:

### What worked well

- **Unpenalized trial-and-error reduced frustration:** Players frequently tested candidate spellings when narrowing down the last one or two letters (for example, trying `SEPNO`, `SWENE`, and `SENNE` before solving `SCENE` $\rightarrow$ `SPENT` in 4 guesses, or testing `BAFLY`, `TARLY`, and `BARLY` while working toward `MANLY`). Because unknown words never cost a turn and show an immediate toast note over the board, players explored freely and completed multiple back-to-back games (`SPENT` in 4, `DEALT` in 5, `VIDEO` in 5).
- **Direct board typing and clear tile labels:** Having the 6-row board and large on-screen keyboard front and center—with `✓ Right`, `● In word`, and `✕ Not in` printed directly on every scored tile—let players start guessing right away without reading a manual.
- **Gentle "I give up" kept players engaged:** When stuck on harder words (`CHEAT`, `WOMAN`, `IRONY`, `MAYBE`), players used **I give up** and immediately answered `"Yes"` or pressed **Play again** to start another round.

### Issues observed and fixes made

1. **Conversational speech misread as a 5-letter guess:**
   - *Observed:* A tester checking their microphone said `"hello can you hear me"`, and the LLM extracted `"HELLO"` as a 5-letter guess and used a turn—prompting the tester to reply, `"you shouldn't just take the first word no should you"`.
   - *Fixed:* Updated the `make_wordle_guess` flow description in `data/wordle/play.yml` so multi-word sentences or questions (`"hello can you hear me"`, `"you shouldn't take the first word"`) are never treated as guesses unless the player explicitly names a word to guess, while a single word like `"HELLO"` on its own still counts as a guess.
2. **Real 5-letter guesses (`ABORT`, `REALLY`) triggering other flows:**
   - *Observed:* When a player guessed `"ABORT"` mid-game, the LLM matched `give_up_wordle` and ended the game early (revealing `"AMONG"`). In another round, `"Really"` triggered `start_wordle`.
   - *Fixed:* Added `lone_word_guess(tracker)` in `actions/action_wordle.py` inside both `ActionStartWordle` and `ActionGiveUp` so any single 5-letter alphabetic word sent during an active game is deterministically scored as a guess. Also added `"abort"` to the `REMOVE` set in `game/curate.py` so it is never chosen as a secret answer while remaining valid as a guess.
3. **Asking about voice mode in chat:**
   - *Observed:* A tester typed `"is there a voice mode"` in the chat box and received the generic fallback reply.
   - *Fixed:* Added the `voice_mode` flow (`data/wordle/play.yml` and `utter_voice_mode` in `domain/wordle.yml`) with one-click chat buttons (**🎙️ Start voice mode** and **🔊 Read aloud only**), plus a persistent **🎙️ Voice mode** toggle button in the top header that reads replies aloud with Deepgram Aura-2 and automatically listens for the player's next turn.
4. **Stray symbols, spoken homophones, and laptop screen fit:**
   - *Observed:* Logs showed stray punctuation (`"--=-"`, `",,,bravt"`) and speech-to-text number transcriptions (`"80 I e u"` for `"ADIEU"`), and the initial `Large` default text size pushed the bottom of the on-screen keyboard below the fold on 13-inch laptop screens.
   - *Fixed:* Restricted direct tile typing to letters only (`currentLetters()` in `web/index.html`), added a spelling tip (`SPELL_TIP`) when spoken guesses fail validation, and changed the default text size to `Normal` (`112.5%` / `18px`) while keeping `Large` and `Extra large` in Settings.
