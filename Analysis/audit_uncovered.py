"""Find display text that never reached the translation corpus.

Previous coverage checks only read ASCII runs from the EXE. This walks every
text-bearing source the game ships with and reports strings absent from the
corpus, so genuine coverage gaps are separated from script tokens:

  exe_utf16   UTF-16LE string table in the executable (never scanned before)
  exe_ascii   ASCII runs in the executable (same pool the old audit used)
  ent         data/*.ent entity definitions
  class       data/fighter, healer, magick, ranger, rogue
  map         data/*.map
  html        help.html

Output: one file per source under Analysis/uncovered_<source>.txt
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "Eschalon_CN"
EXE = GAME / "eschalon_book_1.exe"
DATA = GAME / "data"
HELP = GAME / "help.html"
SOURCE = ROOT / "eschalonbook_text.csv"
OUTDIR = Path(__file__).resolve().parent

LATIN = re.compile(r"[A-Za-z]{2,}")
# Format strings, asset paths, config comments and file names are not prose.
SKIP = re.compile(
    r"(?:[A-Za-z]+::|https?://|^[/\\]|^[A-Za-z]:\\|^;|^#|\\.(?:ttf|csv|pak|png|bin|ent|map|wav|ogg|exe|html?|cfg|ini|vdf|dll)\b)",
    re.IGNORECASE,
)

UTF16_RUN = re.compile(rb"(?:[\x20-\x7e]\x00){4,}")
ASCII_RUN = re.compile(rb"[\x20-\x7e]{6,}")


def norm(value):
    """Compare on content, not quoting or spacing.

    Map files store strings wrapped in quotes while the corpus does not, so a
    raw comparison reports already-translated lines as missing.
    """
    value = value.strip().strip('"').strip("'").strip()
    return re.sub(r"\s+", " ", value)


def load_corpus():
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = [row[0] if row else "" for row in csv.reader(stream)]
    exact = set(rows)
    folded = {norm(r) for r in rows if r.strip()}
    return exact, folded


def wanted(text):
    value = text.strip()
    if len(value) < 4 or not LATIN.search(value):
        return False
    if SKIP.search(value):
        return False
    # A single short token is almost always an identifier.
    if len(value.split()) < 2 and len(value) < 10:
        return False
    return True


def collect(blob, pattern, decode):
    out = {}
    for match in pattern.finditer(blob):
        raw = match.group()
        try:
            value = decode(raw)
        except Exception:
            continue
        value = value.strip()
        if wanted(value):
            out.setdefault(value, 0)
    return out


def main():
    exact, folded = load_corpus()
    print(f"corpus rows: {len(exact)}")

    sources = {}
    exe_bytes = EXE.read_bytes()
    sources["exe_utf16"] = collect(
        exe_bytes, UTF16_RUN, lambda b: b.decode("utf-16-le", errors="replace")
    )
    sources["exe_ascii"] = collect(
        exe_bytes, ASCII_RUN, lambda b: b.decode("latin-1", errors="replace")
    )

    ent = {}
    for path in sorted(DATA.glob("*.ent")):
        ent.update(collect(path.read_bytes(), ASCII_RUN,
                           lambda b: b.decode("latin-1", errors="replace")))
    sources["ent"] = ent

    cls = {}
    for name in ("fighter", "healer", "magick", "ranger", "rogue"):
        path = DATA / name
        if path.exists():
            cls.update(collect(path.read_bytes(), ASCII_RUN,
                               lambda b: b.decode("latin-1", errors="replace")))
    sources["class"] = cls

    maps = {}
    for path in sorted(DATA.glob("*.map")):
        maps.update(collect(path.read_bytes(), ASCII_RUN,
                            lambda b: b.decode("latin-1", errors="replace")))
    sources["map"] = maps

    html = {}
    if HELP.exists():
        html.update(collect(HELP.read_bytes(), ASCII_RUN,
                            lambda b: b.decode("utf-8", errors="replace")))
    sources["html"] = html

    total = 0
    for name, items in sources.items():
        missing = []
        for value in items:
            if value in exact or norm(value) in folded:
                continue
            missing.append(value)
        missing.sort()
        total += len(missing)
        out = OUTDIR / f"uncovered_{name}.txt"
        out.write_text("\n".join(missing), encoding="utf-8")
        print(f"{name:12s} candidates={len(items):6d} uncovered={len(missing):5d} -> {out.name}")

    print(f"\ntotal uncovered: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
