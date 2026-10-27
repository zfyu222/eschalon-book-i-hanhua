"""Validate the documented !PAK header and fixed-size image directory."""
import hashlib
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = (ROOT / 'Game/gfx.pak').read_bytes()
magic, version, count, index_size, raw_size = struct.unpack_from('<5I', data)
assert data[:4] == b'!PAK' and version == 0x10001
directory = zlib.decompress(data[20:20+index_size])
assert len(directory) == raw_size == count * 272
start = 20 + index_size
entries = []
for i in range(count):
    entry = directory[i*272:(i+1)*272]
    compressed_size, relative_offset, png_size, flag = struct.unpack_from('<4I', entry)
    name = entry[16:].split(b'\0', 1)[0].decode('ascii')
    encoded = data[start+relative_offset:start+relative_offset+compressed_size]
    image = zlib.decompress(encoded)
    assert flag == 2 and len(image) == png_size and image.startswith(b'\x89PNG\r\n\x1a\n')
    exported = ROOT / 'Analysis/pak_extract' / f'img_{i+1:04d}_{start+relative_offset:08x}.png'
    assert exported.read_bytes() == image
    entries.append(dict(name=name, resource_index=i+1, offset=start+relative_offset,
                        compressed_size=compressed_size, png_size=png_size,
                        png_sha256=hashlib.sha256(image).hexdigest()))
assert start + sum(e['compressed_size'] for e in entries) == len(data)
report = dict(archive_sha256=hashlib.sha256(data).hexdigest(), count=count,
              entry_size=272, header_size=20, data_start=start,
              all_entries_validated=True, entries=entries)
(ROOT/'ImageText/archive_index.json').write_text(json.dumps(report, indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='entries'}))
