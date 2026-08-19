"""Build Chinese subset fonts whose internal names match Eschalon's fonts."""
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "fonts" / "cn_subset.ttf"

VARIANTS = {
    "cn_OldTymeBG.ttf": {1: "OldTymeBG", 2: "Regular", 4: "OldTymeBG", 6: "OldTymeBG"},
    "cn_Fantasy.ttf": {1: "Fantasy", 2: "Bold", 4: "FantasyBold", 6: "Fantasy"},
    "cn_DS_Celtic_1.ttf": {1: "DS_Celtic-1", 2: "Regular", 4: "DS_Celtic 1", 6: "DSCeltic1"},
}


def main():
    for filename, replacements in VARIANTS.items():
        font = TTFont(SOURCE)
        for record in font["name"].names:
            value = replacements.get(record.nameID)
            if value is None:
                continue
            record.string = value.encode(record.getEncoding())
        target = ROOT / "fonts" / filename
        font.save(target)
        font.close()
        print(f"created {target.name}: {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
