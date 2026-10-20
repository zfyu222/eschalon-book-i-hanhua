"""Inspect how the Father Michael dialogue is stored in the corpus.

The screenshot shows the same panel mixing Chinese and English options, so the
hook reached the panel but failed to match specific lines. This prints the
stored form of each visible paragraph to see whether whole-paragraph keys exist.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

PROBES = [
    "Standing in this small church",
    "Welcome to the Bethel of the Green Moon",
    "I am in need of healing",
    "I was hoping the Bethel would have some work",
    "I am cursed and need spiritual restoration",
    "Can you answer a few questions",
]


def main():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [row[0] if row else "" for row in csv.reader(stream)]
    with TRANSLATED.open("r", encoding="utf-8-sig", newline="") as stream:
        targets = [row[0] if row else "" for row in csv.reader(stream)]

    for probe in PROBES:
        hits = [i for i, s in enumerate(sources) if probe.lower() in s.lower()]
        print(f"=== {probe!r}  rows={len(hits)}")
        for position in hits[:5]:
            print(f"  [{position + 1}] SRC {sources[position][:160]!r}")
            print(f"        DST {targets[position][:100]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
