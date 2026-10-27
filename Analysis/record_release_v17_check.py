"""Bind existing gameplay evidence plus frozen-component/smoke proof to v1.7."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'TranslateFiles/reports/release_v17'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(source,name):
    target=folder/name;shutil.copy2(ROOT/source,target)
    return {'path':target.relative_to(ROOT).as_posix(),'sha256':sha(target)}
report=json.loads((folder/'previous_in_game_check_v16.json').read_text(encoding='utf-8'))
report.pop('status',None);report.pop('quality_report_hash',None)
report['payload_files']=[{'path':'Release/v17/'+name,'game_path':name,'sha256':sha(ROOT/'Release/v17'/name)}
    for name in ['EschalonBook_Chinese_Launcher.exe','steam_appid.txt','gfx.pak']]
new_evidence=[
    copy('Analysis/levelup_crash/20261028_010102_068435/user_skill_description.png','skill_help.png'),
    copy('Analysis/levelup_crash/20261028_010102_068435/user_spell_description.png','spell_help.png'),
    copy('Analysis/levelup_crash/frozen_smoke_v17/verified_report.json','frozen_smoke.json'),
    copy('Analysis/levelup_fix_build.json','fix_validation.json')]
proof=folder/'frozen_components.json'
new_evidence.append({'path':proof.relative_to(ROOT).as_posix(),'sha256':sha(proof)})
report['evidence_files']+=new_evidence
for check in report['checks']:
    if check['category']=='ui':
        check['scene']+='；升级加点下一步、冻结启动器启动界面'
        check['notes']+=' 本次修复模块的升级下一步与技能中文场景通过；冻结启动器到达 Launch Menu 且两个修复探针已挂载。冻结代码递归字节码/常量及全部内嵌译表、字体与实测工程相同；冻结版本身未重复操作完整升级流程，未把启动冒烟等同于全场景验证。'
    elif check['category']=='fonts':
        check['scene']+='；升级页轻甲技能介绍'
        check['notes']+=' 新证据确认轻甲技能长说明中文、蓝色技能名、红色提示与15%数字保留；本版不修改字体文件。'
    elif check['category']=='layout':
        check['notes']+=' 中文贴图与v1.6逐字节相同，沿用既有证据，本版不重排贴图。'
(folder/'in_game_check_input.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(folder/'in_game_check_input.json')
