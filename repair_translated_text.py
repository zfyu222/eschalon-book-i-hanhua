"""Apply the reviewed, project-specific cleanup to Eschalon Book I's CSV.

This is intentionally a narrow one-off repair: every edited row is listed
explicitly and the script refuses to run if the source/translation row count
is not the expected 3048.
"""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
SOURCE = PROJECT / "eschalonbook_text.csv"
TRANSLATED = PROJECT / "eschalonbook_text_translated.csv"


REPLACEMENTS = {
    148: "墨水瓶与羽毛笔",
    410: "制作简易灵药和药剂指南，资深炼金术师乌鲁·暗霜 著。 *这本教程会给你四种最基础混合物的配方。即便是最菜鸟的炼金术师也能调配这些药剂——除了鹰眼药剂需要多几分技巧才能拿捏好比例。*至于治疗灵药和法力药水，你会发现，炼金术技能越高，调制出的药水就越强力。 *-------------- *治疗灵药：柳树汁液和硫磺 *法力药水：曼德拉草根和酸液 *猫眼血清：柳树汁液和溴 *鹰眼药剂：龙涎香和酸液",
    1041: "$左键单击可将点数加到技能上。$右键单击可收回本次操作中分配的技能点。",
    1045: "*轻型 *盔甲包括轻质防护装备，如软皮、硬皮和铆钉皮甲。你对盔甲的熟练度越高，受到物理攻击时承受的伤害就越少。在躯干、腿部或脚部穿着轻型盔甲#会#使#你#的#移动#噪音#增加#15%，影响你无声移动的能力。",
    1046: "*重型 *盔甲包括由金属合金制成的重型防护装备。你对盔甲的熟练度越高，受到物理攻击时承受的伤害就越少。在躯干、腿部或脚部穿着重型盔甲#会#使#你#的#移动#噪音#增加#30%，影响你潜行移动的能力。",
    1050: "*隐匿 *于 *阴影是利用阴影与黑暗掩盖移动的能力。它是始终生效的自动技能，若角色处于黑暗区域，则会赋予“潜藏阴影”效果。技能越高，角色发动此技能所需的黑暗就越少。此外，站在墙壁或大型物体旁会增强效果。&敏捷增强此技能。",
    1054: "*无声 *移动是一项潜行技能，让你移动时不发出声响以避免被察觉。此技能越高，就越能抵消#惩罚#施加#由#穿戴#护甲，并且你可以在被敌人察觉前更接近他们。当没有敌人能听到你移动时，效果窗口会显示“无声”。&敏捷增强此技能。",
    1055: "*撬锁 *技能让你能使用开锁工具解开房门与箱子的锁。&智力与&敏捷增强此技能。",
    1057: "*察觉 *隐藏技能让你能被动发现隐藏物品、门、陷阱与异常之处。此技能由&感知属性增强。",
    1059: "*徒手 *战斗技能让你仅用拳脚攻击目标，造成不亚于手持钝器的伤害。&力量与&速度是增强此*徒手 *战斗技能的属性。",
    1060: "*钝击 *武器包括法杖、钉头锤、战锤、棍棒等钝力武器。它们既能砸碎宝箱，也能敲碎头骨。钝击武器属于近战武器，由&力量与&速度增强。",
    1061: "*弓 *武器包括各类使用箭矢的射击装置。&专注与&敏捷是增强弓术技能的属性。",
    1063: "*短 *刃 *武器包括匕首、短剑及类似刺击或切割器械。短剑因体积更大、重量更重，被归为剑类而非短刃武器。短刃武器被视为近战武器，因此受到&力量与&速度的加成。",
    1627: "^磅于施法时发出。请从&主&武器、&盾牌或&手套槽中移除物品，然后再次尝试施法。||注意：此限制仅在 NPC 或生物附近时生效。",
    2351: "因为你在将技能点投入到职业赋予技能^之后更改了角色职业，导致可用技能点透支。在继续之前，你必须^返还^技能，使可用技能点变为0。",
    2358: "你还有^技能^点未分配。按&返回回到角色编辑器，或按&保存&它们，将点数留到角色下次升级。",
    2359: "你还有^属性^点未分配。按&返回回到角色编辑器，或按&保存&它们，将点数留到角色下次升级。",
}


def read_csv(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


source_rows = read_csv(SOURCE)
translated_rows = read_csv(TRANSLATED)
if len(source_rows) != 3048 or len(translated_rows) != len(source_rows):
    raise RuntimeError(
        f"Unexpected row count: source={len(source_rows)}, translated={len(translated_rows)}"
    )

# The source uses literal backslash-n; the translated CSV currently contains
# physical newlines inside this one field.
row_826 = 826 - 1
if "\\n\\n" not in source_rows[row_826] or "\n\n" not in translated_rows[row_826]:
    raise RuntimeError("Row 826 no longer matches the reviewed newline condition")
translated_rows[row_826] = translated_rows[row_826].replace("\n", "\\n")

for row_number, replacement in REPLACEMENTS.items():
    translated_rows[row_number - 1] = replacement

with TRANSLATED.open("w", encoding="utf-8-sig", newline="") as stream:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerows([[text] for text in translated_rows])

print(f"Repaired {len(REPLACEMENTS) + 1} reviewed rows.")
