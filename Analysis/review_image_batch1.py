"""Record conversation-agent visual decisions for the first evidence package."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
records = []
def decide(i, regions=None, reason=None):
    records.append({'id': str(i), 'status': 'text' if regions else 'no_text',
                    'reason': reason or ('逐项查看清晰证据图，确认标签文字。' if regions else '已查看图像，仅有角色/场景/图标像素，无可辨认文字。'),
                    'unreadable': False, 'regions': regions or []})
def region(text, box):
    return {'text': text, 'box': box}

menu = ['Begin a New Adventure', 'Restore a Saved Adventure', 'Credits', 'Exit', 'Purchase the Full Game']
for i in (1, 4):
    words = menu.copy()
    if i == 4:
        words[-1] += ' at www.basiliskgames.com'
    decide(i, [region(t, [0, y*100, 1000, (y+1)*100]) for y,t in enumerate(words*2)])
for i in (2,3,5,6,8,9,10,11,15,16,17,18,19,20):
    decide(i)
decide(7, [region('Quest Journal', [0,0,1000,1000])])
columns = [
    ["Nor'lander", 'Barrean', 'Rifter', 'Therish', 'Kessian'],
    ['Atheistic', 'Druidic', 'Virtuous', 'Nefarious', 'Agnostic'],
    ['Fighter', 'Rogue', 'Magick User', 'Healer', 'Ranger'],
]
decide(12, [region(t, [x*333,y*200,min(1000,(x+1)*333),(y+1)*200]) for x,c in enumerate(columns) for y,t in enumerate(c)])
decide(13, [region('You Have Died.', [300,0,700,190]),
            region('As you fall to the ground, a tunnel of light fills your vision and you feel yourself', [0,220,1000,470]),
            region('racing forward towards your destiny. In the light you sense the presence of your god.', [0,480,1000,720]),
            region("You will soon stand in judgment of your life's merits and faults.", [70,730,930,1000])])
labels = [('Name:', [20,20,130,80]), ('Title:', [640,0,740,55]), ('Gender:', [855,0,970,55]),
          ('Male', [875,55,960,95]), ('Origin', [35,105,170,160]), ('Axiom', [190,105,325,160]),
          ('Class', [345,105,480,160]), ('Attribute Points:', [630,100,890,158]), ('Next', [520,280,615,330]),
          ('Known Skills', [80,375,330,430]), ('Available Skills', [365,375,598,430]),
          ('Skill Points:', [620,600,805,658]), ('Continue', [835,680,980,735])]
labels += [(t,[785,165+y*50,967,207+y*50]) for y,t in enumerate(['Strength','Dexterity','Endurance','Speed','Intelligence','Wisdom','Perception','Concentration'])]
decide(14,[region(t,b) for t,b in labels])
target = root/'ImageText/decisions-batch1-v1.json'
target.write_text(json.dumps({'records': records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(target)
