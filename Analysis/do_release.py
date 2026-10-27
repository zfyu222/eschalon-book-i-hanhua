"""Build the v1.6 distribution ZIP with player-facing Chinese metadata.

从 Python 调用打包脚本，避免 PowerShell 传中文参数时的代码页转换问题。
用法：python Analysis/do_release.py [--dry-run]
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(r"D:\StaticHanHua\.codebuddy\skills\game-release-patch\scripts\create_release_patch.py")
PYTHON = Path(sys.executable)

ARGS = [
    str(PYTHON),
    str(SCRIPT),
    "--project", str(ROOT),
    "--game-name", "Eschalon Book I",
    "--version", "1.6",
    "--introduction",
    "为 Steam Windows 版《Eschalon: Book I》制作的简体中文汉化补丁。通过显示层文本注入替换游戏画面文字，"
    "并替换界面贴图为中文版本，不修改游戏存档与内部物品 ID。",
    "--coverage",
    "全部 4743 条正文与界面文本（叙事、对话、书籍、任务、物品与技能说明、界面提示）；"
    "39 张界面贴图：主菜单、角色创建、世界地图、状态窗、交易、法术、存读档、死亡与结局文本、制作人员等。",
    "--game-version", "Steam 1.05（eschalon_book_1.exe，32 位）",
    "--platform", "Steam（Windows）",
    "--release-date", "2026-10-27",
    "--install",
    "先退出游戏。把压缩包内的 EschalonBook_Chinese_Launcher.exe、steam_appid.txt、gfx.pak 三个文件复制到游戏根目录"
    "（与 eschalon_book_1.exe 同一层），覆盖 gfx.pak 前请先备份原文件。之后通过 EschalonBook_Chinese_Launcher.exe 启动游戏，"
    "不要直接运行 eschalon_book_1.exe。无需安装 Python 或其他运行库。",
    "--uninstall",
    "删除 EschalonBook_Chinese_Launcher.exe 与补丁附带的 steam_appid.txt，用备份恢复 gfx.pak，即可回到原版。"
    "游戏存档不受影响。",
    "--verification",
    "已在 Steam 1.05 Windows 32 位版实测：启动菜单、主菜单、载入存档界面、角色创建界面全部显示中文，"
    "2492 个汉字按本版译文重建字体后无缺字方块，界面贴图版式正常。对话与任务文本本版未做实机抽检。",
    "--known-issues",
    "1) 启动界面（标题、选项标签、START 按钮）仍是英文原图，只有运行时文本值为中文。"
    "2) 从角色创建界面返回主菜单后，菜单项不显示，需退出游戏重新启动（中文注入的已知副作用）。"
    "3) 世界地图北部竖排地名（MIRKELL 等）保持英文。"
    "4) 菜单艺术字风格与原版不同，中文统一使用黑体。"
    "5) 对话与任务文本未经实机抽检，可能仍有少量显示问题。",
    "--changes",
    "正文与图片统一重译：合并正文 4563 条与图片独有 180 条为 4743 条统一语料，"
    "统一提取并审校术语表（577 术语 / 105 人物 / 379 禁翻），图片与正文不再出现同名不同译；"
    "新增 39 张中文界面贴图；修复贴图文字颜色过暗导致看不清的问题；按新译表重建中文字体，补齐全 2492 个汉字。",
    "--include", r".\Release\v16\EschalonBook_Chinese_Launcher.exe=EschalonBook_Chinese_Launcher.exe",
    "--include", r".\Release\v16\steam_appid.txt=steam_appid.txt",
    "--include", r".\Release\v16\gfx.pak=gfx.pak",
]

if "--dry-run" in sys.argv:
    ARGS.append("--dry-run")

result = subprocess.run(ARGS, cwd=ROOT, text=True, encoding="utf-8", errors="replace")
sys.exit(result.returncode)
