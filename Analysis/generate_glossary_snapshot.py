"""Generate the unified glossary snapshot (revision r1) without allocating tasks.

复刻 translation_workflow.prepare(glossary_review) 的表生成段落：
合并全部 extract 任务的 analysis -> 附加语料证据 -> 共享 audit 快照。
这样可以在分配审校任务前先把既有正式术语并入快照。

用法：python Analysis/generate_glossary_snapshot.py
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent.parent / "Tools" / "localization"))

from glossary_merge import merge_extractions  # noqa: E402
from glossary_corpus_evidence import attach_corpus_evidence  # noqa: E402
import glossary_tool  # noqa: E402


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    db_path = ROOT / "TranslateFiles" / "state" / "workflow.sqlite3"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
    revision = json.loads(meta["revision"])
    source_path = json.loads(meta["source_path"])

    extraction = conn.execute(
        'SELECT * FROM tasks WHERE stage="extract" AND revision=? AND status!="obsolete" ORDER BY rowid',
        (revision,),
    ).fetchall()
    if not extraction or any(task["status"] != "done" for task in extraction):
        raise SystemExit("extract tasks not all done")

    original = merge_extractions(
        (task["id"], json.loads(task["result"])["analysis"]) for task in extraction
    )
    folder = ROOT / f"glossary/r{revision}"
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = folder / "audit" / "glossary_original.json"
    if not snapshot.exists():
        records = [dict(row) for row in conn.execute("SELECT * FROM records ORDER BY ordinal")]
        stats = attach_corpus_evidence(original, records)
        write_json(folder / "corpus_evidence_report.json", stats)
        wrapper = folder / "analysis_input.json"
        write_json(wrapper, {"extra": {"analysis_v1": original}})
        glossary_tool.audit(wrapper, source_path, folder / "audit")
    original = json.loads(snapshot.read_text(encoding="utf-8"))
    write_json(folder / "glossary_original.json", original)
    print(
        "revision=%s terms=%d characters=%d non_translate=%d"
        % (
            revision,
            len(original.get("terms", [])),
            len(original.get("characters", [])),
            len(original.get("non_translate", [])),
        )
    )


if __name__ == "__main__":
    main()
