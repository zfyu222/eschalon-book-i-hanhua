"""Fill translations for visible rows whose text still equals the source.

Scope: rows confirmed as player-visible English left untranslated.
Engine command chains and identifiers are deliberately untouched.

Two kinds of repair:
  1. existing corpus row -> replace its target column
  2. embedded body absent from corpus -> append a source/target pair
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

# Existing rows: source text -> new Chinese target.
REPLACE = {
    "150 Gold Pieces": "150 金币",
    "[Attribute]": "[属性]",
    "Nor'lander": "诺兰达人",
}

# Bodies shown by the engine after parsing message(...), absent from corpus.
APPEND = {
    "This portal has become inactive.":
        "这座传送门已经失效。",
    "This lever is locked. The lighthouse fire cannot be extinguished this way.":
        "这根拉杆被锁住了，无法用这种方式熄灭灯塔之火。",
}


def load(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


def write(path, rows):
    # The corpus carries no BOM; keep that so hooks and other tools see the
    # same byte layout as before the repair.
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

    replaced = 0
    for index, source in enumerate(sources):
        if source in REPLACE and sources[index] == targets[index]:
            targets[index] = REPLACE[source]
            replaced += 1
            print(f"fixed row {index + 1}: {source!r} -> {targets[index]!r}")

    existing = set(sources)
    added = 0
    for source, target in APPEND.items():
        if source in existing:
            print(f"skip existing: {source!r}")
            continue
        sources.append(source)
        targets.append(target)
        added += 1
        print(f"appended: {source!r} -> {target!r}")

    if len(sources) != len(targets):
        print("internal error: row count diverged")
        return 3

    write(SOURCE, sources)
    write(TRANSLATED, targets)
    print(f"\nreplaced={replaced} appended={added} total={len(sources)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
