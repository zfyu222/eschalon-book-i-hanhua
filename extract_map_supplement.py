"""Append newly found .map text to Eschalon Book I's unified CSV pair.

The existing rows and translated values are preserved byte-for-byte as CSV
records. New map literals are appended at the bottom, with English copied to
the translated column so they are clearly pending translation.
"""
from __future__ import annotations

import csv
import re
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Eschalon_CN" / "data"
MASTER_SOURCE = ROOT / "eschalonbook_text.csv"
MASTER_TARGET = ROOT / "eschalonbook_text_translated.csv"
SCRIPT_WORDS = re.compile(
    r"^(?:condition|message|sound|narrative|drop_ent|destroy_script|"
    r"toggle_|port_to|alert_npcs|trigger_talk|screen_|quest|remove_item|"
    r"init_trade|map_|updatezones|areacheck)\b",
    re.IGNORECASE,
)
FILE_OR_ID = re.compile(r"^(?:[A-Za-z_][A-Za-z0-9_]*|\d+|Random)$")


def read_column(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] for row in csv.reader(stream) if row]


def clean(text: str) -> str:
    return text.strip("\x00 \t\r\n").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def add(entries: OrderedDict[str, set[str]], text: str, origin: str, *, allow_single_word: bool = False) -> None:
    text = clean(text)
    if len(text) < 2 or not re.search(r"[A-Za-z]", text):
        return
    if (FILE_OR_ID.fullmatch(text) and not allow_single_word) or SCRIPT_WORDS.match(text):
        return
    entries.setdefault(text, set()).add(origin)


def extract_map(path: Path, entries: OrderedDict[str, set[str]]) -> None:
    # Latin-1 is intentional: it preserves every byte, allowing us to split
    # the binary record data without losing the embedded ASCII fields.
    raw = path.read_bytes().decode("latin-1")

    # A few maps expose a one-word area title in their header (for example
    # ``Darkford``).  It has no space, so the general prose filter below
    # intentionally skips it; collect only title-shaped header values, never
    # the matching internal filename or asset identifier.
    for raw_title in re.findall(rb"[ -~]{3,}", path.read_bytes()[:400]):
        title = raw_title.decode("ascii").strip('"')
        if (
            title != path.stem
            and title != "EMPTY"
            and re.fullmatch(r"[A-Z][A-Za-z'-]{2,}", title)
        ):
            add(entries, title, f"data:{path.name}:title", allow_single_word=True)

    # The map's visible fields are printable ASCII sequences amid binary data.
    # Working on bytes prevents a malformed record from joining unrelated
    # lines into one candidate.
    for raw_field in re.findall(rb"[ -~]{3,}", path.read_bytes()):
        field = raw_field.decode("ascii")
        if ";" in field or SCRIPT_WORDS.match(field):
            continue
        # Binary coordinate bytes can happen to form e.g. ``Y@``.  Real map
        # prose/labels always contain a word boundary or a quoted display text.
        if " " not in field and not (field.startswith('"') and field.endswith('"')):
            continue
        add(entries, field.strip('"'), f"data:{path.name}:field")

    # Script calls carry text inside parentheses. Extract only their visible
    # arguments, never the script program itself.
    for match in re.finditer(r"(?is)\bmessage\s*\(\s*(.*?)\s*\)", raw):
        add(entries, match.group(1).strip('"'), f"data:{path.name}:message")
    for match in re.finditer(r"(?is)\bcondition\s*\(\s*(.*?)\s*\)\s*\(\s*(.*?)\s*\)\s*\(\s*(.*?)\s*\)", raw):
        for value in match.groups():
            add(entries, value.strip('"'), f"data:{path.name}:condition")


def main() -> int:
    originals = read_column(MASTER_SOURCE)
    translations = read_column(MASTER_TARGET)
    if len(originals) != len(translations):
        raise SystemExit("Main corpus source/translation rows are not aligned")
    master = set(originals)

    entries: OrderedDict[str, set[str]] = OrderedDict()
    for path in sorted(DATA.glob("*.map")):
        extract_map(path, entries)

    pending = [text for text in entries if text not in master]
    if pending:
        originals.extend(pending)
        translations.extend(pending)
        for path, values in ((MASTER_SOURCE, originals), (MASTER_TARGET, translations)):
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerows([[value] for value in values])

    print(f"Map literals discovered: {len(entries)}")
    print(f"Already covered by main corpus: {len(entries) - len(pending)}")
    print(f"New rows appended to unified corpus: {len(pending)}")
    print(f"Unified source rows: {len(originals)}")
    print(f"Unified translation rows: {len(translations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
