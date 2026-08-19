"""Apply only reviewed post-translation symbol repairs for Eschalon Book I."""
from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "eschalonbook_text.csv"
TARGET = ROOT / "eschalonbook_text_translated.csv"


def read(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


source = read(SOURCE)
translated = read(TARGET)
if len(source) != len(translated):
    raise SystemExit("Source/translation CSV rows are not aligned")

# AINiee's text-code processing left source words in new square brackets after
# their already-correct Chinese translations.  These brackets do not exist in
# the original and would render visibly in-game.
for row, markers in {
    1043: ("[faith]", "[Wisdom]"),
    1044: ("[Intelligence]",),
    1045: ("[move silently]",),
    1046: ("[move silently]",),
    1048: ("[Cartography]", "[Cartography Skill]"),
    1049: ("[Dodge]", "[ToHit]"),
}.items():
    for marker in markers:
        translated[row - 1] = translated[row - 1].replace(marker, "")

# Keep only source-present formatting controls, in their intended locations.
translated[473 - 1] = re.sub(r"\s+\$$", "", translated[473 - 1])
translated[2102 - 1] = translated[2102 - 1].replace("*", "")

# & is a visible-format control in this game, not a bracketed keyboard token.
for row in (2358, 2359):
    translated[row - 1] = translated[row - 1].replace("&[返回]", "&返回")
    translated[row - 1] = translated[row - 1].replace("&[保存]", "&保存")
    translated[row - 1] = translated[row - 1].replace("&'em", "&它们")

with TARGET.open("w", encoding="utf-8-sig", newline="") as stream:
    csv.writer(stream, lineterminator="\n").writerows([[text] for text in translated])

print("Applied reviewed symbol repairs to 12 rows.")
