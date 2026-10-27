"""Split the unified export back into the text and image source tables.

输入：
  eschalonbook_unified_text_translated.csv   统一译表（由 workflow export 产出）
  TranslateFiles/unified_corpus.json         行来源索引
输出：
  eschalonbook_text_translated.csv           正文译表（与正文源文逐行对应）
  eschalonbook_images_text_translated.csv    图片译表（含与正文重复行的复用译文）

用法：python Analysis/split_unified_translation.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNIFIED = ROOT / "eschalonbook_unified_text_translated.csv"
INDEX = ROOT / "TranslateFiles" / "unified_corpus.json"
TEXT_OUT = ROOT / "eschalonbook_text_translated.csv"
IMAGE_OUT = ROOT / "eschalonbook_images_text_translated.csv"


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [(row[0] if row else "") for row in csv.reader(stream)]


def main():
    unified = read_rows(UNIFIED)
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    if len(unified) != index["unified_rows"]:
        raise SystemExit(f"unified rows {len(unified)} != {index['unified_rows']}")

    text_rows = [""] * index["text_rows"]
    image_rows = [""] * index["image_rows"]
    for item in index["rows"]:
        if item["origin"] == "text":
            text_rows[item["src_row"] - 1] = unified[item["i"] - 1]
        else:
            if item.get("reuse_text_row"):
                image_rows[item["src_row"] - 1] = text_rows[item["reuse_text_row"] - 1]
            else:
                image_rows[item["src_row"] - 1] = unified[item["i"] - 1]

    for path, rows, expected in (
        (TEXT_OUT, text_rows, index["text_rows"]),
        (IMAGE_OUT, image_rows, index["image_rows"]),
    ):
        if len(rows) != expected or any(not value.strip() for value in rows):
            raise SystemExit(f"incomplete rows for {path.name}")
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            for value in rows:
                writer.writerow([value])
        print(f"{path.name}: {len(rows)} rows")


if __name__ == "__main__":
    main()
