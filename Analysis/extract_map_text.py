"""Reduce raw map strings to the text a player can actually read.

Map files mix three things: display prose (grave inscriptions, object and door
descriptions), script chains, and asset file names. Only the first kind and the
bodies of message(...) calls reach the screen.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "uncovered_map.txt"
OUT = ROOT / "map_text_candidates.txt"

MESSAGE = re.compile(r"(?i)\bmessage\s*\(\s*(.+?)\s*\)", re.S)
ASSET = re.compile(r"\.(?:wav|ogg|png|map|ent|bin|csv)$", re.IGNORECASE)
COMMAND = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
NON_TEXT = re.compile(r"^[\s\d.,:;/\-]*$")


def clean(value):
    value = value.strip().strip('"').strip()
    value = re.sub(r"\s+", " ", value)
    return value


def main():
    raw = [line.strip() for line in RAW.read_text(encoding="utf-8").splitlines() if line.strip()]
    bodies = {}
    prose = {}

    for line in raw:
        value = clean(line)
        # Embedded message bodies are displayed on their own.
        for match in MESSAGE.finditer(value):
            body = clean(match.group(1))
            if len(body) >= 8 and re.search(r"[A-Za-z]{3}", body):
                bodies.setdefault(body, 0)
        # A line that is only a script chain carries no readable text itself.
        if COMMAND.match(value) or ASSET.search(value):
            continue
        if NON_TEXT.match(value):
            continue
        if len(value.split()) < 3:
            continue
        prose.setdefault(value, 0)

    merged = dict(bodies)
    for value in prose:
        merged.setdefault(value, 0)

    lines = sorted(merged)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"raw lines      : {len(raw)}")
    print(f"message bodies : {len(bodies)}")
    print(f"prose lines    : {len(prose)}")
    print(f"unique readable: {len(lines)}")
    print(f"written {OUT}")

    print("\n-- sample --")
    for value in lines[:20]:
        print("  ", repr(value[:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
