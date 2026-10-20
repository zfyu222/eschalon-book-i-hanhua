"""Inspect how short dialogue options are stored.

The runtime log shows options like '"Thank you." [BACK]' failing. They may be
absent, or present only with a trailing branch-id byte.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

PROBES = [
    "Thank you.",
    "Eh, thanks.",
    "Goodbye.",
    "No pay? No way.",
    "Hello?",
    "Looking for work, eh?",
    "No way. I'm not going to risk my life",
]


def main():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [row[0] if row else "" for row in csv.reader(stream)]
    with TRANSLATED.open("r", encoding="utf-8-sig", newline="") as stream:
        targets = [row[0] if row else "" for row in csv.reader(stream)]

    for probe in PROBES:
        print(f"=== {probe!r}")
        exact = [i for i, s in enumerate(sources) if s.strip() == probe]
        loose = [i for i, s in enumerate(sources) if probe.lower() in s.lower()]
        print(f"  exact={len(exact)} loose={len(loose)}")
        for position in (exact or loose)[:6]:
            print(f"   [{position + 1}] {sources[position]!r}")
            print(f"        -> {targets[position][:70]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
