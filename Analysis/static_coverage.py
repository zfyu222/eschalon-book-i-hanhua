"""Static completeness audit: enumerate every displayable string in the binary
and check whether the corpus translates it.

This replaces play-testing for coverage purposes. It cannot see text that is
assembled at runtime from numbers/names, but that surface is handled by the
runtime rules instead.
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

IDENT = re.compile(r"^(?:[\w./\\:-]+\.(?:pak|ttf|csv|png|wav|ogg|ent|map|txt|ini|cfg)|\w+::.*|\w+_[a-z_]+)$")
TAG = re.compile(r"^\[[A-Z]+\]$")
DATE = re.compile(r"\b\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}\b")
NUMERIC = re.compile(r"^[\d\s.,:/+\-x]+$")


def col(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


corpus = set(col(SOURCE))
corpus_norm = {re.sub(r"\s+", " ", s).strip().strip('"').strip() for s in corpus}


def classify(text):
    if IDENT.match(text) or TAG.match(text) or DATE.search(text) or NUMERIC.match(text):
        return "identifier"
    if len(text.split()) < 2:
        return "label"
    return "prose"


data = EXE.read_bytes()
candidates = {}

for text, _source in ex.extract_blitz_strings(data):
    text = ex.sanitize_extracted_text(text) if hasattr(ex, "sanitize_extracted_text") else text
    text = text.strip()
    if len(text) < 3 or not re.search(r"[A-Za-z]{2,}", text):
        continue
    candidates.setdefault(text, "exe-string")

runs = re.findall(rb"[\x20-\x7e\r\n\t\xd1]{20,}", data)
for run in runs:
    block = run.decode("latin-1", errors="replace")
    for match in re.finditer(r'"([^"\r\n]{3,})"', block):
        value = match.group(1).strip()
        if value:
            candidates.setdefault(value, "quoted")
    for match in re.finditer(r"\[([A-Za-z][^\[\]\r\n]{8,90})\]", block):
        value = f"[{match.group(1).strip()}]"
        candidates.setdefault(value, "bracket")
    for match in re.finditer(r'(?i)\bmessage\s*\(\s*(.{6,300}?)\)', block, re.S):
        value = re.sub(r"^[\"']|[\"']$", "", match.group(1).strip()).strip()
        if len(value) >= 12:
            candidates.setdefault(value, "message")
    for line in re.split(r"[\r\n]+", block):
        value = line.strip().strip('"').strip()
        if len(value) >= 30 and len(value.split()) >= 5 and re.search(r"[.!?][\"']?$", value):
            candidates.setdefault(value, "prose")

buckets = {"prose": [], "label": [], "identifier": []}
for text in candidates:
    key = re.sub(r"\s+", " ", text).strip().strip('"').strip()
    if text in corpus or key in corpus_norm:
        continue
    buckets[classify(text)].append(text)

print(f"corpus rows        : {len(corpus)}")
print(f"static candidates  : {len(candidates)}")
for name, items in buckets.items():
    print(f"untranslated {name:10}: {len(items)}")
print("\n-- prose sample --")
for text in buckets["prose"][:10]:
    print("  ", repr(text[:110]))
print("\n-- label sample --")
for text in buckets["label"][:10]:
    print("  ", repr(text[:80]))

out = Path(__file__).resolve().parent / "static_missing_prose.txt"
out.write_text("\n".join(buckets["prose"] + buckets["label"]), encoding="utf-8")
print("\nwritten", out, len(buckets["prose"]) + len(buckets["label"]), "rows")
