"""Prepare v1.7 payload/config and prove frozen components match tested sources."""
import hashlib
import json
import shutil
import types
import marshal
from pathlib import Path
import zipfile

from PyInstaller.archive.readers import CArchiveReader

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def code_shape(code):
    return (code.co_code,code.co_names,code.co_varnames,code.co_freevars,code.co_cellvars,
            code.co_exceptiontable,tuple(code_shape(c) if isinstance(c,types.CodeType) else c for c in code.co_consts))

def main():
    candidate=ROOT/'Release/levelup_fix/EschalonBook_Chinese_Launcher.exe'
    tested=json.loads((ROOT/'Analysis/levelup_fix_build.json').read_text(encoding='utf-8'))
    assert sha(candidate)==tested['candidate']['sha256']
    assert sha(ROOT/'display_hook_launcher.py')==tested['candidate']['source_hook_sha256']
    assert tested['tests']['levelup_skill_help_visual'].startswith('passed')
    archive=CArchiveReader(str(candidate))
    frozen=marshal.loads(archive.extract('display_hook_launcher'))
    source=compile((ROOT/'display_hook_launcher.py').read_text(encoding='utf-8'),str(ROOT/'display_hook_launcher.py'),'exec')
    assert code_shape(frozen)==code_shape(source),'Frozen code does not match tested source'
    resources=['translated_strings.csv','translated_strings_translated.csv','eschalonbook_text.csv',
               'eschalonbook_text_translated.csv','runtime_fragment_overrides.json',
               'fonts/cn_OldTymeBG.ttf','fonts/cn_Fantasy.ttf','fonts/cn_DS_Celtic_1.ttf']
    resource_hashes={}
    for name in resources:
        key=next(k for k in archive.toc if k.replace('\\','/')==name)
        blob=archive.extract(key)
        assert blob==(ROOT/name).read_bytes(),name
        resource_hashes[name]=hashlib.sha256(blob).hexdigest()
    payload=ROOT/'Release/v17'
    payload.mkdir(exist_ok=True)
    for source in [candidate,ROOT/'Release/v16/gfx.pak',ROOT/'Release/v16/steam_appid.txt']:
        destination=payload/source.name
        if destination.exists():assert sha(destination)==sha(source),'Refusing to overwrite different payload'
        else:shutil.copy2(source,destination)
    original='0ffbf360080320dd91b98034431a1644b703ff32ecabb306560dfd7da55825d9'
    legacy={}
    for path in (ROOT/'Dispatch').glob('Eschalon Book I_子非鱼汉化*.zip'):
        with zipfile.ZipFile(path) as z:
            if 'PATCH_MANIFEST.json' in z.namelist():
                manifest=json.loads(z.read('PATCH_MANIFEST.json').decode('utf-8-sig'))
            else:
                # Earliest historical ZIP was only a guide; preserve any real
                # legacy payload if present, without assuming a modern manifest.
                manifest={'files':[{'path':n,'sha256':hashlib.sha256(z.read(n)).hexdigest()}
                    for n in z.namelist() if n in ['EschalonBook_Chinese_Launcher.exe','gfx.pak','steam_appid.txt']]}
        for item in manifest['files']:
            name=item['path'];digest=item['sha256']
            if name not in ['EschalonBook_Chinese_Launcher.exe','gfx.pak','steam_appid.txt']:continue
            if name=='gfx.pak' and digest==original:continue
            legacy[(name,digest)]={'path':name,'sha256':digest}
    config={'exe':'eschalon_book_1.exe','exe_sha256':'8f25c5ff8fc869e3c3b02c9e6f960c6a082cfcc097289a5247f237656c3031a8',
            'steam_app_id':'25600','originals':[{'path':'gfx.pak','sha256':original}],
            'legacy':list(legacy.values())}
    write(ROOT/'Release/installer_v17.json',config)
    write(ROOT/'Release/release_config.json',{
        'game_name':'Eschalon Book I','version':'1.7','download_url':'https://github.com/zfyu222/eschalon-book-i-hanhua/releases/',
        'mirror_url':'https://pan.baidu.com/s/5CzGvEaOYAUHbh8iBc-Jsww','share_name':'EschalonBook',
        'feedback_url':'https://docs.qq.com/sheet/DTnhoaFZweVRoV2t0?tab=BB08J2','feedback_name':'EschalonBook问题反馈'})
    report_dir=ROOT/'TranslateFiles/reports/release_v17'
    report_dir.mkdir(exist_ok=False)
    old=ROOT/'TranslateFiles/reports/in_game_check.json'
    shutil.copy2(old,report_dir/'previous_in_game_check_v16.json')
    equivalence={'status':'passed','frozen_module_matches_tested_source':True,'compared':'recursive code/constant/name objects; filenames excluded',
                 'launcher_sha256':sha(candidate),'source_hook_sha256':sha(ROOT/'display_hook_launcher.py'),
                 'frozen_resources_match_tested_project_files':resource_hashes,
                 'in_game_evidence':'Full fixed source module: level-up Next and Light Armor help; frozen launcher startup separately recorded.',
                 'unchanged_payload':['gfx.pak','steam_appid.txt']}
    write(report_dir/'frozen_components.json',equivalence)
    print(json.dumps({'payload':str(payload),'proof':str(report_dir/'frozen_components.json'),'legacy_hashes':len(legacy)},ensure_ascii=False))

if __name__=='__main__':main()
