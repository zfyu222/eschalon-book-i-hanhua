"""Replay the real adapter/installer with a harmless launcher in an isolated folder."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tempfile, time

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'Dispatch/Files'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(folder, action='launch', success=True):
    script=folder/'汉化工具'/('launch.ps1' if action=='launch' else 'patch.ps1')
    args=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script)]
    if action!='launch': args+=['-Action',action,'-NoLaunch']
    r=subprocess.run(args,capture_output=True,timeout=60)
    assert (r.returncode==0)==success,(r.returncode,r.stdout,r.stderr)
    if action=='launch' and success: time.sleep(1)

checks=[]
with tempfile.TemporaryDirectory(prefix='eschalon-entry-') as td:
    base=Path(td); folder=base/'中文 空格 游戏';shutil.copytree(STAGE,folder)
    cfg=folder/'汉化工具/config.json';c=json.loads(cfg.read_text(encoding='utf-8'));c['exe']='fixture_game.exe';cfg.write_text(json.dumps(c),encoding='utf-8')
    # The shipped translation binary is never executed during this test.
    source=base/'stub.cs';source.write_text('using System; using System.IO; class Stub { static void Main(){File.AppendAllText(Path.Combine(Environment.GetEnvironmentVariable("ESCHALON_RUNTIME"),"started.txt"),"start\\n");}}')
    stub=base/'stub.exe'
    subprocess.run(['C:/Windows/Microsoft.NET/Framework/v4.0.30319/csc.exe','/nologo','/target:winexe','/out:'+str(stub),str(source)],check=True)
    shutil.copy2(stub,folder/'汉化文件/EschalonBook_Chinese_Launcher.exe')
    mf=folder/'PATCH_MANIFEST.json';m=json.loads(mf.read_text(encoding='utf-8'))
    item=next(x for x in m['files'] if x['path'].endswith('Launcher.exe'));item['sha256']=sha(stub);item['size']=stub.stat().st_size
    mf.write_text(json.dumps(m),encoding='utf-8')
    shutil.copy2(ROOT/'Eschalon_CN/eschalon_book_1.exe',folder/'fixture_game.exe')
    (folder/'gfx.pak').write_bytes(b'fixture original art');original=sha(folder/'gfx.pak')
    run(folder);checks.append('fresh_install_and_launch')
    state=folder/'.zfy-localization/state.json';before=state.stat().st_mtime_ns
    target=folder/item['path'];mtime=target.stat().st_mtime_ns
    run(folder);assert state.stat().st_mtime_ns==before and target.stat().st_mtime_ns==mtime
    checks.append('installed_launch_without_reinstall')
    target.unlink();run(folder);assert sha(target)==item['sha256'];checks.append('missing_file_repaired')
    m['version']='fixture-next';mf.write_text(json.dumps(m),encoding='utf-8');run(folder)
    assert json.loads(state.read_text(encoding='utf-8-sig'))['package_version']=='fixture-next'
    assert sha(folder/'.zfy-localization/original/gfx.pak')==original
    checks.append('version_upgrade_preserves_original')
    time.sleep(0.5);marker=folder/'started.txt';count=marker.read_text().count('start')
    target.write_bytes(b'foreign change');run(folder,success=False);time.sleep(0.3)
    assert target.read_bytes()==b'foreign change' and marker.read_text().count('start')==count
    checks.append('changed_file_refused_without_launch')
    shutil.copy2(stub,target)
    (folder/'汉化文件/steam_appid.txt').write_bytes(b'bad');target.unlink();run(folder,success=False)
    assert not target.exists();checks.append('corrupt_payload_refused')
    shutil.copy2(STAGE/'汉化文件/steam_appid.txt',folder/'汉化文件/steam_appid.txt');run(folder)
    r=subprocess.run([str(folder/'埃斯卡隆：卷一_中文版.exe')],timeout=60);assert r.returncode==0
    time.sleep(1);checks.append('compiled_exe_chinese_and_space_path')
    run(folder,'uninstall');assert sha(folder/'gfx.pak')==original and not target.exists()
    checks.append('uninstall_restores_original')
    # Replay an actual v1.7 installation state, then upgrade to the new layout.
    shutil.copy2(ROOT/'Dispatch/StagingArchive/v17_single_entry/汉化工具/patch.ps1',folder/'汉化工具/old.ps1')
    old=json.loads((ROOT/'Dispatch/StagingArchive/v17_single_entry/PATCH_MANIFEST.json').read_text(encoding='utf-8'))
    old['files'][0]['sha256']=sha(stub);old['files'][0]['size']=stub.stat().st_size
    mf.write_text(json.dumps(old),encoding='utf-8')
    r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(folder/'汉化工具/old.ps1'),'-Action','install','-NoLaunch'],capture_output=True,timeout=60)
    assert r.returncode==0,(r.stdout,r.stderr)
    assert (folder/'EschalonBook_Chinese_Launcher.exe').exists()
    mf.write_text(json.dumps(m),encoding='utf-8');run(folder)
    assert target.exists() and not (folder/'EschalonBook_Chinese_Launcher.exe').exists()
    run(folder,'uninstall');assert sha(folder/'gfx.pak')==original
    checks.append('v17_layout_migration_and_uninstall')
report={'status':'passed','cases':checks,'real_game_started':False,'real_game_modified':False}
out=ROOT/'TranslateFiles/reports/single_entry';out.mkdir(parents=True,exist_ok=True)
(out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
