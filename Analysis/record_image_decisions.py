"""Bind manually authored, visually checked decisions to a review package."""
import argparse
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('spec')
a = p.parse_args()
spec_path = Path(a.spec)
spec = json.loads(spec_path.read_text(encoding='utf-8'))
records = []
for item in spec['decisions']:
    i, entries = item[0], item[1]
    records.append({'id': str(i), 'status': 'text' if entries else 'no_text',
        'reason': '对话Agent已查看证据图，逐项核对可见文字及区域。' if entries else '对话Agent已查看，角色/场景/物件图像没有可辨文字。',
        'unreadable': False,
        'regions': [{'text': t, 'box': ([round(v*1000/item[2][k%2]) for k,v in enumerate(b)] if len(item)>2 else b)} for t,b in entries]})
for i in spec.get('uncertain', []):
    records.append({'id':str(i),'status':'uncertain','reason':'已查看，但文字无法可靠辨认，保留未决。','unreadable':True,'regions':[]})
target = spec_path.with_name(spec_path.stem + '-reply.json')
target.write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(target)
