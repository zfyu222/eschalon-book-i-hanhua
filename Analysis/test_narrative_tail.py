"""Regression for paragraph-word loss, using production JS and archived REA logic.

Native model: rea_dec_narrative.c / FUN_004c69ad. Space commits pending
word; '*' clears pending word and advances two lines; EOF commits pending.
This is an offline model, not a claim of game screenshot verification.
"""
import ast
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import display_hook_launcher as launcher

def rows(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as f:
        return [row[0] for row in csv.reader(f)]

sources = rows('eschalonbook_text.csv')
targets = rows('eschalonbook_text_translated.csv')
opening = next(i for i, s in enumerate(targets) if s.startswith('你睁开双眼。'))
# Reuse just the bounded BlitzMax-pointer mock, without executing/writing the
# older test's main section or rewriting its historical result.
tree = ast.parse((ROOT / 'Analysis/test_display_probe_contract.py').read_text(encoding='utf-8'))
mock = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'HARNESS' for t in n.targets))
mock = mock.split('const state=create();')[0].replace('__SCRIPT__', json.dumps(
    launcher.build_hook_script(dict(zip(sources, targets))), ensure_ascii=False))
checks = r'''
const state=create();state.load();
function clean(s){return s.replace(/\s/g,'');}
function render(s){
  let pending='',parts=[''];
  for(const ch of s){
    if(ch==='*'){parts.push('');pending='';}
    else {pending+=ch;if(ch===' '){parts[parts.length-1]+=pending;pending='';}}
  }
  parts[parts.length-1]+=pending;
  return parts.map(clean);
}
const opening=__OPENING__;
const legacy=vm.runInContext('makeChineseBreakable('+JSON.stringify(opening)+')',state.context);
const before=render(legacy),expected=opening.split('*').map(clean);
assert(before[0].endsWith('闪电划'));
assert(before[1].endsWith('最私密的信'));
let count=0;
for(const text of __TARGETS__){
  const prepared=vm.runInContext('prepareNarrativeText('+JSON.stringify(text)+')',state.context);
  assert.deepEqual(render(prepared),text.split('*').map(clean));
  assert.equal((prepared.match(/\*/g)||[]).length,(text.match(/\*/g)||[]).length);
  count++;
}
const ebp=new state.Pointer(0x900000),slot=ebp.sub(0x24);
slot.writePointer(state.string(__SOURCE__));
state.callbacks.get(0x4c6c53).call({context:{ebp}});
const actual=state.text(slot.readPointer());
assert.deepEqual(render(actual),expected);
// Per-paragraph fallback must retain the native paragraph delimiter, not LF.
vm.runInContext('translations["Paragraph alpha."]="第一段。"; translations["Paragraph beta."]="第二段。";',state.context);
const fallback=vm.runInContext('lookupParagraph("Paragraph alpha.*Paragraph beta.")',state.context);
assert.equal(fallback,'第一段。*第二段。');
assert.equal(typeof state.callbacks.get(0x4d950f),'function');
assert.equal(typeof state.callbacks.get(0x4c6c53),'function');
assert(!state.events.some(e=>e.kind==='hook_error'));
console.log(JSON.stringify({status:'passed',corpus_rows:count,
 legacy_opening_paragraphs:before,corrected_opening_paragraphs:render(actual),
 production_narrative_callback:true,paragraph_fallback:true,instruction_probes_preserved:true}));
'''
for key, value in [('OPENING', targets[opening]), ('SOURCE', sources[opening]),
                   ('TARGETS', targets + ['甲*乙*丙', '甲 *乙 *', '*甲**乙*',
                                          '一二三四五六七八九十。*终。', 'English.*中文。'])]:
    checks = checks.replace('__' + key + '__', json.dumps(value, ensure_ascii=False))
result = subprocess.run(['node'], input=mock + checks, text=True, encoding='utf-8', capture_output=True)
if result.returncode:
    raise RuntimeError(result.stderr)
report = json.loads(result.stdout)
report['source_sha256'] = hashlib.sha256((ROOT / 'display_hook_launcher.py').read_bytes()).hexdigest()
report['native_evidence'] = 'Analysis/rea_dec_narrative.c'
report['in_game_check'] = 'pending'
out = ROOT / 'Analysis/narrative_tail_regression_20261101.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
