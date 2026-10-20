"""Audit translation quality gaps that the coverage checks cannot see.

Four independent checks over the source/target column pair:

  empty      target is blank while source carries text
  no-cjk     target has letters but no CJK at all (translation never applied)
  residual   target keeps runs of English words outside a small allowlist
  markers    count of style/placeholder markers differs from the source

Results are written to text_gaps_report.txt; the console stays ASCII-safe.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"
OUT = Path(__file__).resolve().parent / "text_gaps_report.txt"

CJK = re.compile(r"[\u3400-\u9fff\uf900-\ufaff]")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")

# Product names, engine tokens and abbreviations that legitimately stay Latin.
ALLOW = {
    "directx", "opengl", "steam", "steamappid", "eschalon", "basilisk",
    "books", "book", "ttf", "png", "csv", "pak", "exe", "html", "htm",
    "gold", "pieces", "hp", "mana", "dmg", "res", "at", "sk", "ar", "exp",
    "sql", "ai", "usb", "dvd", "cd", "gb", "mb", "kb",
}

# Markers the engine treats as control characters, not content.
MARKERS = ["*", "&", "^", "$", "||", "\\n"]


def load(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


def latin_residue(text):
    words = [w.lower() for w in LATIN_WORD.findall(text)]
    keep = [w for w in words if w not in ALLOW]
    return keep


def main():
    source = load(SOURCE)
    target = load(TRANSLATED)
    if len(source) != len(target):
        print(f"row mismatch: {len(source)} vs {len(target)}")
        return 2

    empty, no_cjk, residual, markers = [], [], [], []

    for index, (src, dst) in enumerate(zip(source, target), start=1):
        if not src.strip():
            continue
        if not dst.strip():
            empty.append((index, src))
            continue
        if LATIN_WORD.search(src) and not CJK.search(dst):
            no_cjk.append((index, src, dst))
        keep = latin_residue(dst)
        if len(keep) >= 2:
            residual.append((index, src, dst, keep))
        for marker in MARKERS:
            if src.count(marker) != dst.count(marker):
                markers.append((index, marker, src.count(marker), dst.count(marker), src, dst))
                break

    print(f"rows            : {len(source)}")
    print(f"empty target    : {len(empty)}")
    print(f"no CJK in target: {len(no_cjk)}")
    print(f"latin residue   : {len(residual)}")
    print(f"marker mismatch : {len(markers)}")

    with OUT.open("w", encoding="utf-8") as stream:
        stream.write("== empty target ==\n")
        for index, src in empty:
            stream.write(f"{index}\t{src}\n")
        stream.write("\n== no CJK in target ==\n")
        for index, src, dst in no_cjk:
            stream.write(f"{index}\t{src}\t=>\t{dst}\n")
        stream.write("\n== latin residue ==\n")
        for index, src, dst, keep in residual:
            stream.write(f"{index}\t{src[:80]}\t=>\t{dst[:80]}\t{keep}\n")
        stream.write("\n== marker mismatch ==\n")
        for index, marker, a, b, src, dst in markers:
            stream.write(f"{index}\t{marker!r} {a}->{b}\t{src[:60]}\t=>\t{dst[:60]}\n")

    print(f"\nwritten {OUT}")

    print("\n-- no CJK sample --")
    for index, src, dst in no_cjk[:15]:
        print(f"  {index} {src[:60]!r} => {dst[:50]!r}")
    print("\n-- residual sample --")
    for index, src, dst, keep in residual[:15]:
        print(f"  {index} {keep} | {dst[:60]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
