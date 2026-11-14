########################################
# Name: Salvador Lomeli
# Course: AI 380 Human-AI Interaction - HW3: Wordle for Everyone
# GenAI: Claude (Claude Code) helped write this curation script.
# Description: G7 - builds game/answers.txt, the answer pool, from english.py
#              so players are only asked to guess common, familiar words.
#
# Run from the hw3/ folder:   python -m game.curate
# Requires:                   wordfreq  (pip install wordfreq)
#
# Method (each step's count is printed for the design summary):
#   1. Start with every 5-letter, letters-only word in english.py.
#   2. Keep common words: wordfreq Zipf frequency >= MIN_ZIPF.
#      (Zipf 3.5 ~ a word seen a few times per million words of everyday English.)
#   3. Drop simple inflections that make weak answers:
#      plurals (CARDS -> CARD) and past tenses (BAKED -> BAKE / AIMED -> AIM).
#   4. Drop offensive words and anything removed during manual review
#      (listed in REMOVE below, so re-running keeps those decisions).
########################################

from pathlib import Path

from wordfreq import zipf_frequency

from .english import ENGLISH_WORDS
from .wordle import ALLOWED

MIN_ZIPF = 3.5
OUTPUT = Path(__file__).parent / "answers.txt"

ALL_WORDS = set(ENGLISH_WORDS)

# Offensive or upsetting words, plus words removed during manual review.
# Add to this set while skimming answers.txt, then re-run the script.
REMOVE = {
    # offensive / crude
    "bitch", "whore", "slut", "pussy", "dicks", "penis", "porno", "sexes",
    "semen", "boobs", "horny", "faggy", "nigga", "retard", "kinky", "pimps",
    "skank", "twats", "prick", "crack",
    # upsetting themes for a relaxing game
    "death", "dying", "rapes", "raped", "rapist", "kills", "nazis", "slave",
    "suicide", "tumor", "cancer", "abort", "booze",
    "abuse", "lynch", "widow", "fetus", "gypsy", "queer", "trans", "trump",
    "moron", "idiot", "willy", "sperm", "urine", "vomit", "bowel", "booty",
    "obese", "naked", "erect",
    # manual review: names, places, brands (english.py stores them lowercase)
    "ariel", "benny", "billy", "bobby", "brent", "brock", "burke", "chang",
    "chevy", "colin", "donna", "erica", "harry", "henry", "hogan", "homer",
    "jenny", "jerry", "jesse", "jimmy", "jones", "kelly", "kerry", "laura",
    "lewis", "logan", "louis", "maria", "molly", "nancy", "pedro", "perry",
    "peter", "ralph", "randy", "riley", "roger", "romeo", "sally", "shawn",
    "silva", "smith", "sonny", "terry", "tommy", "weber",
    "calif", "chile", "china", "congo", "costa", "devon", "greek", "japan",
    "leone", "monte", "paris", "roman", "swiss", "texas", "welsh", "dutch",
    "honda", "tesla", "yahoo", "morse", "bible",
    # manual review: slang, prefixes, jargon, or British spellings of US words
    "gimme", "inter", "hydro", "amino", "litre", "metre", "fibre",
}


def is_inflection(word: str) -> bool:
    """True for simple plurals and past tenses whose base word is also a word."""
    if word.endswith("s") and not word.endswith("ss"):
        if word[:-1] in ALL_WORDS:                       # cards -> card
            return True
        if word.endswith("es") and word[:-2] in ALL_WORDS:  # boxes -> box
            return True
        if word.endswith("ies") and word[:-3] + "y" in ALL_WORDS:  # cries -> cry
            return True
    if word.endswith("ed"):
        if word[:-2] in ALL_WORDS or word[:-1] in ALL_WORDS:  # aimed -> aim, baked -> bake
            return True
        if word.endswith("ied") and word[:-3] + "y" in ALL_WORDS:  # cried -> cry
            return True
    return False


def curate() -> list[str]:
    step1 = sorted(ALLOWED)
    print(f"1. Five-letter words in english.py:        {len(step1):>5}")

    step2 = [w for w in step1 if zipf_frequency(w, "en") >= MIN_ZIPF]
    print(f"2. Common words (Zipf >= {MIN_ZIPF}):            {len(step2):>5}")

    step3 = [w for w in step2 if not is_inflection(w)]
    print(f"3. Without plurals / past tenses:          {len(step3):>5}")

    step4 = [w for w in step3 if w not in REMOVE]
    print(f"4. Without offensive / reviewed-out words: {len(step4):>5}")

    return step4


if __name__ == "__main__":
    answers = curate()
    OUTPUT.write_text("\n".join(answers) + "\n")
    print(f"\nWrote {len(answers)} answers to {OUTPUT}")
