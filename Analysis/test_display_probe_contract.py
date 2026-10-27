"""Run generated production callbacks against a bounded mock of BlitzMax strings."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import display_hook_launcher as launcher

SOURCE='The *Shield Skill deals with the effective use of hand-held shields in combative situations.'
TARGET='*盾牌技能涉及在战斗中有效使用手持盾牌。'
NARRATIVE='You open your eyes. Your head is aching.'
NARRATIVE_TARGET='你睁开双眼，头痛欲裂。'
SCRIPT=launcher.build_hook_script({SOURCE:TARGET,NARRATIVE:NARRATIVE_TARGET})
HARNESS=r"""
const vm=require('vm'),assert=require('assert');
const script=__SCRIPT__;
function create(corrupt=false){
  const words=new Map(),strings=new Map(),slots=new Map(),callbacks=new Map(),events=[];
  let next=0x700000;
  class Pointer{
    constructor(address){this.address=Number(address);}
    add(n){return new Pointer(this.address+Number(n));}
    sub(n){return new Pointer(this.address-Number(n));}
    isNull(){return this.address===0;}
    toString(){return '0x'+this.address.toString(16);}
    readU32(){return words.get(this.address)||0;}
    writeU32(x){words.set(this.address,x>>>0);return this;}
    readPointer(){return slots.get(this.address)||new Pointer(0);}
    writePointer(p){slots.set(this.address,p);return this;}
    readUtf16String(){return strings.get(this.address)||'';}
    writeUtf16String(s){strings.set(this.address,s);return this;}
    readByteArray(){
      const bytes=this.address===0x4d950f?[0xc7,0x45,0xe8,1,0,0,0]:[0x83,0xf8,0];
      if(corrupt&&this.address===0x4d950f)bytes[0]=0x90;
      return new Uint8Array(bytes).buffer;
    }
  }
  const context={
    ptr:x=>new Pointer(x),send:x=>events.push(x),
    Process:{mainModule:{base:new Pointer(0x400000)}},
    Memory:{alloc(){const p=new Pointer(next);next+=4096;return p;}},
    Interceptor:{attach(p,cb){callbacks.set(p.address,cb);return {};}}
  };
  vm.createContext(context);
  function string(text){
    const p=new Pointer(next);next+=4096;
    p.writePointer(new Pointer(0x4f1cb0));p.add(4).writeU32(1);
    p.add(8).writeU32(text.length);p.add(12).writeUtf16String(text);return p;
  }
  return {context,callbacks,events,Pointer,string,load:()=>vm.runInContext(script,context),
    text:p=>p.add(12).readUtf16String()};
}
const state=create();state.load();
assert.equal(typeof state.callbacks.get(0x4d950f),'function');
assert.equal(typeof state.callbacks.get(0x4c6c53),'function');
for(const address of [0x477b47,0x4bdeb8,0x4c4982]){
  assert.equal(typeof state.callbacks.get(address).onEnter,'function');
}
function exercise(address,offset,source,target){
  const ebp=new state.Pointer(0x900000),slot=ebp.sub(offset),original=state.string(source);
  slot.writePointer(original);
  state.callbacks.get(address).call({context:{ebp}});
  const result=slot.readPointer(),text=state.text(result);
  assert.equal(text.replace(/\s/g,''),target.replace(/\s/g,''));
  assert.equal(result.add(8).readU32(),text.length);
  assert.equal(result.readPointer().address,0x4f1cb0);
  return {address:'0x'+address.toString(16),source,target:text};
}
const translations=[exercise(0x4d950f,0x4c,__SOURCE__,__TARGET__),
                    exercise(0x4c6c53,0x24,__NARRATIVE__,__NARRATIVE_TARGET__)];
const ebp=new state.Pointer(0x900000),slot=ebp.sub(0x4c),empty=state.string('');
slot.writePointer(empty);state.callbacks.get(0x4d950f).call({context:{ebp}});
assert.equal(slot.readPointer().address,empty.address);
const invalid=create(true);let rejected=false;
try{invalid.load();}catch(e){rejected=String(e).includes('Unsupported code at instruction probe');}
assert.equal(rejected,true);
assert.equal(invalid.callbacks.has(0x4d950f),false);
assert.equal(state.events.some(e=>e.kind==='hook_error'),false);
console.log(JSON.stringify({status:'passed',tests:6,skill_translation:translations[0],
 narrative_translation:translations[1],empty_string_unchanged:true,
 incorrect_instruction_bytes_rejected:true,function_entries_remain_listeners:true}));
"""

for key,value in [('SCRIPT',SCRIPT),('SOURCE',SOURCE),('TARGET',TARGET),
                  ('NARRATIVE',NARRATIVE),('NARRATIVE_TARGET',NARRATIVE_TARGET)]:
    HARNESS=HARNESS.replace('__'+key+'__',json.dumps(value,ensure_ascii=False))
result=subprocess.run(['node'],input=HARNESS,text=True,encoding='utf-8',capture_output=True)
if result.returncode:raise RuntimeError(result.stderr)
print(result.stdout)
out=ROOT/'Analysis/display_probe_contract_20261028.json'
out.write_text(result.stdout,encoding='utf-8')
