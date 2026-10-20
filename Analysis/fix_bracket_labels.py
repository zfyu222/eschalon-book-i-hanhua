"""Translate bracketed inline labels that were left in English.

Standalone rows such as ``[Give ceramic crucible]`` were already translated,
but the same label embedded inside a dialogue line was not. Reuse the existing
standalone wording so both forms read identically.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

# Wording for the Give* labels follows the already-translated standalone rows.
BRACKET_FIX = {
    "[BACK]": "[返回]",
    "[END]": "[结束]",
    "[EXIT]": "[离开]",
    "[LOCKED]": "[锁定]",
    "[Give 75 gold]": "[支付75枚金币]",
    "[Give Divine Ore to Gunther]": "[把神圣矿石交给冈瑟]",
    "[Give Purest Water to Oolaseph]": "[将至纯之水交给奥拉塞夫]",
    "[Give ceramic crucible]": "[交出陶瓷坩埚]",
}


def load(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\r\n")
        for value in rows:
            writer.writerow([value])


def main():
    sources = load(SOURCE)
    targets = load(TRANSLATED)
    if len(sources) != len(targets):
        print(f"row mismatch: {len(sources)} vs {len(targets)}")
        return 2

    changed = []
    for index, target in enumerate(targets):
        original = target
        for english, chinese in BRACKET_FIX.items():
            if english in target:
                target = target.replace(english, chinese)
        if target != original:
            targets[index] = target
            changed.append(index + 1)

    write(TRANSLATED, targets)
    print(f"rows changed: {len(changed)}")
    print("first rows:", changed[:20])
    return 0


if __name__ == "__main__":
    sys.exit(main())
