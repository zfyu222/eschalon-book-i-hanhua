"""Check why message(...) embedded text was not reported by static_coverage.

The audit reports zero gaps, yet rows such as
``message(This portal has become inactive.)`` still hold English body text.
This probe inspects the candidate set directly instead of trusting the summary.
"""

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import extract_offline_texts as ex

EXE = ROOT / "Eschalon_CN" / "eschalon_book_1.exe"
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"


def col(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


corpus_rows = col(SOURCE)
translated_rows = col(TRANSLATED)
corpus = set(corpus_rows)
untranslated_set = {
    src for src, dst in zip(corpus_rows, translated_rows) if src == dst
}

data = EXE.read_bytes()

message_values = {}
runs = re.findall(rb"[\x20-\x7e\r\n\t\xd1]{20,}", data)
print("ascii runs:", len(runs))
for run in runs:
    block = run.decode("latin-1", errors="replace")
    for match in re.finditer(r'(?i)\bmessage\s*\(\s*(.{6,300}?)\)', block, re.S):
        value = re.sub(r"^[\"']|[\"']$", "", match.group(1).strip()).strip()
        if len(value) >= 12:
            message_values.setdefault(value, 0)
        message_values[value] = message_values.get(value, 0)

print("message bodies extracted:", len(message_values))
in_corpus = [v for v in message_values if v in corpus]
not_in_corpus = [v for v in message_values if v not in corpus]
print("  present in corpus     :", len(in_corpus))
print("  absent from corpus    :", len(not_in_corpus))

print("\n-- absent sample --")
for value in not_in_corpus[:15]:
    print("  ", repr(value[:100]))

# Also check blitz string extraction path.
blitz = []
for text, _src in ex.extract_blitz_strings(data):
    if hasattr(ex, "sanitize_extracted_text"):
        text = ex.sanitize_extracted_text(text)
    text = text.strip()
    if len(text) >= 12 and re.search(r"[A-Za-z]{2,}", text):
        blitz.append(text)
print("\nblitz strings:", len(blitz))
blitz_missing = [t for t in blitz if t not in corpus]
print("  absent from corpus:", len(blitz_missing))

# Which untranslated corpus rows contain an embedded message body?
print("\n-- untranslated rows carrying message() --")
for index, (src, dst) in enumerate(zip(corpus_rows, translated_rows), start=1):
    if src != dst:
        continue
    match = re.search(r"(?i)\bmessage\s*\(\s*(.{6,300}?)\)", src)
    if match:
        body = match.group(1).strip()
        print(f"  row {index}: body_in_corpus={body in corpus} {body[:80]!r}")
