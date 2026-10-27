"""Exercise Frida listener vs instruction-probe semantics in a disposable x86 host.

Never attaches to the game. All machine-code fixtures live in the owned helper's
private allocation; the fixture has an EDI save at its mid-function probe site.
"""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess

import frida

SCRIPT = r"""
rpc.exports.runProbe = function(mode) {
  if (Process.arch !== 'ia32') throw new Error('Expected x86 host, got '+Process.arch);
  const code=Memory.alloc(Process.pageSize);
  Memory.protect(code,Process.pageSize,'rwx');
  // outer: save EDI; set sentinel; call inner; return EDI; restore EDI; ret
  code.writeByteArray([0x57,0xbf,0x78,0x56,0x34,0x12,0xe8,0x15,0,0,0,0x89,0xf8,0x5f,0xc3]);
  // inner: save frame, reserve locals, save EDI, assign a local, restore EDI/frame
  code.add(32).writeByteArray([0x55,0x89,0xe5,0x83,0xec,0x10,0x57,
    0xc7,0x45,0xfc,1,0,0,0,0x5f,0x89,0xec,0x5d,0xc3]);
  let hits=0;
  if(mode==='listener') Interceptor.attach(code.add(39),{onEnter(){hits++;}});
  if(mode==='instruction') Interceptor.attach(code.add(39),function(){hits++;});
  Interceptor.flush();
  const run=new NativeFunction(code,'uint32',[]);
  const values=[];
  for(let i=0;i<10;i++)values.push(run());
  return {architecture:Process.arch,mode,hits,expected:0x12345678,values,
    preserved:values.every(x=>x===0x12345678)};
};
"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.exists():raise ValueError('Use a new evidence file')
    records=[]
    for mode in ('unhooked','instruction','listener'):
        # Keep stdin open so this private cmd host remains idle until cleanup.
        helper=subprocess.Popen([r'C:\Windows\SysWOW64\cmd.exe','/d','/q','/k'],
            stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        session=None
        try:
            session=frida.attach(helper.pid)
            script=session.create_script(SCRIPT)
            script.load()
            records.append(script.exports_sync.run_probe(mode))
        finally:
            if session:
                try:session.detach()
                except frida.InvalidOperationError:pass
            if helper.poll() is None:helper.terminate()
            helper.wait(timeout=10)
            if helper.stdin:helper.stdin.close()
    report={'date':dt.datetime.now().astimezone().isoformat(),'frida':frida.__version__,
            'game_started':False,'fixture':'x86 saved-EDI interior instruction','records':records}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    return 0 if records[0]['preserved'] and records[1]['preserved'] and not records[2]['preserved'] else 1


if __name__=='__main__':raise SystemExit(main())
