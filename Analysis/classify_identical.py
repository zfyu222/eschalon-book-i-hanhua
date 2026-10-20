"""Classify corpus rows whose translation is identical to the source.

Static prose audit reported zero gaps, yet many rows still equal their source.
This script separates engine/script tokens from text a player can actually read.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent

SOURCE = PROJECT / "eschalonbook_text.csv"
TRANSLATED = PROJECT / "eschalonbook_text_translated.csv"

# Engine commands are lowercase snake_case verbs, optionally with arguments.
COMMAND_TOKEN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?:\s|$)")
TECHNICAL = re.compile(
    r"(?:[a-z]+::|https?://|\.(?:ttf|csv|pak|png|bin|ent|wav|ogg|exe)\b|"
    r"^[A-Za-z]:\\|^/|%[A-Za-z_]+%|\\n|\\t)",
    re.IGNORECASE,
)
IDENTIFIER = re.compile(r"^[A-Za-z0-9_./%\\-]+$")


def load(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


def classify(text):
    stripped = text.strip()
    if not stripped:
        return "empty"
    # Explicit script chains: "cmd arg ; cmd arg ; ..."
    if ";" in stripped and COMMAND_TOKEN.match(stripped):
        return "script"
    if TECHNICAL.search(stripped):
        return "technical"
    if COMMAND_TOKEN.match(stripped):
        return "script"
    if IDENTIFIER.match(stripped):
        return "identifier"
    # Engine echo lines such as "Map_Mouse_X,Y:" or "Alloc_Mem:".
    if re.match(r"^[A-Za-z][A-Za-z0-9_]*(?:,?[A-Za-z0-9_]+)*:$", stripped):
        return "technical"
    if not re.search(r"[A-Za-z]{2}", stripped):
        return "non-latin"
    return "visible"


def main():
    source = load(SOURCE)
    translated = load(TRANSLATED)
    if len(source) != len(translated):
        print(f"row mismatch: {len(source)} vs {len(translated)}")
        return 2

    buckets = {
        "script": [], "technical": [], "identifier": [],
        "non-latin": [], "visible": [],
    }
    for index, (src, dst) in enumerate(zip(source, translated), start=1):
        if src != dst:
            continue
        kind = classify(src)
        if kind in buckets:
            buckets[kind].append((index, src))

    for kind in ("visible", "script", "technical", "identifier", "non-latin"):
        print(f"{kind:11s}: {len(buckets[kind])}")

    out = ROOT / "identical_visible.txt"
    with out.open("w", encoding="utf-8") as stream:
        for index, text in buckets["visible"]:
            stream.write(f"{index}\t{text}\n")
    print(f"written {out} ({len(buckets['visible'])} rows)")

    print("\n--- all visible candidates ---")
    for index, text in buckets["visible"]:
        print(f"{index}\t{text[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
