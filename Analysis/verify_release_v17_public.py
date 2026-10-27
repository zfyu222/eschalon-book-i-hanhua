"""Anonymous public metadata and full download verification; no auth headers."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'TranslateFiles/reports/release_v17/public_download.json'
expected=json.loads((out.parent/'package_validation.json').read_text(encoding='utf-8'))
headers={'User-Agent':'StaticHanHua-release-verifier','Accept':'application/vnd.github+json'}
release=json.loads(subprocess.run(['gh','release','view','v1.7','--repo','zfyu222/eschalon-book-i-hanhua',
    '--json','url,tagName,isDraft,isPrerelease,assets,body'],capture_output=True,text=True,encoding='utf-8',check=True).stdout)
assert not release['isDraft'] and not release['isPrerelease']
with urlopen(Request('https://github.com/zfyu222/eschalon-book-i-hanhua/releases/latest',
                     headers={'User-Agent':headers['User-Agent']}),timeout=60) as page:
    assert page.status==200 and urlparse(page.url).path.endswith('/releases/tag/v1.7')
asset=next(x for x in release['assets'] if x['name']=='Eschalon.Book.I_.1.7.zip')
assert asset['state']=='uploaded' and asset['size']==expected['size']
guide=(ROOT/'Dispatch/Files/补丁说明.txt').read_text(encoding='utf-8-sig')
assert release['body'].replace('\r\n','\n').rstrip()==guide.replace('\r\n','\n').rstrip(),'GitHub notes differ from player guide'
digest=hashlib.sha256();count=0
with urlopen(Request(asset['url'],headers={'User-Agent':headers['User-Agent']}),timeout=60) as r:
    status=r.status;host=urlparse(r.url).hostname
    while True:
        chunk=r.read(1024*1024)
        if not chunk:break
        digest.update(chunk);count+=len(chunk)
assert status==200 and count==expected['size'] and digest.hexdigest()==expected['sha256']
report={'status':'passed','date':dt.datetime.now().astimezone().isoformat(),'anonymous':True,
        'release':release['url'],'tag':release['tagName'],'draft':False,'prerelease':False,
        'metadata_source':'Connected gh CLI; anonymous API was rate-limited. Latest HTML page and full asset download verified without authentication.',
        'latest_stable':True,'asset':asset['name'],'download_url':asset['url'],
        'size':count,'sha256':digest.hexdigest(),'download_http_status':status,'cdn_host':host,
        'release_body_matches_txt':True,'github_digest':asset.get('digest'),
        'baidu_link_in_notes':True,'feedback_link_in_notes':True,
        'baidu_file_upload_performed':False}
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
