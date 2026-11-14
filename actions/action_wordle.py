########################################
# Name: Salvador Lomeli
# Course: AI 380 Human-AI Interaction - HW3: Wordle for Everyone
# GenAI: Claude (Claude Code) helped write some of these Rasa custom actions.
# Description: Connects Rasa to the game rules in game/wordle.py.
#   The LLM only works out WHAT the player said (e.g. "is it crane?").
#   Everything else - picking the answer, checking and scoring guesses,
#   counting turns - happens here in deterministic Python.
########################################

import logging
import re
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

from game import wordle


def board_payload(answer: str, guesses: List[str], status: str) -> Dict[str, Any]:
    """Board state for the web page (sent as a custom JSON message)."""
    rows = [
        {"word": g.upper(), "states": wordle.score(g, answer)} for g in guesses
    ]
    payload = {
        "type": "wordle_board",
        "rows": rows,
        "max_guesses": wordle.MAX_GUESSES,
        "guesses_left": wordle.MAX_GUESSES - len(guesses),
        "keyboard": wordle.keyboard_state(guesses, answer),
        "status": status,  # "playing" | "won" | "lost"
    }
    if status != "playing":
        payload["answer"] = answer.upper()  # only revealed once the game is over
    return payload


SPELL_TIP = (
    " If I misheard you, try spelling the word one letter at a time, "
    "like C, R, A, N, E."
)

logger = logging.getLogger(__name__)


def is_voice(tracker: Tracker) -> bool:
    """True when the player is talking, not typing (e.g. Rasa's browser_audio)."""
    channel = (tracker.get_latest_input_channel() or "").lower()
    metadata = (tracker.latest_message or {}).get("metadata") or {}
    logger.info(
        "wordle input_channel=%r metadata_keys=%s", channel, sorted(metadata)
    )
    if any(k in channel for k in ("audio", "voice", "phone", "twilio")):
        return True
    # Rasa's Inspector reports "inspector" for typed AND spoken messages, so
    # also look for metadata that only the voice pipeline adds.
    voice_keys = {"merged_transcripts", "barge_in_verdict", "asr", "transcript"}
    return bool(voice_keys & set(metadata))


def say(dispatcher: CollectingDispatcher, tracker: Tracker, text: str,
        board: Dict[str, Any] | None = None) -> None:
    """Send text, plus the board data for screen channels only.

    The voice channel gets text only, so nothing like "JSON" is shown or read aloud.
    """
    if board is None or is_voice(tracker):
        dispatcher.utter_message(text=text)
    else:
        dispatcher.utter_message(text=text, json_message=board)


def lone_word_guess(tracker: Tracker) -> str | None:
    """The guess, when a game is on and the whole message is one 5-letter word.

    The LLM can mistake a real guess like ABORT or RESET for "give up" or
    "new game". A lone 5-letter word during a game is always a guess.
    """
    if not tracker.get_slot("wordle_active"):
        return None
    text = ((tracker.latest_message or {}).get("text") or "").strip()
    match = re.fullmatch(r"([A-Za-z]{%d})[.!?]?" % wordle.WORD_LENGTH, text)
    return match.group(1) if match else None


def score_guess(
    dispatcher: CollectingDispatcher, tracker: Tracker, raw_guess: str
) -> List[Dict[Text, Any]]:
    answer = tracker.get_slot("wordle_answer")
    guesses = list(tracker.get_slot("wordle_guesses") or [])

    if not answer or not tracker.get_slot("wordle_active"):
        dispatcher.utter_message(
            text="There's no game going right now. Say \"new game\" to start one."
        )
        return [SlotSet("wordle_guess", None)]

    # G4: invalid guesses get a clear message and do NOT use up a turn.
    problem = wordle.validate(raw_guess)
    if problem:
        left = wordle.MAX_GUESSES - len(guesses)
        tip = SPELL_TIP if is_voice(tracker) else ""
        dispatcher.utter_message(
            text=f"{problem} You still have {left} {'guess' if left == 1 else 'guesses'} left.{tip}"
        )
        return [SlotSet("wordle_guess", None)]

    guess = wordle.normalize(raw_guess)
    if guess in guesses:
        left = wordle.MAX_GUESSES - len(guesses)
        dispatcher.utter_message(
            text=(
                f"You already tried {guess.upper()}, so I didn't count it again. "
                f"You still have {left} {'guess' if left == 1 else 'guesses'} left."
            )
        )
        return [SlotSet("wordle_guess", None)]
    guesses.append(guess)
    states = wordle.score(guess, answer)
    result = wordle.describe(guess, states)
    left = wordle.MAX_GUESSES - len(guesses)

    if wordle.is_win(guess, answer):
        status = "won"
        text = f"{result}\n\n{wordle.end_message(True, answer, len(guesses))}"
    elif left == 0:
        status = "lost"
        text = f"{result}\n\n{wordle.end_message(False, answer, len(guesses))}"
    else:
        status = "playing"
        text = f"{result}\n\nYou have {left} {'guess' if left == 1 else 'guesses'} left."

    say(dispatcher, tracker, text, board_payload(answer, guesses, status))
    return [
        SlotSet("wordle_guesses", guesses),
        SlotSet("wordle_active", status == "playing"),
        SlotSet("wordle_guess", None),
    ]


class ActionStartWordle(Action):
    """G1: start a new game with a fresh hidden answer."""

    def name(self) -> Text:
        return "action_start_wordle"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        word = lone_word_guess(tracker)
        if word:
            return score_guess(dispatcher, tracker, word)
        answer = wordle.new_answer()
        say(
            dispatcher,
            tracker,
            f"New game! I'm thinking of a {wordle.WORD_LENGTH}-letter word. "
            f"You have {wordle.MAX_GUESSES} guesses, and there's no timer, so take your time. "
            "Type or say any 5-letter word to make your first guess.",
            board_payload(answer, [], "playing"),
        )
        return [
            SlotSet("wordle_answer", answer),
            SlotSet("wordle_guesses", []),
            SlotSet("wordle_active", True),
        ]


class ActionScoreGuess(Action):
    """G3-G6: check the guess, score it, and end the game on a win or loss."""

    def name(self) -> Text:
        return "action_score_guess"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        return score_guess(dispatcher, tracker, tracker.get_slot("wordle_guess") or "")


class ActionGiveUp(Action):
    """Gentle "I give up": kindly reveal the word and offer a new game."""

    def name(self) -> Text:
        return "action_give_up"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        word = lone_word_guess(tracker)
        if word:
            return score_guess(dispatcher, tracker, word)
        answer = tracker.get_slot("wordle_answer")
        if not answer or not tracker.get_slot("wordle_active"):
            dispatcher.utter_message(
                text="There's no game going right now. Say \"new game\" whenever you'd like to play."
            )
            return []
        guesses = list(tracker.get_slot("wordle_guesses") or [])
        say(
            dispatcher,
            tracker,
            f"That's completely fine. The word was {answer.upper()}. "
            "This one was a tricky one! Would you like to play again?",
            board_payload(answer, guesses, "lost"),
        )
        return [SlotSet("wordle_active", False)]
