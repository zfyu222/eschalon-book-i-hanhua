"""Verify the owned frozen smoke process when its console pipe is buffered."""
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import os
import signal
import frida

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'Analysis/levelup_crash/frozen_smoke_v17'
prior=json.loads((folder/'report.json').read_text(encoding='utf-8'))
game_pid=4200
command=f'''$g=Get-CimInstance Win32_Process -Filter "ProcessId={game_pid}";
$p=Get-CimInstance Win32_Process -Filter "ProcessId=$($g.ParentProcessId)";
$w=Get-Process -Id {game_pid};
@{{game=$g|Select-Object ProcessId,ParentProcessId,ExecutablePath;parent=$p|Select-Object ProcessId,ParentProcessId,ExecutablePath;title=$w.MainWindowTitle;responding=$w.Responding}}|ConvertTo-Json -Depth 4'''
observed=json.loads(subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True,check=True).stdout)
assert observed['parent']['ParentProcessId']==prior['launcher_pid']
assert Path(observed['parent']['ExecutablePath']).resolve()==(ROOT/prior['launcher']).resolve()
assert Path(observed['game']['ExecutablePath']).resolve()==(ROOT/'Eschalon_CN/eschalon_book_1.exe').resolve()
assert observed['responding'] and observed['title']=='Launch Menu'
session=frida.attach(game_pid)
event=threading.Event();messages=[]
try:
    script=session.create_script("""send({pid:Process.id,architecture:Process.arch,
      skill:Array.from(new Uint8Array(ptr('0x4d950f').readByteArray(7))),
      narrative:Array.from(new Uint8Array(ptr('0x4c6c53').readByteArray(3)))});""")
    script.on('message',lambda m,d:(messages.append(m),event.set()))
    script.load();assert event.wait(5)
    data=messages[0]['payload']
    assert data['architecture']=='ia32' and data['skill'][0]==0xe9 and data['narrative'][0]==0xe9
finally:session.detach()
report={'status':'passed','launcher':prior['launcher'],'sha256':prior['sha256'],
        'observed':observed,'live_instruction_probes':data,
        'initial_pipe_capture':'Buffered console produced no lines; initial readiness timeout preserved in report.json, not treated as game failure.',
        'character_loaded':False,'gameplay_input':False,
        'gameplay_evidence':'Identical fixed module and resources were tested in the existing level-up/skill-help run; component equivalence separately checked.'}
(folder/'verified_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Exact owned child/parent only, after path and recorded bootloader ancestry checks.
os.kill(game_pid,signal.SIGTERM)
os.kill(observed['parent']['ProcessId'],signal.SIGTERM)
print(json.dumps(report,ensure_ascii=False))
