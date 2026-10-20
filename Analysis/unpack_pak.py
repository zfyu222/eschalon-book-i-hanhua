"""Extract zlib-compressed PNG streams from gfx.pak.

gfx.pak has no plaintext index: magic '!PAK', then a sequence of zlib
streams. Each stream inflates to a PNG. This locates every stream by
probing zlib headers and reports dimensions so the launch art can be found.
"""

import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAK = ROOT / "Eschalon_CN" / "gfx.pak"
OUT = Path(__file__).resolve().parent / "pak_extract"

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def png_size(blob):
    if len(blob) < 24 or not blob.startswith(PNG_SIG):
        return None
    return struct.unpack(">II", blob[16:24])


def main():
    OUT.mkdir(exist_ok=True)
    data = PAK.read_bytes()
    print(f"pak size: {len(data):,}")
    print("header:", data[:12].hex())

    index = []
    offset = 0
    while offset < len(data) - 2:
        if data[offset] != 0x78:
            offset += 1
            continue
        chunk = data[offset:]
        probe = zlib.decompressobj()
        try:
            inflated = probe.decompress(chunk)
            inflated += probe.flush()
        except zlib.error:
            offset += 1
            continue
        if not inflated.startswith(PNG_SIG) or not probe.eof:
            offset += 1
            continue
        consumed = len(chunk) - len(probe.unused_data)
        size = png_size(inflated)
        name = f"img_{len(index) + 1:04d}_{offset:08x}.png"
        (OUT / name).write_bytes(inflated)
        index.append((name, offset, consumed, len(inflated), size))
        offset += consumed

    print(f"png streams: {len(index)}")
    for name, off, consumed, raw, size in index:
        print(f"  {name} offset=0x{off:x} stream={consumed:,} png={raw:,} size={size}")

    print("\n-- 800x600 or wider --")
    for name, off, consumed, raw, size in index:
        if size and size[0] >= 800 and size[1] >= 400:
            print(f"  {name} {size[0]}x{size[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
