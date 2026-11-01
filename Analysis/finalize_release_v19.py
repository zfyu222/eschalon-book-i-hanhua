"""Finish the single-entry layout after the shared generator creates the guide."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    stage=ROOT/'Dispatch/Files';payload=ROOT/'Release/v19'
    report=ROOT/'TranslateFiles/reports/release_v19'
    config=json.loads((ROOT/'Release/release_config.json').read_text(encoding='utf-8'))
    m=json.loads((ROOT/'Dispatch/StagingArchive/v18_narrative_tail/PATCH_MANIFEST.json').read_text(encoding='utf-8'))
    out=ROOT/'Dispatch/Eschalon Book I_子非鱼汉化1.9.zip'
    with zipfile.ZipFile(out) as z:guide=z.read('补丁说明.txt').decode('utf-8-sig')
    guide=guide.replace('\r\n','\n')
    important='【重要：启动中文版】\n请运行“埃斯卡隆：卷一_中文版.exe”；直接运行原游戏EXE不能启用本汉化。\n\n'
    guide=guide.replace('游戏介绍\n',important+'游戏介绍\n')
    assert important in guide
    guide=guide.replace('或者网盘链接: '+config['mirror_url'],'或者网盘链接: '+config['share_name']+' '+config['mirror_url'])
    (stage/'补丁说明.txt').write_text(guide,encoding='utf-8-sig')
    m.update(archive=out.name,version='1.9',created='2026-11-01')
    for e in m['files']+m['auxiliary']:
        p=payload/e['path'];e.update(sha256=sha(p),size=p.stat().st_size)
        dest=stage/e.get('archive_path',e['path']);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    direct=stage/'汉化工具/runtime/EschalonBook_Chinese_Launcher.exe'
    if direct.exists():
        direct.rename(report/'generated_direct_layout.exe');direct.parent.rmdir()
    for name in ['gfx.pak','steam_appid.txt']:
        direct=stage/name
        if direct.exists():
            assert sha(direct)==sha(payload/name)
            direct.rename(report/('generated_direct_'+name))
    (stage/'PATCH_MANIFEST.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
    expected={e.get('archive_path',e['path']) for e in m['files']+m['auxiliary']}|{'补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt'}
    assert {p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}-{'SHA256SUMS.txt'}==expected-{'SHA256SUMS.txt'}
    (stage/'SHA256SUMS.txt').write_text(''.join(sha(stage/n)+'  '+n+'\n' for n in sorted(expected) if n!='SHA256SUMS.txt'),encoding='utf-8')
    building=out.with_suffix('.building.zip')
    with zipfile.ZipFile(building,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n in sorted(expected):z.write(stage/n,n)
    building.replace(out)
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for n in expected:assert hashlib.sha256(z.read(n)).hexdigest()==sha(stage/n)
    for n in ['补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt']:shutil.copy2(stage/n,ROOT/'Dispatch'/n)
    config.update(version='1.9',launch_mode='custom_launcher')
    (ROOT/'Release/release_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    data={'version':'1.9','archive':out.name,'size':out.stat().st_size,'sha256':sha(out),'files':len(expected),'crc':'passed','hashes':'passed','in_game_validation':'pending'}
    (report/'package.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(data,ensure_ascii=False))
if __name__=='__main__':main()
