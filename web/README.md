# Web page for Lexi's Word Game

`index.html` is the web front end. It sends what the player types or says to
Rasa's REST channel and draws the board from the `wordle_board` JSON that
`actions/action_wordle.py` sends. All rules (answers, validation, scoring) stay
in Python.

## Run it

1. From the `hw3/` folder: `rasa train`, then `rasa run --cors "*"`
   (the REST channel listens on http://localhost:5005).
2. Open `web/index.html` in Chrome, Edge, or Safari. A new game starts on its own.
   If Rasa is on another address, change it under **Settings → Game server**.

## Public demo link (https://lexi.salvadorlomeli.com)

A free Cloudflare Tunnel puts the game on `lexi.salvadorlomeli.com` while this
laptop runs it. `/webhooks/...` goes to Rasa (port 5005) and everything else to
the page (port 8080), so the page and Rasa share one https address and the
microphone works. API keys stay in `.env` on the laptop.

**One-time setup**

1. `brew install cloudflared`
2. `cloudflared tunnel login` (opens a browser; pick `salvadorlomeli.com`)
3. `cloudflared tunnel create lexi`, then put the printed tunnel ID into
   `deploy/cloudflared.yml` (`credentials-file`).
4. `cloudflared tunnel route dns lexi lexi.salvadorlomeli.com`

**Each demo**

From the `hw3/` folder:

- `./deploy/lexi.sh on` starts Rasa, the page and the tunnel in the background
  (it skips anything already running), then share https://lexi.salvadorlomeli.com
- `./deploy/lexi.sh off` takes the site offline. It stops Rasa only if `on`
  started it, so nobody keeps using the Gemini and Deepgram quota.
- `./deploy/lexi.sh status` shows what's running and whether the site is up.
- `./deploy/lexi.sh logs` shows recent log lines if something goes wrong.

The page talks to whichever site it was opened from. Opened as a file or on
`localhost`, it uses `http://localhost:5005`. A `?server=https://...` link
overrides the address.

## How the page meets the accessibility priorities

| Priority | What the page does |
|---|---|
| Perceivable feedback | Every letter shows a symbol **and** a word (✓ Right, ● In word, ✕ Not in), plus a different border (solid / dashed / dotted). "Not in" letters are also struck through. A legend opens in a How to play pop-up on first visit and is always one press away under Help. Each guess has a plain-language sentence for screen readers, and Lexi's replies are announced in a live region. |
| Color-free check | The "Symbols and words only" style uses no hue at all, so it is a built-in grayscale check. |
| Operable, forgiving | Plays fully by keyboard (type anywhere, Enter, Backspace; arrow keys on the board). Big focus ring. Every control is at least 44 × 44 px. There are no timers. A word that isn't counted stays in the box, selected, so it's easy to fix. "I give up" asks first. Help is in the header and under the board. |
| Readable, supportive | Atkinson Hyperlegible font, sizes in rem, layout reflows at 200% zoom. Earlier guesses and the whole conversation stay visible. A "Repeat last message" button replays the latest reply. The feedback style, text size, keyboard layout, read-aloud, and animation choices are saved on the device. |

## Enhancements in the page

- **A: "Why this letter?" explainer.** Select any scored letter to read or hear why it got that result, including repeated-letter cases.
- **A: Letter notebook.** A private scratch area that doesn't affect the game.
- **B: Voice play.** The Speak buttons (under the guess box and in the chat) record your voice and send it to Deepgram through the Rasa server. Listening stops when you pause. Spelled-out letters ("C, R, A, N, E") are joined into one word.
- **B: Voice mode.** The 🎙️ Voice mode button in the header turns on a hands-free conversation: Lexi reads each reply aloud with a natural Deepgram voice (Aura 2), then listens for your answer. Read aloud on its own is still in Settings.
- **B: Alternative input.** A large on-screen keyboard, in QWERTY or A to Z order.
- **B: Adjustable layout.** Text size, feedback style, and animation options.
- **C: Gentle "I give up".** Asks to confirm, then kindly shows the word.
- **Wordle-style layout.** Board on top with the on-screen keyboard right under it; letters go straight into the tiles (a hidden guess box keeps it screen-reader friendly). Short pop-up notes for guesses that don't count, and a game-over pop-up with Play again. Full replies stay in the Lexi chat.
- **C: New player.** **Settings → New player** (it asks first) clears the conversation, board, notebook and display settings on this device and gets a new anonymous id, so Rasa starts a fresh session. Only the server address is kept.
- **C: Save and resume.** The board, conversation, and notebook are kept on the device. Rasa keeps the game for the same anonymous player id while the server is running.

## Contrast ratios (WCAG 2.1 formula)

Text needs 4.5:1 or more; tile edges, borders, and the focus ring need 3:1 or more.

```
== standard
  text on page                 15.53:1  PASS (needs 4.5)
  text on panel                16.48:1  PASS (needs 4.5)
  muted on page                 8.35:1  PASS (needs 4.5)
  muted on panel                8.86:1  PASS (needs 4.5)
  button text on primary        6.70:1  PASS (needs 4.5)
  danger on panel               7.33:1  PASS (needs 4.5)
  Right: letter on tile         6.17:1  PASS (needs 4.5)
  In word: letter on tile       9.82:1  PASS (needs 4.5)
  Not in: letter on tile        9.94:1  PASS (needs 4.5)
  Right tile edge vs page       5.81:1  PASS (needs 3)
  In word tile edge vs page     7.44:1  PASS (needs 3)
  Not in tile edge vs page      5.02:1  PASS (needs 3)
  Empty tile edge vs page       4.28:1  PASS (needs 3)
  Control borders vs page       4.28:1  PASS (needs 3)
  Focus ring vs page            6.31:1  PASS (needs 3)
== mono
  text on page                 15.53:1  PASS (needs 4.5)
  text on panel                16.48:1  PASS (needs 4.5)
  muted on page                 8.35:1  PASS (needs 4.5)
  muted on panel                8.86:1  PASS (needs 4.5)
  button text on primary       18.88:1  PASS (needs 4.5)
  danger on panel               7.33:1  PASS (needs 4.5)
  Right: letter on tile        18.88:1  PASS (needs 4.5)
  In word: letter on tile      18.88:1  PASS (needs 4.5)
  Not in: letter on tile        9.94:1  PASS (needs 4.5)
  Right tile edge vs page      17.79:1  PASS (needs 3)
  In word tile edge vs page    17.79:1  PASS (needs 3)
  Not in tile edge vs page      5.02:1  PASS (needs 3)
  Empty tile edge vs page       4.28:1  PASS (needs 3)
  Control borders vs page       4.28:1  PASS (needs 3)
  Focus ring vs page           17.79:1  PASS (needs 3)
== dark
  text on page                 21.00:1  PASS (needs 4.5)
  text on panel                18.73:1  PASS (needs 4.5)
  muted on page                13.62:1  PASS (needs 4.5)
  muted on panel               12.15:1  PASS (needs 4.5)
  button text on primary       14.54:1  PASS (needs 4.5)
  danger on panel               8.21:1  PASS (needs 4.5)
  Right: letter on tile        14.63:1  PASS (needs 4.5)
  In word: letter on tile      14.54:1  PASS (needs 4.5)
  Not in: letter on tile       13.62:1  PASS (needs 4.5)
  Right tile edge vs page      14.63:1  PASS (needs 3)
  In word tile edge vs page    21.00:1  PASS (needs 3)
  Not in tile edge vs page     13.62:1  PASS (needs 3)
  Empty tile edge vs page       7.84:1  PASS (needs 3)
  Control borders vs page       7.84:1  PASS (needs 3)
  Focus ring vs page           14.54:1  PASS (needs 3)
```

## Privacy

The page stores only settings, the board, the conversation, and the notebook in
the browser's local storage, under a random player id. It asks for no names or
other personal details. Voice is turned into text by the browser and is not
recorded by the game.
