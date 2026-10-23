"""Tiny persistence helper for the high score (JSON file next to main.py)."""
import json

import config as C


def load_high_score() -> int:
    try:
        with open(C.HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            return max(0, int(json.load(f).get("high_score", 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def save_high_score(score: int) -> None:
    try:
        with open(C.HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            json.dump({"high_score": int(score)}, f)
    except OSError as exc:
        print(f"[storage] could not save high score: {exc}")
