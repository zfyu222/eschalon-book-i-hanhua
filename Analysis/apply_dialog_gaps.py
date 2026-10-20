"""Add short dialogue options the runtime reported as unmatched.

Every key here comes from runtime_untranslated.jsonl and was confirmed absent
from the corpus. Keys are stored in exactly the form the engine draws:
record quotes kept, branch-id byte removed.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

PAIRS = {
    '"Hello?"': '"你好？"',
    '"No pay? No way."': '"没有报酬？想都别想。"',
    '"Eh, thanks." [BACK]': '"呃，谢谢。" [返回]',
    '"Thank you." [BACK]': '"谢谢。" [返回]',
    '"Goodbye." [END]': '"再见。" [结束]',
    # Standalone markers; the engine also draws the words without brackets.
    "[BACK]": "[返回]",
    "[END]": "[结束]",
    "BACK": "返回",
    "END": "结束",
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

    existing = set(sources)
    added = 0
    for source, target in PAIRS.items():
        if source in existing:
            print(f"skip existing: {source!r}")
            continue
        sources.append(source)
        targets.append(target)
        existing.add(source)
        added += 1
        print(f"added: {source!r} -> {target!r}")

    write(SOURCE, sources)
    write(TRANSLATED, targets)
    print(f"appended {added}, total {len(sources)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
