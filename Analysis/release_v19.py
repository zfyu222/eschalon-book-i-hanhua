"""Release narrative-tail fix with the tested v1.8 single-entry adapter."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parents[1]
REPORT=ROOT/'TranslateFiles/reports/release_v19'
REPORT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

stage=ROOT/'Dispatch/Files'
old_manifest=json.loads((stage/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
assert old_manifest['version']=='1.8'
assert all(sha(stage/e.get('archive_path',e['path']))==e['sha256'] for e in old_manifest['files']+old_manifest['auxiliary'])
payload=ROOT/'Release/v19'
payload.mkdir(exist_ok=True)
entries=[]
for e in old_manifest['files']+old_manifest['auxiliary']:
    name=e['path']; source=stage/e.get('archive_path',name)
    if name.endswith('/runtime/EschalonBook_Chinese_Launcher.exe'):
        source=ROOT/'Release/narrative_tail_fix/EschalonBook_Chinese_Launcher.exe'
    dest=payload/name;dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        assert sha(dest)==sha(source),'Existing candidate differs: '+name
    else:shutil.copy2(source,dest)
    entries.append((dest,name))
evidence=REPORT/'authorization.json'
write(evidence,{'user_statement':'好的，那再次发布游戏阿爸','context':'User again requests publication after the pending runtime validation and release gate were explained. Offline tests passed; runtime validation remains pending.',
                'in_game_validation':'pending','version':'1.9','date':'2026-11-01'})
sys.path.insert(0,str(WORKSPACE/'Tools/localization'))
from translation_workflow import Workflow
flow=Workflow(ROOT)
with flow.db() as db:
    export=flow.meta(db,'last_export');previous=flow.meta(db,'in_game_check')
write(REPORT/'previous_game_check.json',previous)
authorization={'translation_sha256':export['translation_sha256'],
 'authorization':'explicit_user_release','in_game_validation':'pending','accept_pending_runtime':True,
 'user_statement':'好的，那再次发布游戏阿爸','game_version':'Steam 1.05（eschalon_book_1.exe，32 位）','platform':'Steam（Windows）',
 'payload_files':[{'path':p.relative_to(ROOT).as_posix(),'game_path':n,'sha256':sha(p)} for p,n in entries],
 'evidence_files':[{'path':evidence.relative_to(ROOT).as_posix(),'sha256':sha(evidence)},
 {'path':'Analysis/narrative_tail_regression_20261101.json','sha256':sha(ROOT/'Analysis/narrative_tail_regression_20261101.json')}]}
flow.record_release_acceptance(authorization)
# The new export binds the refreshed quality report. Old in-game evidence is
# retained unchanged, not relabelled as having tested the new payload.
write(REPORT/'release_check.json',flow.release_check())

tool=WORKSPACE/'.agents/skills/game-release-patch/scripts/create_release_patch.py'
config=json.loads((ROOT/'Release/release_config.json').read_text(encoding='utf-8'))
args=[sys.executable,str(tool),'--project',str(ROOT),'--game-name','Eschalon Book I','--version','1.9',
 '--chinese-name','埃斯卡隆：卷一','--english-name','Eschalon: Book I','--release-date','2026-11-01',
 '--game-version',authorization['game_version'],'--platform',authorization['platform'],
 '--steam-url','https://store.steampowered.com/app/25600/',
 '--introduction','一款复古风格的单人奇幻角色扮演游戏，采用格子地图与回合制战斗。玩家自由分配属性和技能，搭配装备与法术，探索野外和地下城、寻找宝物并完成任务，在非线性冒险中揭开自己的身世。',
 '--coverage','剧情、对话、物品、任务、技能说明及界面文字，包含39张中文界面贴图。',
 '--install','解压到 eschalon_book_1.exe 所在文件夹，双击“埃斯卡隆：卷一_中文版.exe”，首次运行自动安装并启动，以后直接启动。',
 '--upgrade','覆盖解压新版补丁后，运行同一个“埃斯卡隆：卷一_中文版.exe”。',
 '--uninstall','运行“卸载汉化.cmd”。',
 '--changes','修复开场及同类叙事段落末尾缺字的问题，保留升级加点崩溃修复与安装游玩一体的中文版入口。']
for k in ['download_url','mirror_url','share_name','feedback_url','feedback_name']:
    args+=['--'+k.replace('_','-'),config[k]]
for p,n in entries:args+=['--include',str(p)+'='+n]
subprocess.run(args+['--dry-run'],check=True)
archive=ROOT/'Dispatch/StagingArchive/v18_narrative_tail'
assert not archive.exists()
assert stage.resolve()==ROOT/'Dispatch/Files' and archive.parent.resolve()==ROOT/'Dispatch/StagingArchive'
stage.rename(archive)
subprocess.run(args,check=True)
from finalize_release_v19 import main
main()
