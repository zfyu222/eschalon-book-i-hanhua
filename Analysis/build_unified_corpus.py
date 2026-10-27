"""Build the unified source corpus for the 2026-10-27 rebuild.

正文文本与图片文本合并为同一份翻译源文，供统一术语提取与翻译使用。
图片 231 条中与正文完全相同的行不重复计入，拆分回填时复用正文译文。

输出：
  eschalonbook_unified_text.csv          统一源文（单列）
  TranslateFiles/unified_corpus.json     行来源索引（拆分回正文/图片用）
  TranslateFiles/unified_context.json    逐条上下文（group/resource/text_type/note）
"""
import csv
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
text_csv = root / "eschalonbook_text.csv"
image_csv = root / "eschalonbook_images_text.csv"
mapping_json = root / "eschalonbook_images_text.mapping.json"
out_csv = root / "eschalonbook_unified_text.csv"
out_index = root / "TranslateFiles" / "unified_corpus.json"
out_context = root / "TranslateFiles" / "unified_context.json"


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [(row[0] if row else "") for row in csv.reader(stream)]


def image_name(row_no, image_rows):
    for item in image_rows:
        if item.get("csv_row") == row_no:
            sources = item.get("sources") or []
            if sources:
                path = sources[0].get("path") or ""
                match = re.match(r"(img_\d+)", path)
                if match:
                    return match.group(1)
                return Path(path).stem
    return ""


def main():
    text = read_rows(text_csv)
    images = read_rows(image_csv)
    mapping = json.loads(mapping_json.read_text(encoding="utf-8"))
    image_rows = mapping.get("regions") or []

    unified = []
    index = {"schema": 1, "text_rows": len(text), "image_rows": len(images), "rows": []}
    context = {}
    text_lookup = {}
    for pos, value in enumerate(text, start=1):
        text_lookup.setdefault(value.strip(), pos)

    for pos, value in enumerate(text, start=1):
        unified.append(value)
        index["rows"].append({"i": len(unified), "origin": "text", "src_row": pos})
        context[str(len(unified))] = {
            "group": "text",
            "resource": "eschalonbook_text.csv",
            "text_type": "game_text",
        }

    duplicates = []
    appended = 0
    for pos, value in enumerate(images, start=1):
        key = value.strip()
        if key in text_lookup:
            duplicates.append({"image_row": pos, "text_row": text_lookup[key]})
            index["rows"].append(
                {
                    "i": None,
                    "origin": "image",
                    "src_row": pos,
                    "reuse_text_row": text_lookup[key],
                }
            )
            continue
        unified.append(value)
        appended += 1
        index["rows"].append({"i": len(unified), "origin": "image", "src_row": pos})
        name = image_name(pos, image_rows)
        context[str(len(unified))] = {
            "group": "image",
            "resource": name or "gfx.pak",
            "text_type": "image_text",
            "note": "该文本刻在游戏贴图上，排版区域固定，译文需简短，避免超出原始文字块宽度。",
        }

    with out_csv.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        for value in unified:
            writer.writerow([value])

    index["unified_rows"] = len(unified)
    index["image_appended"] = appended
    index["image_duplicates"] = duplicates
    out_index.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    out_context.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"unified={len(unified)} text={len(text)} image={len(images)} "
        f"image_appended={appended} duplicates={len(duplicates)}"
    )


if __name__ == "__main__":
    main()
