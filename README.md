# Lexi's Word Game

A relaxing Wordle-style word game made for older adults. Lexi, a friendly
chat assistant, picks a secret 5-letter word and helps you find it. You can
type or speak your guesses. There is no timer and no pressure.

AI 380: Human-AI Interaction, HW3: Wordle for Everyone (Fall 2026).

## Play the game

**Live link:** [lexi.salvadorlomeli.com](https://lexi.salvadorlomeli.com/)

Open the link in Chrome, Edge, or Safari. A new game starts by itself.

The public site runs on a Google Cloud VM; see `deploy/gcp/README.md`.

## How to play

1. Lexi picks a secret 5-letter word. You have **6 guesses**.
2. Type a word, tap the letters on the screen, or press **Speak** and say it.
   You can also spell it out, like "C, R, A, N, E". Then press **Guess**.
3. Each letter gets one of three results. Every result has a symbol and a word,
   so you don't need to tell colors apart:

   | Symbol | Word on the tile | Meaning |
   |---|---|---|
   | ✓ | Right | Right letter, right spot |
   | ● | In word | In the word, but in a different spot |
   | ✕ | Not in | Not in the word |

4. Words Lexi doesn't know, or words that are too short or too long, **never
   use up a guess**.
5. Stuck? Press **I give up** and Lexi will kindly tell you the word.
   You can always start a **New game**.

### Helpful extras

- **Why this letter?** Select any letter on the board to read or hear why it got its result.
- **Read aloud.** Turn it on in **Settings** to hear Lexi's replies.
- **Repeat last message.** Hear or read Lexi's last reply again.
- **Letter notebook.** Jot down letters you suspect. Only you see it.
- **Settings.** Choose the feedback style (colors and symbols, symbols only, or
  high-contrast dark), the text size, and an A-to-Z or computer-style keyboard.
  Your choices are saved on your device.
- **Pick up where you left off.** If you close the page, your game is still
  there when you come back.
- **Keyboard only.** Type letters anywhere, press Enter to guess and Backspace
  to delete. Use the arrow keys to move between letters on the board.
- **Help** is always at the top of the page.

## Run it yourself

You need Python 3.11, a Rasa Pro license, a Gemini API key, and, for Rasa's
voice mode, a Deepgram API key.

1. Install Rasa Pro and the project's Python packages into a virtual environment:

   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install rasa-pro wordfreq
   ```

2. Create a `.env` file in this folder (it is not committed):

   ```
   RASA_LICENSE=...
   GEMINI_API_KEY=...
   DEEPGRAM_API_KEY=...
   ```

3. Train the assistant and start the server:

   ```bash
   rasa train
   rasa run --cors "*"
   ```

4. Open `web/index.html` in your browser. If the server runs on a different
   address than `http://localhost:5005`, change it under
   **Settings → Game server**.

To try text and voice chat without the web page, run `rasa inspect` instead.
It uses port 5005 too, so stop `rasa run` first.

## How it works

- **The rules are plain Python** (`game/wordle.py`). Picking the answer,
  checking guesses against `english.py`, and scoring letters, including
  repeated letters, never go through the language model.
- **Rasa Pro handles the conversation** (`data/`, `domain/`, `actions/`).
  The language model (Gemini 3.1 Flash-Lite) only works out what the player
  meant, for example that "is it crane?" is a guess.
- **The web page** (`web/index.html`) sends messages to Rasa and draws the board.
  `web/README.md` lists its accessibility features and contrast ratios.

```
actions/   Rasa custom actions that connect the chat to the game rules
data/      Conversation flows
domain/    Replies, slots, and actions
game/      Game rules, the word list (english.py), and the answer list
web/       The web page players use
tests/     End-to-end conversation tests
```

## Choosing the answers

`english.py` has 8,548 five-letter words, many of them obscure. The script
`game/curate.py` builds the answer list in `game/answers.txt`:

| Step | Words left |
|---|---|
| 1. Five-letter, letters-only words in `english.py` | 8,548 |
| 2. Keep common words (wordfreq Zipf frequency ≥ 3.5) | 1,740 |
| 3. Remove plurals and past tenses (CARDS, BAKED) | 1,248 |
| 4. Remove offensive or upsetting words, names, places, brands, and slang (manual review) | 1,143 |

Every word in `english.py` is still accepted as a guess; only the answers are
limited. To rebuild the list, run `python -m game.curate`.

## Privacy

The game asks for no names or personal details. The web page stores only your
settings, board, conversation, and notebook in your own browser, under a random
player ID. Spoken guesses are turned into text by the browser and are not recorded.

## Credits and AI use

- `english.py` was provided by the course.
- The letter-scoring logic is adapted from my earlier Wordle assignment,
  written with Sam from the QUAD.
- Common-word frequencies come from the [wordfreq](https://pypi.org/project/wordfreq/) library.
- Claude (Claude Code) helped restructure the game rules and helped write some of the Rasa
  custom actions, the curation script, and the web page. Each file's header
  notes where AI was used for assistance.
- Built with [Rasa Pro](https://rasa.com/docs/pro/) and Google Gemini.
