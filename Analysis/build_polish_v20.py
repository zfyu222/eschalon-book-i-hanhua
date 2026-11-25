"""Build the v2.0 localized textures, distributable delta and runtime launcher."""
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from PyInstaller.archive.readers import CArchiveReader

from rebuild_image_archive import rebuild

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "Release/v20_build"
PRIOR_ARCHIVE = ROOT / "Dispatch/StagingArchive/v19_before_v20"
OLD_FILES = PRIOR_ARCHIVE if PRIOR_ARCHIVE.is_dir() else ROOT / "Dispatch/Files"
BASE = ROOT / "ImagePatch/backup/gfx.pak"
sys.path.insert(0, str(ROOT / "ImagePatch"))
import render_image_text as renderer

ORIGINAL = "0ffbf360080320dd91b98034431a1644b703ff32ecabb306560dfd7da55825d9"
V19 = "2d2ffc2e4bd9882b4a0e212c26eca71d460613a5f0714db6456e3f9465bd4a80"
LINUX = {"linux_launch.png", "mainmenu_linux.png"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(data):
    return [row[0] for row in csv.reader(io.StringIO(data.decode("utf-8-sig"), newline=""))]


def read_archive(path):
    data = path.read_bytes()
    magic, version, count, packed_size, raw_size = struct.unpack_from("<4s4I", data)
    assert (magic, version, raw_size) == (b"!PAK", 0x10001, count * 272)
    start = 20 + packed_size
    directory = zlib.decompress(data[20:start])
    assert len(directory) == raw_size
    entries = {}
    for index in range(count):
        span, offset, length, flag = struct.unpack_from("<4I", directory, index * 272)
        name = directory[index * 272 + 16:(index + 1) * 272].split(b"\0", 1)[0].decode("ascii")
        encoded = data[start + offset:start + offset + span]
        assert name not in entries and flag == 2 and len(encoded) == span
        decoded = zlib.decompress(encoded)
        assert len(decoded) == length
        entries[name] = (start + offset, encoded, decoded)
    return data[:start], entries


def screen_preference(original, target):
    """Redraw the single Windows launcher label without erasing the bezel."""
    image = original.convert("RGB")
    data = np.array(image)
    y0, y1, x0, x1 = 314, 334, 78, 250
    roi = data[y0:y1, x0:x1].astype(np.int16)
    strokes = (roi[:, :, 2] > roi[:, :, 1] + 6) & (roi[:, :, 2] > 103)
    mask = np.zeros(data.shape[:2], dtype=np.uint8)
    mask[y0:y1, x0:x1] = strokes.astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((3, 3), dtype=np.uint8))
    canvas = Image.fromarray(cv2.inpaint(data, mask, 3, cv2.INPAINT_TELEA))
    font = ImageFont.truetype(str(renderer.FONT), 17, index=renderer.FONT_INDEX)
    ImageDraw.Draw(canvas).text((163, 323), target, font=font, anchor="mm",
                                fill=(205, 201, 237), stroke_width=1, stroke_fill=(42, 41, 65))
    return canvas.convert(original.mode)


def repair_wood_grain(data, mask, cache):
    workspace = ROOT.parents[1]
    tools = workspace / "Tools/image_text"
    cache.mkdir(exist_ok=True)
    Image.fromarray(data).save(cache / "keyboard_source.png")
    Image.fromarray(mask).save(cache / "keyboard_mask.png")
    command = """
from pathlib import Path
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, sys.argv[1])
from image_style import lama_fill
tools = Path(sys.argv[1])
cache = Path(sys.argv[2])
source = np.array(Image.open(cache / "keyboard_source.png"))
mask = np.array(Image.open(cache / "keyboard_mask.png"))
filled, provider = lama_fill(source, mask, tools / "models/lama_fp32.onnx")
source[mask > 0] = filled[mask > 0]
Image.fromarray(source).save(cache / "keyboard_clean.png")
print(provider)
"""
    subprocess.run([str(tools / ".venv-gpu/Scripts/python.exe"), "-c", command,
                    str(tools), str(cache)], check=True)
    return Image.open(cache / "keyboard_clean.png").convert("RGB")


def keyboard_shortcuts(original, regions, translations, cache):
    """Restore the wood grain between glyphs and keep the key labels aligned."""
    data = np.array(original.convert("RGB"))
    typo_mask = np.zeros(data.shape[:2], dtype=np.uint8)
    for region in regions:
        x0, y0, x1, y1 = map(round, region["box"])
        x0, y0, x1, y1 = max(3, x0 - 4), y0 - 1, min(data.shape[1] - 3, x1 + 4), y1 + 1
        roi = data[y0:y1, x0:x1].astype(np.int16)
        red, green, blue = np.moveaxis(roi, -1, 0)
        bright = (red > 160) & (green > 152) & (blue > 146)
        accent = ((red > 148) & (red > green + 47)) | ((green > 128) & (green > red + 23)) | ((blue > 140) & (blue > red + 34))
        typo_mask[y0:y1, x0:x1] |= (bright | accent).astype(np.uint8) * 255
    typo_mask = cv2.dilate(typo_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    # The title has a wide, low-contrast embossed shadow beyond the colored ink.
    typo_mask[11:41, 43:364] = 255
    canvas = repair_wood_grain(data, typo_mask, cache)
    draw = ImageDraw.Draw(canvas)
    key_font = ImageFont.truetype(str(renderer.FONT), 14, index=renderer.FONT_INDEX)
    body_font = ImageFont.truetype(str(renderer.FONT), 14, index=renderer.FONT_INDEX)
    heading_font = ImageFont.truetype(str(renderer.FONT), 21, index=renderer.FONT_INDEX)

    def lettering(position, text, font, fill, anchor):
        draw.text(position, text, font=font, fill=fill, anchor=anchor, stroke_width=1, stroke_fill=(26, 23, 19))

    for region in regions:
        row = region["csv_row"]
        text = translations[row - 1]
        _, y0, _, y1 = region["box"]
        center_y = round((y0 + y1) / 2)
        if row in (86, 103):
            lettering((200, center_y), text, heading_font, (239, 236, 222), "mm")
            continue
        key, description = text.split("  ", 1)
        color = (243, 124, 104) if row <= 96 else (167, 222, 191)
        if row >= 104:
            color = (168, 185, 245)
        lettering((105, center_y), key, key_font, color, "rm")
        if row == 99:
            first, rest = description.split("或", 1)
            lines = (first, "或" + rest)
        elif row == 107:
            first, rest = description.split("：", 1)
            lines = (first + "：", rest)
        else:
            lines = (description,)
        y = center_y - 7 * (len(lines) - 1)
        for line in lines:
            assert draw.textlength(line, font=body_font) < 279
            lettering((113, y), line, body_font, (246, 240, 227), "lm")
            y += 14
    return canvas


def render_changed_images(original_entries, prior_entries):
    name = "eschalonbook_images_text_translated.csv"
    before = subprocess.check_output(["git", "-C", str(ROOT), "show", f"740e7f1:{name}"])
    source = (ROOT / "eschalonbook_images_text.csv").read_bytes()
    target = (ROOT / name).read_bytes()
    old, new, originals = map(read_csv, (before, target, source))
    mapping = json.loads((ROOT / "eschalonbook_images_text.mapping.json").read_text(encoding="utf-8"))
    assert mapping["csv_sha256"] == sha(source) and len(old) == len(new) == len(originals) == 231
    changed = {i for i, (a, b) in enumerate(zip(old, new), 1) if a != b}
    by_offset = {e[0]: name for name, e in original_entries.items()}
    groups = {}
    skipped = set()
    for region in mapping["regions"]:
        row = region["csv_row"]
        if row not in changed:
            continue
        assert len(region["sources"]) == 1
        src = region["sources"][0]
        provenance = src["provenance"]
        assert provenance["archive_sha256"] == ORIGINAL
        path = by_offset[provenance["stream_offset"]]
        assert src["file_sha256"] == sha(original_entries[path][2])
        if path in LINUX:
            skipped.add(path)
            continue
        groups.setdefault(path, []).append(region)
    assert changed == {r["csv_row"] for group in groups.values() for r in group}
    replacements = BUILD / "textures"
    previews = BUILD / "previews"
    replacements.mkdir()
    previews.mkdir()
    for path, regions in groups.items():
        old_img = Image.open(io.BytesIO(prior_entries[path][2]))
        original = Image.open(io.BytesIO(original_entries[path][2]))
        width, height = original.size
        assert old_img.size == original.size
        raw_path = previews / f"original_{path}"
        raw_path.write_bytes(original_entries[path][2])
        if path == "launchscreen.png":
            region, = regions
            updated = screen_preference(original, new[region["csv_row"] - 1])
        elif path == "keyboard_shortcuts.png":
            keyboard_regions = [r for r in mapping["regions"] if 86 <= r["csv_row"] <= 107]
            updated = keyboard_shortcuts(original, keyboard_regions, new, previews)
        else:
            rendered = previews / f"regions_{path}"
            renderer.render(raw_path, regions, originals, new, rendered)
            fresh = Image.open(rendered).convert(old_img.mode)
            updated = old_img.copy()
            for region in regions:
                x0, y0, x1, y1 = renderer._region_box(region, width, height)
                box = x0, max(0, y0 - 2), x1, min(height, y1 + 2)
                updated.paste(fresh.crop(box), box)
        updated.save(replacements / path)
        old_img.save(previews / f"v19_{path}")
    return replacements, {"changed_rows": sorted(changed), "images": sorted(groups),
                          "linux_variants_excluded": sorted(skipped), "source_sha256": sha(source),
                          "images_translation_sha256": sha(target)}


def make_delta(original, prior, target):
    encoded_header, target_entries = read_archive(target)
    delta = bytearray(b"EZG1" + struct.pack("<I", len(target_entries) + 1))
    delta.extend(struct.pack("<iiI", -1, -1, len(encoded_header)) + encoded_header)
    literal_names = []
    for name, (offset, encoded, png) in target_entries.items():
        original_offset, original_chunk, original_png = original[name]
        prior_offset, prior_chunk, _ = prior[name]
        if png == original_png:
            assert encoded == original_chunk == prior_chunk
            delta.extend(struct.pack("<iiI", original_offset, prior_offset, len(encoded)))
        else:
            assert png != original_png
            delta.extend(struct.pack("<iiI", -1, -1, len(encoded)) + encoded)
            literal_names.append(name)
    assert len(literal_names) == 40
    (BUILD / "gfx.delta").write_bytes(delta)
    return {"localized_streams": len(literal_names), "original_streams_excluded": len(target_entries)-len(literal_names),
            "delta_sha256": sha(delta), "delta_size": len(delta),
            "supported_base_hashes": [ORIGINAL, V19]}


def build_launcher():
    old_runtime = OLD_FILES / "汉化文件/EschalonBook_Chinese_Launcher.exe"
    archive = CArchiveReader(str(old_runtime))
    fonts_home = BUILD / "fonts"
    fonts_home.mkdir()
    inputs = ("translated_strings_translated.csv", "eschalonbook_text_translated.csv")
    required = set("".join("".join(read_csv((ROOT / name).read_bytes())) for name in inputs))
    required.update(chr(n) for n in range(32, 127))
    old_required = set("".join("".join(read_csv(archive.extract(name))) for name in inputs))
    for name in ("build_font_variants.py", "eschalonbook_text_translated.csv",
                 "eschalonbook_images_text_translated.csv", "translated_strings_translated.csv"):
        shutil.copy2(ROOT / name, BUILD / name)
    (BUILD / "Analysis").mkdir()
    shutil.copy2(ROOT / "Analysis/rebuild_cn_font.py", BUILD / "Analysis/rebuild_cn_font.py")
    # The existing script exits 1 on historical control/decorative characters;
    # audit required glyphs against both corpora below instead.
    subprocess.run([sys.executable, str(BUILD / "Analysis/rebuild_cn_font.py")], check=False)
    subprocess.run([sys.executable, str(BUILD / "build_font_variants.py")], check=True)
    missing = set()
    for path in fonts_home.glob("*.ttf"):
        with TTFont(path) as font:
            absent = {c for c in required if ord(c) not in font.getBestCmap()}
            assert absent <= old_required and not any("\u3400" <= c <= "\u9fff" for c in absent)
            missing.update(absent)
    spec = ROOT / "build_release/EschalonBook_Chinese_Launcher.spec"
    original_spec = spec.read_text(encoding="utf-8")
    old_fonts = repr(str(ROOT / "fonts"))[1:-1]
    new_fonts = repr(str(fonts_home))[1:-1]
    candidate_spec = BUILD / spec.name
    assert original_spec.count(old_fonts) == 3
    candidate_spec.write_text(original_spec.replace(old_fonts, new_fonts), encoding="utf-8")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(BUILD),
                    "--workpath", str(BUILD / "pyinstaller"), str(candidate_spec)], cwd=ROOT, check=True)
    runtime = BUILD / "EschalonBook_Chinese_Launcher.exe"
    frozen = CArchiveReader(str(runtime))
    for entry in frozen.toc:
        name = entry.replace("\\", "/")
        if name.endswith(".csv") or name == "runtime_fragment_overrides.json":
            assert frozen.extract(entry) == (ROOT / name).read_bytes()
        elif name.startswith("fonts/"):
            assert frozen.extract(entry) == (BUILD / name).read_bytes()
    return {"size": runtime.stat().st_size, "sha256": sha(runtime.read_bytes()),
            "legacy_non_han_exclusions": sorted(ord(c) for c in missing)}


def main(reuse_launcher=False):
    if not reuse_launcher:
        BUILD.mkdir()
    prior_path = OLD_FILES / "汉化文件/gfx.pak"
    assert sha(BASE.read_bytes()) == ORIGINAL and sha(prior_path.read_bytes()) == V19
    validation = json.loads((ROOT / "TranslateFiles/reports/final_validation.json").read_text(encoding="utf-8"))
    assert validation["status"] == "passed" and validation["translation_sha256"] == sha(
        (ROOT / "eschalonbook_unified_text_translated.csv").read_bytes())
    _, original = read_archive(BASE)
    _, prior = read_archive(prior_path)
    replacements, image = render_changed_images(original, prior)
    gfx = BUILD / "gfx.pak"
    built = rebuild(prior_path, replacements, gfx)
    assert set(built["changed"]) == set(image["images"])
    report = {"translation_sha256": validation["translation_sha256"], "images": image,
              "gfx": built, "delta": make_delta(original, prior, gfx)}
    (BUILD / "images_and_delta.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if reuse_launcher:
        prior = json.loads((BUILD / "build.json").read_text(encoding="utf-8"))
        assert prior["translation_sha256"] == report["translation_sha256"]
        report["launcher"] = prior["launcher"]
        assert report["launcher"]["sha256"] == sha((BUILD / "EschalonBook_Chinese_Launcher.exe").read_bytes())
    else:
        report["launcher"] = build_launcher()
    (BUILD / "build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main(reuse_launcher="--reuse-launcher" in sys.argv[1:])
