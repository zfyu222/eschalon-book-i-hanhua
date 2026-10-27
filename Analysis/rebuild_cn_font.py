"""Rebuild the Chinese subset font from the current translation tables.

译文换了措辞后会出现原字体子集没有的字，这些字在游戏里会显示为空白，
因此发布前必须按最新译表重新生成 fonts/cn_subset.ttf 及其三个名称变体。

用法：python Analysis/rebuild_cn_font.py
"""
import csv
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter

ROOT = Path(__file__).resolve().parent.parent
TABLES = [
    "eschalonbook_text_translated.csv",
    "eschalonbook_images_text_translated.csv",
    "translated_strings_translated.csv",
]
SOURCE = Path(r"C:\Windows\Fonts\msyh.ttc")
SUBSET = ROOT / "fonts" / "cn_subset.ttf"


def collect_chars():
    chars = set()
    for name in TABLES:
        path = ROOT / name
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.reader(stream):
                if row:
                    chars.update(row[0])
    chars.update(chr(code) for code in range(32, 127))
    chars.discard("\r")
    chars.discard("\n")
    return "".join(sorted(chars))


def main():
    text = collect_chars()
    cjk = sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    print(f"characters: {len(text)} (cjk {cjk})")
    if not SOURCE.exists():
        raise SystemExit(f"missing source font {SOURCE}")
    font = TTFont(str(SOURCE), fontNumber=0)
    subsetter = Subsetter()
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.save(str(SUBSET))
    font.close()
    print(f"wrote {SUBSET.relative_to(ROOT)}: {SUBSET.stat().st_size:,} bytes")

    # 校验：重新读回，确认每个字符都有字形
    check = TTFont(str(SUBSET))
    cmap = set()
    for table in check["cmap"].tables:
        cmap |= set(table.cmap.keys())
    check.close()
    missing = sorted({c for c in text if ord(c) not in cmap})
    if missing:
        sample = "".join(missing[:40]).encode("unicode_escape").decode("ascii")
        print(f"WARNING missing glyphs: {len(missing)} {sample}")
        return 1
    print("glyph coverage: complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
