"""Verify ZIP integrity and replay real player scripts in disposable directories."""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ZIP=ROOT/'Dispatch/Eschalon Book I_子非鱼汉化1.7.zip'
OUT=ROOT/'TranslateFiles/reports/release_v17'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names)
    manifest=json.loads(z.read('PATCH_MANIFEST.json').decode('utf-8'))
    guide_raw=z.read('补丁说明.txt');assert guide_raw.startswith(b'\xef\xbb\xbf')
    guide=guide_raw.decode('utf-8-sig')
    assert '运行情况' not in guide
    for text in ['https://pan.baidu.com/s/5CzGvEaOYAUHbh8iBc-Jsww',
                 'https://docs.qq.com/sheet/DTnhoaFZweVRoV2t0?tab=BB08J2',
                 '本补丁使用 AI 辅助翻译，请适当降低预期。']:
        assert text in guide
    assert guide.index('下载与反馈')<guide.index('安装汉化')<guide.index('补丁升级')<guide.index('卸载汉化')
    assert all(f'v1.{n}' in guide for n in range(8))
    assert 'eschalon_book_1.exe' not in names
    expected={'补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt'}
    for item in manifest['files']+manifest['auxiliary']:
        name=item.get('archive_path',item['path']);expected.add(name)
        assert hashlib.sha256(z.read(name)).hexdigest()==item['sha256']
    assert names==expected
    for line in z.read('SHA256SUMS.txt').decode('utf-8').splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(z.read(name)).hexdigest()==digest
results=[]
original_hash='0ffbf360080320dd91b98034431a1644b703ff32ecabb306560dfd7da55825d9'
assert sha(ROOT/'Game/gfx.pak')==original_hash
def action(folder,verb,success=True):
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
             str(folder/'汉化工具/patch.ps1'),'-Action',verb,'-NoLaunch'],capture_output=True)
    assert (result.returncode==0)==success,(verb,result.returncode,result.stdout,result.stderr)
    return result.stdout
def seed(base,name,legacy=False):
    folder=base/name;folder.mkdir()
    with zipfile.ZipFile(ZIP) as z:z.extractall(folder)
    shutil.copy2(ROOT/'Eschalon_CN/eschalon_book_1.exe',folder/'eschalon_book_1.exe')
    if legacy:
        for n in ['gfx.pak','EschalonBook_Chinese_Launcher.exe','steam_appid.txt']:
            shutil.copy2(ROOT/'Release/v16'/n,folder/n)
    else:shutil.copy2(ROOT/'Game/gfx.pak',folder/'gfx.pak')
    return folder

with tempfile.TemporaryDirectory(prefix='eschalon-v17-player-tests-') as temporary:
    base=Path(temporary).resolve()
    assert base.parent==Path(tempfile.gettempdir()).resolve() and base.name.startswith('eschalon-v17-player-tests-')
    fresh=seed(base,'fresh')
    action(fresh,'install')
    for item in manifest['files']:assert sha(fresh/item['path'])==item['sha256']
    action(fresh,'install');results+=['fresh_install','repeat_install']
    assert sha(fresh/'.zfy-localization/original/gfx.pak')==original_hash
    # Exercise a real changed-payload upgrade in this fixture only. This PE is
    # not executed; formal ZIP and release payload are never changed.
    payload=fresh/'汉化文件/EschalonBook_Chinese_Launcher.exe'
    with payload.open('ab') as f:f.write(b'fixture-version-upgrade')
    fixture_manifest=json.loads((fresh/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
    for item in fixture_manifest['files']:
        if item['path']=='EschalonBook_Chinese_Launcher.exe':item['sha256']=sha(payload)
    (fresh/'PATCH_MANIFEST.json').write_text(json.dumps(fixture_manifest),encoding='utf-8')
    action(fresh,'install');assert sha(fresh/'EschalonBook_Chinese_Launcher.exe')==sha(payload)
    assert sha(fresh/'.zfy-localization/original/gfx.pak')==original_hash
    results.append('changed_payload_upgrade_preserves_original')
    action(fresh,'uninstall');assert sha(fresh/'gfx.pak')==original_hash
    assert not (fresh/'EschalonBook_Chinese_Launcher.exe').exists()
    action(fresh,'uninstall');action(fresh,'install');action(fresh,'uninstall')
    assert sha(fresh/'gfx.pak')==original_hash
    results+=['uninstall_restores_original','repeat_uninstall','reinstall_after_uninstall']
    old=seed(base,'legacy_v16',True)
    action(old,'install')
    for item in manifest['files']:assert sha(old/item['path'])==item['sha256']
    state=json.loads((old/'.zfy-localization/state.json').read_text(encoding='utf-8-sig'))
    gfx=next(x for x in state['records'] if x['path']=='gfx.pak')
    assert gfx['restore_steam'] and not gfx['original']
    assert b'STEAM_RESTORE=True' in action(old,'uninstall')
    assert not (old/'EschalonBook_Chinese_Launcher.exe').exists()
    results+=['legacy_v16_upgrade','legacy_v16_uninstall_requests_steam_restore_without_launching_it']
    corrupt=seed(base,'corrupt')
    (corrupt/'汉化文件/steam_appid.txt').write_bytes(b'corrupt')
    action(corrupt,'install',False)
    assert sha(corrupt/'gfx.pak')==original_hash and not (corrupt/'EschalonBook_Chinese_Launcher.exe').exists()
    results.append('corrupt_payload_changes_nothing')
    changed=seed(base,'external_change')
    action(changed,'install');(changed/'EschalonBook_Chinese_Launcher.exe').write_bytes(b'user-change')
    action(changed,'uninstall',False);action(changed,'install',False)
    assert (changed/'EschalonBook_Chinese_Launcher.exe').read_bytes()==b'user-change'
    assert sha(changed/'gfx.pak')==next(x['sha256'] for x in manifest['files'] if x['path']=='gfx.pak')
    results.append('externally_changed_file_preserved')
    wrong=seed(base,'wrong_version');(wrong/'eschalon_book_1.exe').write_bytes(b'unsupported')
    action(wrong,'install',False)
    assert sha(wrong/'gfx.pak')==original_hash and not (wrong/'EschalonBook_Chinese_Launcher.exe').exists()
    results.append('wrong_exe_version_changes_nothing')
report={'status':'passed','archive':ZIP.name,'sha256':sha(ZIP),'size':ZIP.stat().st_size,
        'crc':'passed','manifest_and_sums':'passed','files':sorted(names),
        'player_script_cases':results,'real_game_directory_modified':False,
        'steam_validation_launched_during_tests':False}
(OUT/'package_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
