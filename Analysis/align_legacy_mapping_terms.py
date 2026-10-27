"""Align the launcher's legacy mapping table with the newly frozen glossary.

启动器先加载 core.load_mapping()（translated_strings.csv 1082 条，来自 EXE 内嵌
字符串扫描），再用统一译表覆盖同名 key。旧表里 355 条可见文本不在统一语料中，
仍沿用 v1.5 译文。本脚本只做术语对齐，不重译正文：

  - 无歧义术语直接替换（Goblins 哥布林→地精 等）
  - Blackwater / Darkwater 都会译成「黑水镇」，按原文专名区分后才替换

用法：python Analysis/align_legacy_mapping_terms.py
"""
import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "translated_strings.csv"
TARGET = ROOT / "translated_strings_translated.csv"
BACKUP = ROOT / "TranslateFiles" / "backups" / "translated_strings_translated.v1.5.csv"

PLAIN = {
    "哥布林": "地精",
    "盐渍海岸": "咸海岸",
    "真菌史莱姆": "真菌软泥怪",
    "埃鲁多": "埃鲁博",
}


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [(row[0] if row else "") for row in csv.reader(stream)]


def main():
    sources = read_rows(SOURCE)
    targets = read_rows(TARGET)
    if len(sources) != len(targets):
        raise SystemExit("row count mismatch")
    if not BACKUP.exists():
        BACKUP.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TARGET, BACKUP)
        print(f"backup: {BACKUP.relative_to(ROOT)}")

    changed = []
    for index, (source, target) in enumerate(zip(sources, targets)):
        updated = target
        for old, new in PLAIN.items():
            updated = updated.replace(old, new)
        # Blackwater 保留「黑水镇」，只有 Darkwater 改为「暗水镇」。
        if "Darkwater" in source and "黑水镇" in updated:
            updated = updated.replace("黑水镇", "暗水镇")
        if updated != target:
            changed.append((index + 1, source[:40], target[:40], updated[:40]))
            targets[index] = updated

    with TARGET.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        for value in targets:
            writer.writerow([value])
    print(f"aligned rows: {len(changed)}")
    for row in changed[:10]:
        print("  %s | %s => %s" % (row[0], row[2], row[3]))


if __name__ == "__main__":
    main()
