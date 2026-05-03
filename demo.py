#!/usr/bin/env python3
"""Print the latest round's scoreboard so you can see what this repo
produces without setting anything up.

Run: python3 demo.py
"""

from __future__ import annotations

import pathlib
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent
REVIEWS_DIR = REPO_ROOT / "results" / "reviews"


def latest_review() -> pathlib.Path | None:
    candidates = sorted(REVIEWS_DIR.glob("sandbox-*.md"))
    return candidates[-1] if candidates else None


def extract_section(text: str, heading: str) -> str:
    """Return the body of `## <heading>` up to (but not including) the
    next `## ` heading. Returns empty string if not found."""
    marker = f"## {heading}"
    start = text.find(marker)
    if start < 0:
        return ""
    after = text.find("\n## ", start + len(marker))
    return text[start:after if after > 0 else len(text)].rstrip()


def main() -> int:
    review = latest_review()
    if review is None:
        print("# sandbox — no captured rounds yet")
        print()
        print("No review file at results/reviews/sandbox-*.md.")
        print()
        print("Round 1's methodology was superseded; its artifacts were")
        print("dropped. Run a fresh round per README → Try it, then this")
        print("script will print its scoreboard.")
        return 0

    text = review.read_text()
    scoreboard = extract_section(text, "Scoreboard")

    print(f"# sandbox — latest round preview")
    print()
    print(f"Source: {review.relative_to(REPO_ROOT)}")
    print()
    print(scoreboard if scoreboard else "(no Scoreboard section in review)")
    print()
    print(f"Full review:  {review.relative_to(REPO_ROOT)}")
    print(f"How to run:   README.md → Try it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
