"""Verify public stable release, guide equivalence, cover and full ZIP download."""
import hashlib,json,subprocess
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'TranslateFiles/reports/release_v19'
expected=json.loads((OUT/'package.json').read_text(encoding='utf-8'))
release=json.loads(subprocess.run(['gh','release','view','v1.9','--repo','zfyu222/eschalon-book-i-hanhua',
 '--json','url,tagName,isDraft,isPrerelease,assets,body'],capture_output=True,text=True,encoding='utf-8',check=True).stdout)
assert not release['isDraft'] and not release['isPrerelease']
assert release['body'].replace('\r','').strip()==(OUT/'release_notes.md').read_bytes().decode('utf-8').replace('\r','').strip()
headers={'User-Agent':'StaticHanHua-release-verifier'}
with urlopen(Request('https://github.com/zfyu222/eschalon-book-i-hanhua/releases/latest',headers=headers),timeout=45) as r:
    assert r.status==200 and r.url.endswith('/v1.9')
asset=next(a for a in release['assets'] if a['name']=='Eschalon.Book.I_.1.9.zip')
assert asset['size']==expected['size'] and asset['state']=='uploaded'
digest=hashlib.sha256();count=0
with urlopen(Request(asset['url'],headers=headers),timeout=45) as r:
    assert r.status==200
    while chunk:=r.read(1024*1024):digest.update(chunk);count+=len(chunk)
assert count==expected['size'] and digest.hexdigest()==expected['sha256']
cover=next(a for a in release['assets'] if a['name']=='title.jpg')
with urlopen(Request(cover['url'],headers=headers),timeout=45) as r:
    assert r.status==200 and r.read()==(ROOT/'Dispatch/Artwork/title.jpg').read_bytes()
report={'status':'passed','version':'1.9','release':release['url'],'download_url':asset['url'],
        'anonymous_download_http':200,'size':count,'sha256':digest.hexdigest(),
        'latest_stable':True,'body_matches_prepared_notes':True,'cover_verified':True,
        'baidu_file_uploaded':False,'in_game_validation':'pending'}
(OUT/'public_download.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
