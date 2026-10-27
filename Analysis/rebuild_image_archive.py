"""Rebuild !PAK on an isolated output path; never mutate the installed game."""
import argparse
import hashlib
import struct
import zlib
from pathlib import Path


def rebuild(source, replacements, destination):
    source, replacements, destination = map(Path, (source, replacements, destination))
    if destination.exists() or destination.resolve() == source.resolve():
        raise ValueError('A new output path is required')
    data = source.read_bytes()
    magic, version, count, packed_size, raw_size = struct.unpack_from('<5I', data)
    if data[:4] != b'!PAK' or version != 0x10001:
        raise ValueError('Unsupported archive')
    directory = bytearray(zlib.decompress(data[20:20+packed_size]))
    if len(directory) != raw_size or raw_size != count*272:
        raise ValueError('Invalid directory')
    data_start = 20+packed_size
    chunks, offset, changed, original_images = [], 0, [], {}
    for i in range(count):
        size, old_offset, png_size, flag = struct.unpack_from('<4I', directory, i*272)
        name = directory[i*272+16:(i+1)*272].split(b'\0',1)[0].decode('ascii')
        chunk = data[data_start+old_offset:data_start+old_offset+size]
        image = zlib.decompress(chunk)
        if flag != 2 or len(image) != png_size:
            raise ValueError(f'Invalid image {name}')
        original_images[name] = image
        path = replacements/name
        if path.is_file():
            replacement = path.read_bytes()
            from io import BytesIO
            from PIL import Image
            with Image.open(BytesIO(image)) as a, Image.open(BytesIO(replacement)) as b:
                if a.size != b.size:
                    raise ValueError(f'Image dimensions changed: {name}')
            if replacement != image:
                chunk, png_size = zlib.compress(replacement, 9), len(replacement)
                changed.append(name)
        struct.pack_into('<4I', directory, i*272, len(chunk), offset, png_size, flag)
        chunks.append(chunk)
        offset += len(chunk)
    allowed = set(original_images)
    if {p.name for p in replacements.glob('*.png')} - allowed:
        raise ValueError('Unknown replacement filename')
    encoded = zlib.compress(bytes(directory), 9)
    result = struct.pack('<5I', magic, version, count, len(encoded), raw_size)+encoded+b''.join(chunks)
    # Independently verify every decoded entry and unchanged original resource.
    table = zlib.decompress(result[20:20+len(encoded)])
    start = 20+len(encoded)
    for i, (name, original) in enumerate(original_images.items()):
        n, off, length, flag = struct.unpack_from('<4I', table, i*272)
        decoded = zlib.decompress(result[start+off:start+off+n])
        expected = (replacements/name).read_bytes() if name in changed else original
        if decoded != expected or len(decoded) != length:
            raise ValueError(f'Read-back mismatch: {name}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
    return {'changed': changed, 'entries_verified': count,
            'source_sha256': hashlib.sha256(data).hexdigest(),
            'output_sha256': hashlib.sha256(result).hexdigest()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--replacements', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    import json
    print(json.dumps(rebuild(args.source, args.replacements, args.destination)))
