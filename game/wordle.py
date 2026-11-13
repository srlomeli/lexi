########################################
# Name: Salvador Lomeli
# Course: AI 380 Human-AI Interaction - HW3: Wordle for Everyone
# Collaborators: Sam from the QUAD (original scoring logic, earlier Wordle assignment)
# GenAI: Claude (Claude Code) helped restructure my earlier Wordle scoring into
#        GUI-free functions and wrote the validation messages and keyboard state.
# Description: Core game rules (G1-G7). No Rasa or UI code lives here, so the
#              rules stay deterministic and testable; the LLM never scores guesses.
########################################

import random
from pathlib import Path

from .english import ENGLISH_WORDS

WORD_LENGTH = 5

# G2: six guesses, like NYT Wordle, so players who know the original feel at home.
# (Adjustable-difficulty enhancement can raise this per game.)
MAX_GUESSES = 6

CORRECT = "correct"   # right letter, right spot
PRESENT = "present"   # in the word, different spot
ABSENT = "absent"     # not in the word

# G3: every 5-letter, letters-only word in english.py is an allowed guess.
# A set makes each lookup instant (english.py's isEnglishWord scans a list).
ALLOWED = {w for w in ENGLISH_WORDS if len(w) == WORD_LENGTH and w.isalpha()}

# G7: curated answer pool, one word per line (built by game/curate.py + manual review).
ANSWERS_FILE = Path(__file__).parent / "answers.txt"


def load_answers() -> list[str]:
    """Read the curated answer list; every answer must also be an allowed guess."""
    words = [w.strip().lower() for w in ANSWERS_FILE.read_text().split()]
    words = [w for w in words if w in ALLOWED]
    if not words:
        raise RuntimeError(
            f"{ANSWERS_FILE} is empty. Run the curation script to fill it first."
        )
    return words


ANSWERS = load_answers() if ANSWERS_FILE.exists() and ANSWERS_FILE.stat().st_size else []


def new_answer() -> str:
    """G1: pick a hidden answer for a new game."""
    pool = ANSWERS or load_answers()  # raises a clear error if answers.txt is empty
    return random.choice(pool)


def normalize(guess: str) -> str:
    """Lowercase and drop spaces/hyphens, so 'C R A N E' or ' Crane ' both work."""
    return "".join(guess.split()).replace("-", "").lower()


def validate(guess: str) -> str | None:
    """G4: return None if the guess is OK, otherwise a short, kind message.

    An invalid guess never uses up a turn; the caller only counts a guess
    when this returns None.
    """
    word = normalize(guess)
    if not word:
        return "Please type a 5-letter word."
    if not word.isalpha():
        return "Please use letters only, no numbers or symbols."
    if len(word) < WORD_LENGTH:
        return f"That word is too short: it has {len(word)} letters. Please use {WORD_LENGTH}."
    if len(word) > WORD_LENGTH:
        return f"That word is too long: it has {len(word)} letters. Please use {WORD_LENGTH}."
    if word not in ALLOWED:
        return f"I don't know the word {word.upper()}. Please try another word. This guess was not counted."
    return None


def score(guess: str, answer: str) -> list[str]:
    """G5: score each letter, handling repeated letters correctly.

    Adapted from my earlier Wordle: pass 1 marks exact matches and crosses
    those letters off; pass 2 gives "present" only while unused copies remain.
    Example: guess SPEED vs answer ABIDE -> only one E is credited.
    """
    guess, answer = normalize(guess), normalize(answer)
    states = [ABSENT] * WORD_LENGTH
    remaining = list(answer)

    # Pass 1: correct letters
    for i in range(WORD_LENGTH):
        if guess[i] == answer[i]:
            states[i] = CORRECT
            remaining[i] = "*"  # mark this letter as used

    # Pass 2: present letters (anything left stays absent)
    for i in range(WORD_LENGTH):
        if states[i] != CORRECT and guess[i] in remaining:
            states[i] = PRESENT
            remaining[remaining.index(guess[i])] = "*"

    return states


_POSITIONS = ["first", "second", "third", "fourth", "fifth"]


def describe(guess: str, states: list[str]) -> str:
    """Plain-language result for screen readers, read-aloud, and chat."""
    phrases = {
        CORRECT: "is correct",
        PRESENT: "is in the word, but in a different spot",
        ABSENT: "is not in the word",
    }
    word = normalize(guess).upper()
    parts = [
        f"{_POSITIONS[i].capitalize()} letter {word[i]} {phrases[s]}."
        for i, s in enumerate(states)
    ]
    return f"{word}: " + " ".join(parts)


def keyboard_state(guesses: list[str], answer: str) -> dict[str, str]:
    """Best state seen so far for each letter, for coloring the on-screen keyboard.

    Only upgrades (absent -> present -> correct), fixing the old bug where a key
    stayed "present" after the letter was later found in the right spot.
    """
    rank = {ABSENT: 0, PRESENT: 1, CORRECT: 2}
    keys: dict[str, str] = {}
    for g in guesses:
        for letter, s in zip(normalize(g), score(g, answer)):
            if letter not in keys or rank[s] > rank[keys[letter]]:
                keys[letter] = s
    return keys


def is_win(guess: str, answer: str) -> bool:
    return normalize(guess) == normalize(answer)


def end_message(won: bool, answer: str, guesses_used: int) -> str:
    """G6: clear, gentle win/loss message that always offers a new game."""
    if won:
        tries = "guess" if guesses_used == 1 else "guesses"
        return f"You got it! The word was {answer.upper()}, solved in {guesses_used} {tries}. Would you like to play again?"
    return f"Good effort! The word was {answer.upper()}. Would you like to play again?"
