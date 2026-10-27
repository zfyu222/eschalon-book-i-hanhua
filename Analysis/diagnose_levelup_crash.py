"""Diagnostic-only launcher: record native faults without changing game/saves."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OBSERVER = r"""
(() => {
  const recent=[];
  const emit=event=>send({kind:'crash_diagnostic',event:{...event,time:new Date().toISOString()}});
  function trace(context) {
    try {return Thread.backtrace(context,Backtracer.ACCURATE).slice(0,20).map(String);}
    catch(error){return ['unavailable: '+error];}
  }
  let exceptionCount=0;
  Process.setExceptionHandler(details=>{
    try {
      const registers={};
      for(const name of ['eip','esp','ebp','eax','ebx','ecx','edx','esi','edi'])
        if(details.context[name]!==undefined)registers[name]=String(details.context[name]);
      let instruction=null;
      try{instruction=Instruction.parse(details.address).toString();}catch(_){}
      if(++exceptionCount<=32)emit({type:'native_exception',exception:details.type,
        address:String(details.address),registers,instruction,number:exceptionCount,
        memory:details.memory?{operation:details.memory.operation,address:String(details.memory.address)}:null,
        stack:trace(details.context),recent:recent.slice()});
    }catch(_){}
    return false; // Observe only; never suppress the game's exception.
  });
  Interceptor.attach(ptr('0x4D950F'),{onEnter(){
    try{
      const event={type:'skill_paragraph',ebp:String(this.context.ebp),returnAddress:String(this.returnAddress)};
      try{
        const value=this.context.ebp.sub(0x4c).readPointer(),length=value.add(8).readU32();
        event.pointer=String(value);event.length=length;event.refs=value.add(4).readU32();
        event.stringType=String(value.readPointer());
        const range=Process.findRangeByAddress(value);
        event.range=range?{base:String(range.base),size:range.size,protection:range.protection}:null;
        if(length<=65535)event.text=value.add(12).readUtf16String(Math.min(length,240));
      }catch(error){event.readError=String(error);}
      // Keep a bounded in-memory ring: this hook may run every UI frame.
      recent.push(event);if(recent.length>24)recent.shift();
    }catch(_){}
  }});
  for(const name of ['ExitProcess','TerminateProcess']){
    try{
      const address=Process.getModuleByName('kernel32.dll').getExportByName(name);
      Interceptor.attach(address,{onEnter(args){
        emit({type:'native_exit',api:name,code:args[name==='ExitProcess'?0:1].toUInt32(),
          stack:trace(this.context),recent:recent.slice()});
      }});
    }catch(error){emit({type:'observer_warning',api:name,error:String(error)});}
  }
  emit({type:'observer_ready',mainModule:{name:Process.mainModule.name,path:Process.mainModule.path,base:String(Process.mainModule.base)}});
})();
"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Check without launching.')
    args=parser.parse_args()
    os.environ['ESCHALON_WINDOWED']='1'  # Keep the existing preference, do not force fullscreen.
    import frida
    import display_hook_launcher as launcher
    if args.check:
        import subprocess
        script=launcher.build_hook_script({})+'\n'+OBSERVER
        check=subprocess.run(['node','--check'],input=script,text=True,capture_output=True)
        if check.returncode:raise RuntimeError(check.stderr)
        print(json.dumps({'frida':frida.__version__,'runtime':str(launcher.core.EXE),
                          'javascript_syntax':'passed','launched':False}))
        return 0
    folder=ROOT/'Analysis/levelup_crash'/dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    folder.mkdir(parents=True)
    lock=threading.Lock()
    def record(value):
        value={'time':dt.datetime.now().astimezone().isoformat(),**value}
        with lock,(folder/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value,ensure_ascii=False,default=str)+'\n')
            stream.flush()
    old_hashes={}
    for attr in ['UNTRANSLATED_LOG','CALLSTACK_LOG','PARAGRAPH_LOG','NARRATIVE_CALL_LOG']:
        old=getattr(launcher,attr)
        if old.exists():
            copy=folder/('previous_'+old.name)
            shutil.copy2(old,copy)
            old_hashes[old.name]=hashlib.sha256(copy.read_bytes()).hexdigest()
        setattr(launcher,attr,folder/old.name)
    record({'type':'diagnostic_start','previous_log_sha256':old_hashes,'runtime':str(launcher.core.EXE),
            'source_hook_sha256':hashlib.sha256(Path(launcher.__file__).read_bytes()).hexdigest()})
    builder=launcher.build_hook_script
    launcher.build_hook_script=lambda mapping:builder(mapping)+'\n'+OBSERVER
    original_message=launcher.on_message
    def on_message(message,data):
        if message.get('type')=='error':record({'type':'frida_script_error','message':message})
        elif message.get('payload',{}).get('kind')=='crash_diagnostic':
            event=message['payload']['event'];record(event)
            if event.get('type') in ('native_exception','native_exit'):
                print('Diagnostic event:',event.get('type'),event.get('address',event.get('api')),flush=True)
            return
        original_message(message,data)
    launcher.on_message=on_message
    original_attach=frida.attach
    def attach(*a,**kw):
        session=original_attach(*a,**kw)
        def detached(reason,crash=None):
            event={'type':'session_detached','reason':str(reason)}
            if crash:
                event['crash']={k:getattr(crash,k,None) for k in ('pid','process_name','summary','report','parameters')}
                report=getattr(crash,'report',None)
                if report:(folder/'native_crash.txt').write_text(report,encoding='utf-8')
            record(event)
        session.on('detached',detached)
        return session
    frida.attach=attach
    core=launcher.core
    core.k32.GetExitCodeProcess.argtypes=[core.wintypes.HANDLE,core.ctypes.POINTER(core.wintypes.DWORD)]
    core.k32.GetExitCodeProcess.restype=core.wintypes.BOOL
    original_wait=core.k32.WaitForSingleObject
    def wait(handle,timeout):
        result=original_wait(handle,timeout);code=core.wintypes.DWORD()
        if core.k32.GetExitCodeProcess(handle,core.ctypes.byref(code)):
            record({'type':'process_wait_finished','wait_result':result,'exit_code':code.value,'exit_hex':f'0x{code.value:08x}'})
        return result
    core.k32.WaitForSingleObject=wait
    print('诊断目录：',folder,flush=True)
    print('请载入升级前的存档，按原来的步骤加点并点击下一步。诊断器不会替你保存。',flush=True)
    try:return launcher.main()
    except Exception as exc:
        record({'type':'launcher_exception','error':repr(exc)})
        raise
    finally:
        record({'type':'diagnostic_end'})
        print('诊断记录已保存：',folder,flush=True)


if __name__=='__main__':
    raise SystemExit(main())
