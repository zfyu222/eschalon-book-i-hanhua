"""Replay actual CMD entrypoints in a Unicode game path containing spaces."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='eschalon-v17-cmd-') as temp:
    base=Path(temp).resolve()
    assert base.parent==Path(tempfile.gettempdir()).resolve() and base.name.startswith('eschalon-v17-cmd-')
    game=base/'游戏目录 with spaces';game.mkdir()
    with zipfile.ZipFile(ROOT/'Dispatch/Eschalon Book I_子非鱼汉化1.7.zip') as z:z.extractall(game)
    shutil.copy2(ROOT/'Eschalon_CN/eschalon_book_1.exe',game/'eschalon_book_1.exe')
    shutil.copy2(ROOT/'Game/gfx.pak',game/'gfx.pak')
    original=sha(game/'gfx.pak')
    for action in ['安装汉化.cmd','卸载汉化.cmd']:
        result=subprocess.run([os.environ['COMSPEC'],'/d','/c',action],cwd=game,input=b'\r\n',capture_output=True,timeout=90)
        assert result.returncode==0,(action,result.stdout,result.stderr)
        if action.startswith('安装'):
            state=json.loads((game/'.zfy-localization/state.json').read_text(encoding='utf-8-sig'))
            assert state['status']=='installed'
            assert sha(game/'EschalonBook_Chinese_Launcher.exe')==sha(ROOT/'Release/v17/EschalonBook_Chinese_Launcher.exe')
        else:
            assert sha(game/'gfx.pak')==original
            assert not (game/'EschalonBook_Chinese_Launcher.exe').exists()
    report={'status':'passed','cmd_entrypoints':['安装汉化.cmd','卸载汉化.cmd'],
            'path_case':'Unicode plus spaces','installed_payload_hash':'matched',
            'original_restored':True,'real_game_modified':False}
out=ROOT/'TranslateFiles/reports/release_v17/cmd_entrypoints.json'
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
