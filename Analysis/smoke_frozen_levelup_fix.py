"""Smoke-test the owned frozen launcher, without loading or saving a character."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
exe=ROOT/'Release/levelup_fix/EschalonBook_Chinese_Launcher.exe'
out=ROOT/'Analysis/levelup_crash/frozen_smoke_v17'
out.mkdir(parents=True,exist_ok=False)
env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1',ESCHALON_WINDOWED='1',
         ESCHALON_RUNTIME=str(ROOT/'Eschalon_CN'))
started=dt.datetime.now().astimezone().isoformat()
owned=subprocess.Popen([str(exe)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                       creationflags=subprocess.CREATE_NO_WINDOW)
events=queue.Queue();lines=[];game_pid=None;ready=False;error=None;title=''
def reader():
    for raw in iter(owned.stdout.readline,b''):
        events.put(raw.decode('utf-8',errors='replace'))
    events.put(None)
threading.Thread(target=reader,daemon=True).start()
try:
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        try:line=events.get(timeout=1)
        except queue.Empty:continue
        if line is None:break
        lines.append(line)
        match=re.search(r'Game PID:\s*(\d+)',line)
        if match:game_pid=int(match.group(1))
        if 'Display hook error:' in line or 'Traceback' in line:error=line
        if 'Chinese runtime started.' in line:
            ready=True
            time.sleep(3)
            title=subprocess.run(['powershell.exe','-NoProfile','-Command',
                  f'(Get-Process -Id {game_pid}).MainWindowTitle'],capture_output=True,text=True).stdout.strip()
            break
    if not ready or error:raise RuntimeError('Frozen startup did not reach a clean ready state')
finally:
    # Only the exact PID reported by this owned launcher can be stopped. Check
    # its path and ancestry first; never stop the player's existing game PID.
    cleanup='not_started'
    if game_pid:
        command=(f'$g=Get-CimInstance Win32_Process -Filter "ProcessId={game_pid}"; '
                 f'$p=Get-CimInstance Win32_Process -Filter "ProcessId=$($g.ParentProcessId)"; '
                 f'if($g -and $g.ExecutablePath -eq "{ROOT / "Eschalon_CN/eschalon_book_1.exe"}" '
                 f'-and ($g.ParentProcessId -eq {owned.pid} -or $p.ParentProcessId -eq {owned.pid})) '
                 f'{{Stop-Process -Id {game_pid};"owned_smoke_game_stopped"}} else {{"not_owned_not_stopped"}}')
        cleanup=subprocess.run(['powershell.exe','-NoProfile','-Command',command],capture_output=True,text=True).stdout.strip()
    try:owned.wait(timeout=15)
    except subprocess.TimeoutExpired:
        owned.terminate();owned.wait(timeout=10)
    (out/'stdout.log').write_text(''.join(lines),encoding='utf-8')
    report={'started':started,'launcher':str(exe.relative_to(ROOT)),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
      'launcher_pid':owned.pid,'game_pid':game_pid,'ready':ready,'error':error,'window_title':title,
      'cleanup':cleanup,'character_loaded':False,'gameplay_test':'No gameplay input. Level-up/skill-help evidence is from the identical fixed module tested earlier.',
      'status':'passed' if ready and not error else 'failed'}
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
