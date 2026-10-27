"""Attach the shipped v1.5 term renderings to the unified glossary snapshot.

不覆盖新提取的译名，也不改动表结构：
  - 新表已含同一 source 且译名不同 -> 在 term_reason 追记 v1.5 旧译名，供审校裁决
  - v1.5 有而统一语料未提取到 -> 只写入 legacy_reference.json 备查，不强行新增条目

用法：python Analysis/annotate_legacy_terms.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = ROOT / "TranslateFiles" / "glossary" / "r1" / "audit" / "glossary_original.json"
PLAIN = ROOT / "TranslateFiles" / "glossary" / "r1" / "glossary_original.json"
LEGACY_GLOSSARY = ROOT / "TranslateFiles" / "backups" / "20261027_rebuild" / "glossary_r1" / "glossary_original.json"
LEGACY_CSV = ROOT / "ainiee_glossary.csv"
REPORT = ROOT / "TranslateFiles" / "glossary" / "legacy_reference.json"

MARK = "；已发布 v1.5 译名为「{}」，请核对是否统一。"


def load_pairs(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = {}
    for table in ("terms", "characters"):
        for row in data.get(table, []):
            source = row.get("source", "")
            target = row.get("recommended_translation", "")
            if source and target:
                pairs[source] = target
    return pairs


def main():
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    legacy = {}
    if LEGACY_GLOSSARY.exists():
        legacy.update(load_pairs(LEGACY_GLOSSARY))
    with LEGACY_CSV.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        next(reader, None)
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                legacy.setdefault(row[0].strip(), row[1].strip())

    same, conflicts, missing = [], [], []
    current = {}
    for table in ("terms", "characters"):
        for row in snapshot.get(table, []):
            current[row.get("source", "")] = (table, row)
    for source, old_target in legacy.items():
        hit = current.get(source)
        if hit is None:
            missing.append({"source": source, "v1_5": old_target})
            continue
        table, row = hit
        new_target = row.get("recommended_translation", "")
        if new_target == old_target:
            same.append(source)
            continue
        conflicts.append({"source": source, "table": table, "v1_5": old_target, "extracted": new_target})
        reason = row.get("term_reason", "")
        if "已发布 v1.5 译名" not in reason:
            row["term_reason"] = reason.rstrip() + MARK.format(old_target)

    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    PLAIN.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT.write_text(
        json.dumps(
            {
                "legacy_source": str(LEGACY_GLOSSARY.relative_to(ROOT)),
                "legacy_csv": LEGACY_CSV.name,
                "legacy_total": len(legacy),
                "same": len(same),
                "conflicts": conflicts,
                "missing_in_unified": missing,
                "note": "conflicts 只追记历史译名，不覆盖新提取结果；missing_in_unified 未强行新增条目。",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"legacy={len(legacy)} same={len(same)} conflicts={len(conflicts)} missing={len(missing)}")


if __name__ == "__main__":
    main()
