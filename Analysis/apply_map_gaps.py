"""Append map-file and UTF-16 display text that never reached the corpus.

Every entry here was confirmed absent from the corpus by audit_uncovered.py and
extract_map_text.py. Script chains, asset names and engine debug output are
deliberately excluded; only text the player can read is added.
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "eschalonbook_text.csv"
TRANSLATED = ROOT / "eschalonbook_text_translated.csv"

PAIRS = {
    # Setting value next to the already-translated 32-bit entry.
    "16-bit (Thousands of colors)": "16位（数千色）",

    # Map interaction prose.
    "A corpse rises from the coffin!": "一具尸体从棺材里爬了起来！",
    "A gate moves...": "某处传来闸门移动的声音……",
    "A gate opens...": "一道闸门开启了……",
    "A passkey in your possession fits in the lever's slot allowing you to unlock it.":
        "你身上的一把钥匙正好插入拉杆的槽中，解开了锁。",
    "A skeleton rises from the coffin!": "一具骷髅从棺材里爬了起来！",
    "A spirit rises from the coffin!": "一个幽灵从棺材里升了起来！",
    "Abygale: You are not allowed in there! Please leave!":
        "阿比盖尔：你不能进去！请离开！",
    "Agh! The Goblins have been using this well as a toilet!":
        "呃啊！哥布林一直把这口井当厕所用！",
    "Ah! Very refreshing!": "啊！真是清爽！",
    "Arachnid chamber: enter with caution! Please do not harm the specimens; take only the magickal components that you need for your studies.":
        "蛛形生物室：进入时请小心！请勿伤害这些标本，只取研究所需的魔法材料。",
    "As you near the rock wall, a section crumbles apart! It appears this was only a poorly made false wall.":
        "你靠近石墙时，一段墙体崩塌了！看来这只是一道做工粗糙的假墙。",
    "Edward - Loving father, helpful friend; neither helped him in the end.":
        "爱德华——慈爱的父亲，乐于助人的朋友；最终两者都没能救他。",
    "Far away you can hear the faint sound of a gate moving...":
        "远处隐约传来闸门移动的声音……",
    "Far off you hear the fainest sound of a gate moving...":
        "远方传来极其微弱的闸门移动声……",
    "It appears someone has been making wishes by throwing coins down the well!":
        "看来有人一直在往井里投硬币许愿！",
    "It appears someone has dug up a coffin and dragged it into this house. All that's left of the body inside is fragments of bone and clothing.":
        "看来有人挖出了一口棺材并把它拖进了这栋房子。里面的遗体只剩下骨片和衣物碎片。",
    "Lars; man about town, now under ground.":
        "拉尔斯；昔日城里的风云人物，如今长眠地下。",
    "Nothing happens...": "什么也没发生……",
    "Rachel - Beauty now bones; hollow and alone.":
        "瑞秋——昔日美人，如今只剩白骨；空寂而孤独。",
    "Secret wall!": "暗墙！",
    "Stop the clocks from ticking; make the sun disappear; happiness for me is ending; because you're gone my dear.":
        "让时钟停摆；让太阳消失；我的幸福即将终结；因为你已离去，亲爱的。",
    "Suddenly you hear a war horn and four giants charge into the battle!":
        "突然传来号角声，四个巨人冲入了战斗！",
    "The Gate Key in your inventory fits the keyhole. Upon inserting it, the gate crashes downward into the ground!":
        "你背包里的城门钥匙正好插入锁孔。插入后，闸门轰然坠入地下！",
    "The barrel was full of Fungal Slime, and a small pouch of gold!":
        "桶里装满了真菌黏液，还有一小袋金币！",
    "The blast knocks out the northwest wall to this room!":
        "爆炸炸塌了这个房间的西北墙！",
    "The blast opens a pathway through the rocks!":
        "爆炸在岩石间炸出了一条通路！",
    "The casket was filled with Fanged Salamanders, gnawing away at what was left of the bones!":
        "棺材里满是尖牙火蜥，正在啃食残余的尸骨！",
    "The door opens into a tiny closet containing a chest.":
        "门后是一间小储藏室，里面有一个箱子。",
    "The gate rises and the lever becomes locked in place.":
        "闸门升起，拉杆随之锁死。",
    "The ground gives way and you fall into darkness!":
        "地面塌陷，你坠入了黑暗！",
    "The portcullis behind you opens...": "你身后的铁闸门打开了……",
    "The pressure plate triggers the portculis!": "压力板触发了铁闸门！",
    "The sound of steel grinding on stone can be heard far off in the darkness.":
        "黑暗中远处传来钢铁摩擦石面的声响。",
    "The wall on the northeast side of the room moves!":
        "房间东北侧的墙体移动了！",
    "The water has a oily film floating on it. You decide to not drink it.":
        "水面浮着一层油膜，你决定不喝。",
    "The water smells putrid.": "水散发着腐臭味。",
    "The water tastes exceptionally fresh here!": "这里的水格外清冽！",
    "There is something sticking out of the cracks in a nearby rock!":
        "附近岩石的裂缝里有什么东西露了出来！",
    'This door seems to be as solid as the brick walls surrounding it; in fact, upon closer inspection, the door appears to have been painted upon the wall! There is no visible keyhole, though it appears this "door" may move under some other mechanical force.':
        "这扇门看起来和周围的砖墙一样坚固；事实上，仔细一看，门是画在墙上的！看不到锁孔，但这扇「门」似乎会因某种机械力量而移动。",
    "This storage room is filled with rusted shovels and picks hanging on the walls.":
        "这间储藏室的墙上挂满了生锈的铲子和镐。",
    "This switch feels broken. It just moves loosely back and forth.":
        "这个开关像是坏了，只是松松垮垮地来回晃动。",
    "This switch is jammed and will not budge.":
        "这个开关卡住了，纹丝不动。",
    "This switch offers no resistance as if it is broken and no longer attached to any mechanism.":
        "这个开关毫无阻力，像是已经损坏，不再连接任何机关。",
    "To prevent injury, the massive gate has been locked in place. A key or separate switch is needed to release it.":
        "为防止伤人，巨大的闸门已被锁死。需要钥匙或另一个开关才能释放它。",
    "Triggering the switch causes the gate to slide down into the walkway.":
        "扳动开关后，闸门滑落至通道中。",
    "Upon stepping on this pressure plate, a section of wall to the southwest opens up!":
        "踩上这块压力板后，西南侧的一段墙壁打开了！",
    "Very odd...this well is completely dry. The bucket is filled with dry leaves.":
        "真奇怪……这口井完全干涸了，水桶里装满了枯叶。",
    "When you examine the rocks, several crash to the floor.":
        "你查看岩石时，几块石头轰然落地。",
    "You hear the faint sound of a gate moving somewhere...":
        "你听到某处隐约传来闸门移动的声音……",
    "You hear the faint sound of a steel gate moving...":
        "你听到隐约的铁闸门移动声……",
    "You notice a leather pouch stuffed into the shelves of bones!":
        "你发现骨架上塞着一个皮袋！",
    "You notice something nearby on the wall. It appears to be a hidden area behind a brick!":
        "你注意到墙上附近有什么东西。砖块后面似乎有个隐藏空间！",
    "You notice something stuffed into the shelves of bones!":
        "你发现骨架里塞着什么东西！",
    "You only find a moldy bucket filled with smelly water.":
        "你只找到一个发霉的水桶，里面装满了臭水。",
    "You take a drink of the refreshing water.": "你喝了一口清冽的水。",
    "You've been ambushed!": "你遭到了伏击！",
    "You've disturbed a nest of Bloodsippers!": "你惊扰了一窝吸血虫！",
    "an old grave marker; the name is barely legible.":
        "一块古老的墓碑；上面的名字几乎无法辨认。",

    # Prompt shown by the well script before the Yes/No branch.
    "There is a rope going down the well. Pull it up?":
        "井里垂着一根绳子。要拉上来吗？",

    # Short dialogue option that existed only as a raw ASCII run.
    "I can do this.": "我能做到。",
}


def load(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return [row[0] if row else "" for row in csv.reader(stream)]


def write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\r\n")
        for value in rows:
            writer.writerow([value])


def main():
    sources = load(SOURCE)
    targets = load(TRANSLATED)
    if len(sources) != len(targets):
        print(f"row mismatch: {len(sources)} vs {len(targets)}")
        return 2

    existing = set(sources)
    added = 0
    for source, target in PAIRS.items():
        if source in existing:
            print(f"skip existing: {source[:60]!r}")
            continue
        sources.append(source)
        targets.append(target)
        existing.add(source)
        added += 1

    write(SOURCE, sources)
    write(TRANSLATED, targets)
    print(f"appended {added}, total {len(sources)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
