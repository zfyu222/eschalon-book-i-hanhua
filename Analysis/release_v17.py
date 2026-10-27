"""Build the v1.7 release with shared installer and approved per-game links."""
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
tool=ROOT.parents[1]/'.agents/skills/game-release-patch/scripts/create_release_patch.py'
config=json.loads((ROOT/'Release/release_config.json').read_text(encoding='utf-8'))
args=[sys.executable,str(tool),'--project',str(ROOT),'--game-name',config['game_name'],'--version',config['version'],
      '--release-date','2026-10-28','--game-version','Steam 1.05（eschalon_book_1.exe，32 位）','--platform','Steam（Windows）',
      '--introduction','《Eschalon: Book I》简体中文汉化补丁。',
      '--coverage','剧情、对话、物品、任务、技能说明及界面文字，包含39张中文界面贴图。',
      '--install','解压到 eschalon_book_1.exe 所在文件夹，双击“安装汉化.cmd”，完成后双击 EschalonBook_Chinese_Launcher.exe 启动游戏。',
      '--upgrade','覆盖解压到游戏目录，再运行“安装汉化.cmd”。',
      '--uninstall','运行“卸载汉化.cmd”。',
      '--changes','修复升级加点后点击“下一步”崩溃的问题，保留技能说明中文；增加自动安装与卸载脚本。',
      '--installer-config',str(ROOT/'Release/installer_v17.json')]
for key in ['download_url','mirror_url','share_name','feedback_url','feedback_name']:
    args+=['--'+key.replace('_','-'),config[key]]
for name in ['EschalonBook_Chinese_Launcher.exe','steam_appid.txt','gfx.pak']:
    args+=['--include',f'Release/v17/{name}={name}']
dry='--dry-run' in sys.argv
if dry:args.append('--dry-run')
result=subprocess.run(args,cwd=ROOT)
if result.returncode or dry:raise SystemExit(result.returncode)
output=ROOT/'Dispatch'/f"{config['game_name']}_子非鱼汉化{config['version']}.zip"
stage=ROOT/'Dispatch/Files'
# Keep the complete selected layout in Files, including generated metadata,
# then produce the final ZIP solely from that reviewed staging directory.
with zipfile.ZipFile(output) as z:
    for name in ['补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt']:
        (stage/name).write_bytes(z.read(name))
manifest=json.loads((stage/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
expected={x.get('archive_path',x['path']) for x in manifest['files']+manifest['auxiliary']}
expected.update(['补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt'])
actual={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
assert actual==expected,('Unexpected staging files',actual-expected,expected-actual)
building=output.with_suffix('.building.zip')
if building.exists():raise FileExistsError(building)
with zipfile.ZipFile(building,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for name in sorted(expected):z.write(stage/name,name)
building.replace(output)
print('Final ZIP built exclusively from Dispatch/Files:',output)
