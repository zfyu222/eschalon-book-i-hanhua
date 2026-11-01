"""Validate frozen code, package, authorization and actual no-launch upgrade."""
import hashlib,json,marshal,shutil,subprocess,sys,tempfile,types,zipfile
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'TranslateFiles/reports/release_v19'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stage=ROOT/'Dispatch/Files'
m=json.loads((stage/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
check=json.loads((OUT/'release_check.json').read_text(encoding='utf-8'))
assert check['in_game_validation']=='pending' and check['authorization']=='explicit_user_release'
assert {(e['path'],e['sha256']) for e in m['files']+m['auxiliary']}=={(e['game_path'],e['sha256']) for e in check['payload_files']}
with zipfile.ZipFile(ROOT/'Dispatch'/m['archive']) as z:
    assert z.testzip() is None
    for e in m['files']+m['auxiliary']:
        assert hashlib.sha256(z.read(e.get('archive_path',e['path']))).hexdigest()==e['sha256']
    for line in z.read('SHA256SUMS.txt').decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
    guide=z.read('补丁说明.txt').decode('utf-8-sig')
    assert '【重要：启动中文版】' in guide
    for v in range(10):
        if v:assert 'v1.'+str(v) in guide
candidate=stage/'汉化文件/EschalonBook_Chinese_Launcher.exe'
a=CArchiveReader(str(candidate));frozen=marshal.loads(a.extract('display_hook_launcher'))
def shape(c):
    return (c.co_code,c.co_names,c.co_varnames,c.co_freevars,c.co_cellvars,c.co_exceptiontable,
            tuple(shape(v) if isinstance(v,types.CodeType) else v for v in c.co_consts))
assert shape(frozen)==shape(compile((ROOT/'display_hook_launcher.py').read_text(encoding='utf-8'),frozen.co_filename,'exec'))
for key in a.toc:
    name=key.replace('\\','/')
    if name.endswith('.csv') or name.startswith('fonts/') or name=='runtime_fragment_overrides.json':
        assert a.extract(key)==(ROOT/name).read_bytes(),name
def install(folder):
    r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(folder/'汉化工具/patch.ps1'),'-Action','install','-NoLaunch'],capture_output=True,timeout=60)
    assert r.returncode==0,(r.stdout,r.stderr)
with tempfile.TemporaryDirectory(prefix='eschalon-v19-real-upgrade-') as td:
    folder=Path(td)/'中文 空格 游戏'
    shutil.copytree(ROOT/'Dispatch/StagingArchive/v18_narrative_tail',folder)
    shutil.copy2(ROOT/'Eschalon_CN/eschalon_book_1.exe',folder/'eschalon_book_1.exe')
    original=b'isolated original texture fixture';(folder/'gfx.pak').write_bytes(original)
    install(folder)
    old=json.loads((folder/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
    target=folder/'汉化工具/runtime/EschalonBook_Chinese_Launcher.exe'
    assert sha(target)==old['files'][0]['sha256']
    shutil.copytree(stage,folder,dirs_exist_ok=True);install(folder)
    assert sha(target)==sha(candidate)
    assert (folder/'.zfy-localization/original/gfx.pak').read_bytes()==original
    before=target.stat().st_mtime_ns;install(folder);assert target.stat().st_mtime_ns==before
report={'status':'passed','crc_and_hashes':True,'authorized_payload_paths_match':True,
        'frozen_code_and_resources_match':True,'v18_to_v19_actual_binary_no_launch_upgrade':True,
        'repeat_install_no_rewrite':True,'original_preserved':True,'real_game_started':False,'in_game_validation':'pending'}
(OUT/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
notes='![埃斯卡隆：卷一 子非鱼汉化](https://github.com/zfyu222/eschalon-book-i-hanhua/releases/download/v1.9/title.jpg)\n\n'+guide.replace('【重要：启动中文版】','**重要：启动中文版**')
(OUT/'release_notes.md').write_text(notes,encoding='utf-8')
shutil.copy2(ROOT/'Dispatch'/m['archive'],ROOT/'Release/Eschalon.Book.I_.1.9.zip')
