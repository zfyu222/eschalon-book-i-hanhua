"""Check whether dialogue lines carrying trailing branch bytes are translated.

extract_offline_texts strips a one-byte branch id that follows the closing
quote. static_coverage requires the candidate to end with sentence punctuation,
so rows like '...for me?"_' are dropped from that audit entirely. This probe
checks the underlying sentences directly.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

PROBES = [
    "A talking tree wants to help me",
    "A deal is a deal, even among us",
    "I can do this.",
    "Can I ask you another question",
    "place?",
    "quality of your crypt",
    "I have killed the Hive Queen",
    "I have returned with your Chieftain",
]


def main():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        sources = [row[0] if row else "" for row in csv.reader(stream)]
    with TRANSLATED.open("r", encoding="utf-8-sig", newline="") as stream:
        targets = [row[0] if row else "" for row in csv.reader(stream)]

    for probe in PROBES:
        hits = [i for i, s in enumerate(sources) if probe.lower() in s.lower()]
        print(f"== {probe!r} rows {len(hits)}")
        for position in hits[:3]:
            print(f"   {position + 1} {sources[position][:90]!r}")
            print(f"      -> {targets[position][:60]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
