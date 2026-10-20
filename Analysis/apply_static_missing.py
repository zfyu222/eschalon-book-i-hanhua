import csv
from pathlib import Path

root = Path(__file__).resolve().parent.parent
LIST = Path(__file__).resolve().parent / "static_missing_prose.txt"
SOURCE = root / "eschalonbook_text.csv"
TRANSLATED = root / "eschalonbook_text_translated.csv"
QUEUE = Path(__file__).resolve().parent / "queue_v2.csv"


def col(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


sources = col(SOURCE)
existing = set(sources)
new_texts = []
for line in LIST.read_text(encoding="utf-8").splitlines():
    value = line.strip()
    if not value or value in existing:
        continue
    existing.add(value)
    new_texts.append(value)

with SOURCE.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    for value in new_texts:
        writer.writerow([value])
with TRANSLATED.open("a", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    for _ in new_texts:
        writer.writerow([""])
with QUEUE.open("w", encoding="utf-8", newline="") as stream:
    writer = csv.writer(stream)
    for index, value in enumerate(new_texts):
        writer.writerow([index, value])

print("appended:", len(new_texts), "total:", len(sources) + len(new_texts))
