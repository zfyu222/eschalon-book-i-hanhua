"""Check the map readable-text list against the corpus, normalized.

audit_uncovered.py works on raw ASCII runs, so a script line counts as one
unmatched item even when its embedded sentences are translated. This check
uses the sentence-level list produced by extract_map_text.py instead.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT / "eschalonbook_text.csv"
TRANSLATED = PROJECT / "eschalonbook_text_translated.csv"
CANDS = ROOT / "map_text_candidates.txt"

QUOTES = "\"'"


def norm(value):
    value = value.strip().strip(QUOTES).strip()
    return re.sub(r"\s+", " ", value)


def main():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [row[0] if row else "" for row in csv.reader(stream)]
    with TRANSLATED.open("r", encoding="utf-8-sig", newline="") as stream:
        targets = [row[0] if row else "" for row in csv.reader(stream)]

    index = {}
    for position, source in enumerate(sources):
        index.setdefault(norm(source), position)

    candidates = [
        line for line in CANDS.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    missing = []
    for candidate in candidates:
        key = norm(candidate)
        position = index.get(key)
        if position is None:
            missing.append((candidate, "absent"))
        elif sources[position] == targets[position]:
            missing.append((candidate, "untranslated"))

    print(f"candidates {len(candidates)}  unresolved {len(missing)}")
    for text, reason in missing:
        print(f"  [{reason}] {text[:110]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
