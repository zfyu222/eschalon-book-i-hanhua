"""Rebuild runtime fonts from every shipped translation, then audit coverage."""
import csv
import json
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from build_font_variants import VARIANTS

ROOT = Path(__file__).resolve().parent
SOURCES = ("translated_strings_translated.csv", "eschalonbook_text_translated.csv")


def main():
    characters = set(chr(code) for code in range(32, 127))
    for name in SOURCES:
        with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.reader(stream):
                if row:
                    characters.update(row[0])
    characters.difference_update("\r\n\t\ufeff")
    required = {ord(char) for char in characters}
    old = {}
    for name in VARIANTS:
        with TTFont(ROOT / "fonts" / name) as font:
            old[name] = "".join(chr(code) for code in sorted(required - font.getBestCmap().keys()))
    font = TTFont(r"C:\Windows\Fonts\simhei.ttf")
    missing = required - font.getBestCmap().keys()
    missing_han = {code for code in missing if 0x3400 <= code <= 0x9FFF}
    if missing_han:
        raise RuntimeError(f"Source font lacks codepoints: {sorted(missing)}")
    # Legacy base CSV also contains control bytes and decorative emoji, which
    # are not Chinese glyphs. Report these separately instead of hiding them.
    unsupported = sorted(missing)
    required.difference_update(missing)
    builder = subset.Subsetter()
    builder.populate(unicodes=required)
    builder.subset(font)
    target = ROOT / "fonts" / "cn_subset.ttf"
    font.save(target)
    font.close()
    for name, replacements in VARIANTS.items():
        with TTFont(target) as font:
            for record in font["name"].names:
                if record.nameID in replacements:
                    record.string = replacements[record.nameID].encode(record.getEncoding())
            font.save(ROOT / "fonts" / name)
        with TTFont(ROOT / "fonts" / name) as font:
            missing = required - font.getBestCmap().keys()
            if missing:
                raise RuntimeError(f"{name} lacks codepoints: {sorted(missing)}")
    report = {"sources": SOURCES, "required_characters": len(required),
              "previous_missing": old, "remaining_missing": 0,
              "unsupported_non_han_codepoints": unsupported}
    report_dir = ROOT / "Analysis" / "font_coverage"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "coverage.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
