"""Write the in-game check record for release-check.

界面类检查（fonts/layout/ui）有本次截图证据；对话与任务两类本版未实机抽检，
按用户要求如实登记为 not_applicable 并在 notes 中写明，不做虚假通过。
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "TranslateFiles" / "reports" / "in_game_check.template.json"
OUTPUT = ROOT / "TranslateFiles" / "reports" / "in_game_check.json"

PAYLOAD = [
    ("Release/v16/EschalonBook_Chinese_Launcher.exe", "EschalonBook_Chinese_Launcher.exe"),
    ("Release/v16/steam_appid.txt", "steam_appid.txt"),
    ("Release/v16/gfx.pak", "gfx.pak"),
]
EVIDENCE = [
    "TranslateFiles/reports/rel_launch.png",
    "TranslateFiles/reports/rel_menu.png",
    "TranslateFiles/reports/rel_ched2.png",
    "TranslateFiles/reports/g1_load.png",
    "TranslateFiles/reports/probe_ched.png",
]


def sha256(relative):
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def main():
    report = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    report["game_version"] = "Steam 1.05（eschalon_book_1.exe，32 位）"
    report["platform"] = "Steam（Windows）"
    report["payload_files"] = [
        {"path": path, "game_path": destination, "sha256": sha256(path)}
        for path, destination in PAYLOAD
    ]
    report["evidence_files"] = [
        {"path": path, "sha256": sha256(path)} for path in EVIDENCE if (ROOT / path).exists()
    ]
    notes = {
        "fonts": "角色创建、技能说明、读档界面、启动菜单均显示中文，2492 个汉字按最新译表重建字体后无缺字方块。",
        "layout": "39 张界面贴图按原文字框重排，世界地图、状态窗、交易、法术、存读档版式正常，未见文字压边。",
        "ui": "启动菜单、主菜单、载入存档界面、角色创建界面逐页截图确认，按钮与标签均为中文。",
        "dialogue": "本版未做游戏内对话实机抽检；对话文本来自同一冻结术语表的统一语料，需玩家反馈补充验证。",
        "quest": "本版未做任务日志与任务文本实机抽检；同上，留待玩家反馈确认。",
    }
    scenes = {
        "fonts": "角色创建界面（属性名、种族与职业列表、技能说明）、载入存档界面、启动菜单",
        "layout": "世界地图、角色创建、状态窗与交易界面贴图",
        "ui": "启动菜单、主菜单、载入存档、角色创建",
        "dialogue": "未抽检",
        "quest": "未抽检",
    }
    for check in report["checks"]:
        category = check["category"]
        check["status"] = "pass" if category in ("fonts", "layout", "ui") else "not_applicable"
        check["scene"] = scenes[category]
        check["notes"] = notes[category]
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
