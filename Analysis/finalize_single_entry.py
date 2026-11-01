"""Refresh metadata and build the reviewed v1.8 Files directory into a new ZIP."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]
stage=ROOT/'Dispatch/Files'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((stage/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
assert m['version']=='1.8' and m['launch_mode']=='custom_launcher'
assert not (stage/'安装汉化.cmd').exists()
for x in m['files']+m['auxiliary']:
    p=stage/x.get('archive_path',x['path'])
    if x in m['files']: assert sha(p)==x['sha256']
    else: x.update(sha256=sha(p),size=p.stat().st_size)
(stage/'PATCH_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
expected={x.get('archive_path',x['path']) for x in m['files']+m['auxiliary']}|{'补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt'}
assert {p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}==expected
(stage/'SHA256SUMS.txt').write_text(''.join(sha(stage/n)+'  '+n+'\n' for n in sorted(expected) if n!='SHA256SUMS.txt'),encoding='utf-8')
for n in ['PATCH_MANIFEST.json','SHA256SUMS.txt']:shutil.copy2(stage/n,ROOT/'Dispatch'/n)
out=ROOT/'Dispatch'/m['archive']
with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_DEFLATED) as z:
    for n in sorted(expected):z.write(stage/n,n)
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    for n in expected:assert hashlib.sha256(z.read(n)).hexdigest()==sha(stage/n)
report={'archive':out.name,'sha256':sha(out),'size':out.stat().st_size,'crc':'passed','file_hashes':'passed','files':len(expected),'published':False}
(ROOT/'TranslateFiles/reports/single_entry/package.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
