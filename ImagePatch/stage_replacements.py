"""Stage rendered PNGs under the archive's internal names.

gfx.pak 的目录项名称是 0.png / 1.png 这类序号名，而解包脚本按
img_{序号}_{offset:08x}.png 命名。文件名里的 offset 与目录项的 old_offset 一一对应，
据此把 ImagePatch/out 的产物映射成 rebuild_image_archive.py 需要的替换文件名。

用法：python ImagePatch/stage_replacements.py
"""
import re
import shutil
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_PAK = ROOT / "ImagePatch" / "backup" / "gfx.pak"
PAK = ORIGINAL_PAK if ORIGINAL_PAK.exists() else ROOT / "Eschalon_CN" / "gfx.pak"
OUT_DIR = ROOT / "ImagePatch" / "out"
STAGE_DIR = ROOT / "ImagePatch" / "stage"
PATTERN = re.compile(r"^img_\d+_([0-9a-f]{8})\.png$")
# 启动界面是整体版式图，多行文本与运行时文本层叠加后版式不可控，保持原图。
EXCLUDE = {"launchscreen.png", "mainmenu_linux.png", "linux_launch.png"}


def archive_names(pak_path):
    data = pak_path.read_bytes()
    magic, version, count, packed_size, _ = struct.unpack_from("<5I", data)
    if data[:4] != b"!PAK":
        raise SystemExit("unsupported archive")
    directory = zlib.decompress(data[20:20 + packed_size])
    data_start = 20 + packed_size
    mapping = {}
    for index in range(count):
        size, offset, _, flag = struct.unpack_from("<4I", directory, index * 272)
        name = directory[index * 272 + 16:(index + 1) * 272].split(b"\0", 1)[0].decode("ascii")
        # 解包脚本记录的是文件绝对偏移，目录里存的是相对数据区的偏移。
        mapping[data_start + offset] = name
    return mapping


def main():
    offsets = archive_names(PAK)
    if STAGE_DIR.exists():
        shutil.rmtree(STAGE_DIR)
    STAGE_DIR.mkdir(parents=True)
    staged, skipped = 0, []
    for path in sorted(OUT_DIR.glob("*.png")):
        match = PATTERN.match(path.name)
        if not match:
            skipped.append(path.name)
            continue
        offset = int(match.group(1), 16)
        name = offsets.get(offset)
        if name is None or name in EXCLUDE:
            skipped.append(path.name)
            continue
        shutil.copy2(path, STAGE_DIR / name)
        staged += 1
    print(f"staged {staged} replacements, skipped {len(skipped)}")
    for name in skipped[:10]:
        print(f"  skip {name}")


if __name__ == "__main__":
    main()
