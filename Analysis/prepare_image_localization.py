"""Verify existing PNG stream exports and preserve game-archive provenance."""
import hashlib
import json
import re
import zlib
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'ImageText'
PAK = ROOT / 'Game' / 'gfx.pak'


def main():
    OUT.mkdir(exist_ok=True)
    data = PAK.read_bytes()
    archive_hash = hashlib.sha256(data).hexdigest()
    provenance = {}
    paths = sorted((ROOT / 'Analysis' / 'pak_extract').glob('*.png'))
    for path in paths:
        match = re.fullmatch(r'img_(\d+)_(\w+)\.png', path.name)
        if not match:
            raise ValueError(path.name)
        offset = int(match[2], 16)
        stream = zlib.decompressobj()
        raw = stream.decompress(data[offset:]) + stream.flush()
        if not stream.eof or raw != path.read_bytes():
            raise ValueError(f'Export does not match archive: {path}')
        provenance[path.name] = {
            'asset': 'gfx.pak', 'archive_sha256': archive_hash,
            'stream_offset': offset,
            'compressed_size': len(data) - offset - len(stream.unused_data),
            'resource_index': int(match[1]),
        }
    (OUT / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    known_text = {28,34,35,37,38,39,42,44,45,46,47,48,49,53,54,55,56,
                  89,90,91,93,94,96,97,102,147,176,178,179,186,197,198,199,
                  200,203,205,206,207,208,212,215,216,218,224}
    policy = {'script': 'latin', 'negative_samples': 20, 'weak_samples': 10,
              'ordinary_samples': 10, 'qwen_batch': 100, 'seed': 42,
              'families': {}, 'images': {}}
    for path in paths:
        if provenance[path.name]['resource_index'] in known_text:
            policy['images'][path.name] = {'known_text': True, 'risks': ['art']}
    policy['calibration'] = {
        'reviewer': 'conversation_agent',
        'evidence': 'contact_01.png through contact_12.png visually inspected; mixed gold art text, white body text, tiny map labels, sprite sheets and scenery. No ordinary-font fast path validated from thumbnails.',
        'limitations': 'Contact sheets establish text presence only. Exact wording and boxes require full-resolution visual adjudication.'}
    (OUT / 'policy-v1.json').write_text(json.dumps(policy, indent=2) + '\n', encoding='utf-8')
    # Every exported asset is visible on numbered pages, without OCR answers.
    for page in range((len(paths) + 19) // 20):
        sheet = Image.new('RGB', (1200, 1050), '#555555')
        draw = ImageDraw.Draw(sheet)
        for index, path in enumerate(paths[page*20:(page+1)*20]):
            pic = Image.open(path).convert('RGBA')
            pic.thumbnail((285, 175))
            x, y = (index % 4) * 300, (index // 4) * 210
            sheet.paste(pic, (x, y+24), pic)
            draw.text((x+4, y+3), path.name, fill='white')
        sheet.save(OUT / f'contact_{page+1:02d}.png')
    print(json.dumps({'verified_exports': len(paths), 'archive_sha256': archive_hash}))


if __name__ == '__main__':
    main()
