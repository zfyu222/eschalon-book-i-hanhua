"""Final spot-check on the last suspicious ASCII candidates.

Remaining 'uncovered' rows are mostly item-table and book-list CSV records
whose name column is translated as its own corpus entry. This verifies that
assumption and checks the two short dialogue lines that stayed unmatched.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

PROBES = [
    "And it was stolen?",
    "I can do this.",
    "Mithril Alloy Chain Boots",
    "Cloak of the Shadow",
    "A History of Thaermore",
    "The Alchemist's Cookbook",
    "Divine Ore Great Sword",
    "Recurved Composite Great Bow",
]


def main():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [row[0] if row else "" for row in csv.reader(stream)]
    with TRANSLATED.open("r", encoding="utf-8-sig", newline="") as stream:
        targets = [row[0] if row else "" for row in csv.reader(stream)]

    for probe in PROBES:
        exact = [i for i, s in enumerate(sources) if s.strip() == probe]
        loose = [i for i, s in enumerate(sources) if probe.lower() in s.lower()]
        print(f"== {probe!r} exact={len(exact)} loose={len(loose)}")
        for position in (exact or loose)[:3]:
            print(f"   {position + 1} {sources[position][:70]!r}")
            print(f"      -> {targets[position][:50]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
