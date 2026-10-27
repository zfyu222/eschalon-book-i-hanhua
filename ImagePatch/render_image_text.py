"""Prototype: repaint one gfx.pak image region with Chinese text.

清字用 cv2.inpaint 只修补「比局部背景更亮」的文字笔画像素，保留石纹；
再用中文字体按区域尺寸自适应渲染译文。

用法：python ImagePatch/render_image_text.py img_0034
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MAPPING = ROOT / "eschalonbook_images_text.mapping.json"
SOURCE_CSV = ROOT / "eschalonbook_images_text.csv"
TARGET_CSV = ROOT / "eschalonbook_images_text_translated.csv"
SRC_DIR = ROOT / "Analysis" / "pak_extract"
OUT_DIR = ROOT / "ImagePatch" / "out"
FONT = Path("C:/Windows/Fonts/msyhbd.ttc")
FONT_INDEX = 0
# 这些区域由游戏运行时文本绘制覆盖，贴图里只清字、不烧字，避免同一句话出现两次。
CLEAR_ONLY_ROWS = set()



def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [(row[0] if row else "") for row in csv.reader(stream)]


def text_mask(bgr, box, inset=1):
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0 = max(0, x0 + inset), max(0, y0 + inset)
    x1, y1 = min(bgr.shape[1], x1 - inset), min(bgr.shape[0], y1 - inset)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    patch = bgr[y0:y1, x0:x1]
    if patch.size == 0:
        return None
    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
    flat = flat_background(patch)
    if flat is not None:
        base = float(flat.astype(float) @ np.array([0.114, 0.587, 0.299]))
        spread = 32.0
    else:
        ring = np.concatenate([
            gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1],
        ])
        base = float(np.median(ring))
        sigma = float(np.percentile(np.abs(ring.astype(float) - base), 70))
        spread = min(max(sigma * 2.2, 14.0), 90.0)
    mask = (np.abs(gray.astype(float) - base) > spread).astype(np.uint8) * 255
    if int((mask > 0).sum()) < 12 or int((mask > 0).sum()) > gray.size * 0.8:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        low = float(gray[binary == 0].mean()) if (binary == 0).any() else None
        high = float(gray[binary > 0].mean()) if (binary > 0).any() else None
        if low is not None and high is not None:
            background_is_low = abs(low - base) <= abs(high - base)
            mask = binary if background_is_low else (255 - binary)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
    full = np.zeros(bgr.shape[:2], np.uint8)
    full[y0:y1, x0:x1] = mask
    return full, patch, gray


def flat_background(patch):
    """Return the background colour when the patch sits on an even background.

    取四角小块的中位数：白色文本框、纯色按钮、纸面都会被判定为平坦背景，
    石纹/渐变背景则返回 None 交给 inpaint。
    """
    height, width = patch.shape[:2]
    corner = max(3, min(8, height // 6, width // 6))
    blocks = [
        patch[0:corner, 0:corner],
        patch[0:corner, width - corner:width],
        patch[height - corner:height, 0:corner],
        patch[height - corner:height, width - corner:width],
    ]
    means = np.array([
        block.reshape(-1, block.shape[-1])[:, :3].astype(float).mean(axis=0)
        for block in blocks
    ])
    spread = means.max(axis=0) - means.min(axis=0)
    if float(spread.max()) > 34.0:
        return None
    return np.median(means, axis=0).astype(np.uint8)


def text_color(patch, mask_patch, background=None):
    pixels = patch[mask_patch > 0]
    if pixels.size == 0:
        return (255, 255, 255)
    if background is not None:
        distance = np.linalg.norm(
            pixels.astype(float) - background.astype(float), axis=1
        )
        selected = pixels[distance >= np.percentile(distance, 70)]
    else:
        luminance = pixels.astype(float) @ np.array([0.114, 0.587, 0.299])
        selected = pixels[luminance >= np.percentile(luminance, 70)]
    mean = selected.mean(axis=0)
    return tuple(int(v) for v in mean[::-1])


def layout(draw, text, box_w, box_h):
    """Return the font and wrapped lines that fit inside the region."""
    width = max(8, int(box_w))
    height = max(8, int(box_h))
    size = max(9, int(height * 0.78))
    while size >= 9:
        font = ImageFont.truetype(str(FONT), size, index=FONT_INDEX)
        step = max(1.0, size * 1.18)
        lines = []
        for paragraph in text.split("\n"):
            if not paragraph:
                lines.append("")
                continue
            current = ""
            for char in paragraph:
                candidate = current + char
                if draw.textlength(candidate, font=font) <= width or not current:
                    current = candidate
                else:
                    lines.append(current)
                    current = char
            if current:
                lines.append(current)
        if len(lines) * step <= height + 1:
            return font, lines, step
        size -= 1
    font = ImageFont.truetype(str(FONT), 9, index=FONT_INDEX)
    return font, [text], 11.0


def _region_box(region, width, height, inset=1):
    x0, y0, x1, y1 = [int(round(v)) for v in region["box"]]
    x0, y0 = max(0, x0 + inset), max(0, y0 + inset)
    x1, y1 = min(width, x1 - inset), min(height, y1 - inset)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return None
    return x0, y0, x1, y1


def render(image_path, regions, sources, targets, out_path):
    raw = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise SystemExit(f"cannot read {image_path}")
    alpha = None
    if raw.ndim == 3 and raw.shape[2] == 4:
        alpha = raw[:, :, 3].copy()
        bgr = raw[:, :, :3]
    else:
        bgr = raw
    height, width = bgr.shape[:2]
    # gfx.pak 中部分界面图是「alpha 遮罩」：RGB 恒为深灰，形状完全由 alpha 表达。
    alpha_layer = alpha is not None and int(alpha.min()) < 10 and float(alpha.mean()) < 200

    work = bgr.copy()
    alpha_image = Image.fromarray(alpha, "L") if alpha_layer else None
    alpha_draw = ImageDraw.Draw(alpha_image) if alpha_image is not None else None

    for region in regions:
        row = region["csv_row"]
        if targets[row - 1].strip() == sources[row - 1].strip():
            continue
        box = _region_box(region, width, height)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        # 原字形上下缘（降部、下划线）常溢出 mapping 的框，纵向再放宽 2px 才清得干净。
        y0, y1 = max(0, y0 - 2), min(height, y1 + 2)
        if alpha_layer:
            alpha_draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=0)
            continue
        mask_info = text_mask(bgr, region["box"])
        if mask_info is None:
            continue
        flat = flat_background(mask_info[1])
        if flat is not None:
            work[y0:y1, x0:x1] = flat
            continue
        rect = np.zeros((height, width), np.uint8)
        rect[y0:y1, x0:x1] = 255
        work = cv2.inpaint(work, rect, 4, cv2.INPAINT_TELEA)

    pil = Image.fromarray(cv2.cvtColor(work, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil)
    for region in regions:
        row = region["csv_row"]
        target = targets[row - 1].strip()
        if not target or target == sources[row - 1].strip():
            continue
        if row in CLEAR_ONLY_ROWS:
            continue
        box = _region_box(region, width, height)
        if box is None:
            continue
        x0, y0, x1, y1 = box
        if alpha_layer:
            patch = bgr[y0:y1, x0:x1]
            opaque = alpha[y0:y1, x0:x1] > 128
            if opaque.any():
                color = tuple(int(v) for v in np.median(patch[opaque], axis=0)[::-1])
            else:
                color = (235, 235, 235)
        else:
            mask_info = text_mask(bgr, region["box"])
            if mask_info is None:
                continue
            flat = flat_background(mask_info[1])
            color = text_color(mask_info[1], mask_info[2] > 0, flat)
        font, lines, step = layout(draw, target, x1 - x0, y1 - y0)
        total = step * len(lines)
        ty = y0 + ((y1 - y0) - total) / 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            tx = x0 + ((x1 - x0) - tw) // 2 - bbox[0]
            if alpha_layer:
                alpha_draw.text((tx, ty), line, font=font, fill=255)
            else:
                shadow = tuple(max(0, c - 90) for c in color)
                draw.text((tx + 1, ty + 1), line, font=font, fill=shadow)
            draw.text((tx, ty), line, font=font, fill=color)
            ty += step

    final = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    if alpha_layer:
        final = np.dstack([final, np.array(alpha_image)])
    elif alpha is not None:
        final = np.dstack([final, alpha])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), final)
    print(f"{out_path.name}: {len(regions)} regions" + (" (alpha mask)" if alpha_layer else ""))


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else "img_0034"
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    sources = read_rows(SOURCE_CSV)
    targets = read_rows(TARGET_CSV)
    grouped = {}
    for region in mapping["regions"]:
        if not region["sources"]:
            continue
        path = region["sources"][0]["path"]
        if prefix != "all" and not path.startswith(prefix):
            continue
        grouped.setdefault(path, []).append(region)
    if not grouped:
        raise SystemExit(f"no regions for {prefix}")
    for name, regions in sorted(grouped.items()):
        render(SRC_DIR / name, regions, sources, targets, OUT_DIR / name)


if __name__ == "__main__":
    main()
