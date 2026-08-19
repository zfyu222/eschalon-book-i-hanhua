# Eschalon: Book I（建议中文名：阿斯卡隆：卷一）AINiee 翻译指南

本项目使用统一离线语料翻译。当前原文库为 `eschalonbook_text.csv`：

- 3048 条文本
- 3048 个物理行
- 当前 `eschalonbook_text_translated.csv` 只是等长原文模板，不包含需要继承的旧译文
- 源语言：英语
- 目标语言：简体中文

## 一、AINiee 必做设置

### 1. 导入禁翻表

1. 启动：

   ```powershell
   cd D:\StaticHanHua\Tools\AINiee
   .\venv\Scripts\python.exe AiNiee.py
   ```

2. 打开左侧“禁翻表”，开启顶部开关。
3. 导入本目录的 `ainiee_exclusion_list.json`。
4. 点击“保存”。

不要使用自动扫描生成的宽泛方括号/尖括号规则。`[Attack]`、`[Quest Complete]`
和 `<cough>` 都是玩家可见文本，需要翻译内部内容。

### 2. 确认“自动预处理文本”已开启

在“应用设置”→“高级设置”→“翻译设置”中，开启“自动预处理文本”。
它对应的内部配置键为 `auto_process_text_code_segment`；本机当前已经是开启状态。

它会在译前暂存禁翻内容，译后恢复，可防止 `* & # ^ $`、`||` 和字面 `\n`
被删除、全角化或改变数量。

### 3. 导入术语表

导入 `ainiee_glossary.csv`。建议先确认专名音译；一旦开始翻译，不要中途更换译法。

## 二、推荐提示词

将以下内容追加到 AINiee 的系统提示词：

```text
你正在翻译经典西式奇幻 CRPG《Eschalon: Book I》的游戏文本，目标语言为简体中文。

翻译要求：
1. 语言自然、简洁，采用经典欧美奇幻 RPG 的叙述语气；UI 和战斗提示优先短而清楚。
2. 严格遵守术语表，同一角色、地点、属性、技能和物品始终使用同一译名。
3. 原文中的半角控制符 *、&、#、^、$ 必须逐个保留，数量不变，并放在对应中文词语之前。
4. “||”是游戏换行符，必须原样保留；字面“\n”必须保持为反斜杠+n，禁止写成真实换行。
5. [END]、[BACK]、[LOCKED]、[EXIT] 是机器标记，必须原样保留。
6. 其他方括号内容是玩家选项或战斗提示：翻译内部文字，但保留半角 [ ]。
   例如 [Attack] -> [攻击]，[Quest Complete] -> [任务完成]。
7. <cough> 等尖括号内容是可见动作描述：翻译内部文字，但保留半角 < >。
8. 单独的 $ 可能是玩家姓名占位符，必须保留；$Click 这类写法只保护 $，后面的单词仍需翻译。
9. 不增加原文没有的信息，不删除数值、百分号、引号和标点，不把半角符号改成全角控制符。
10. 若整条文本明显是 quest、remove_item、init_trade、screen_fade 等内部命令，则原样输出。
```

## 三、文风建议

- 叙事和书籍：自然、略带古典奇幻感，避免现代网络用语。
- NPC 对话：保留人物态度；粗鲁、虔诚、胆怯等语气应有区别。
- UI/战斗：尽量精炼，例如 `Save vs Disease: SUCCESS!` → `疾病豁免：成功！`。
- `Magick` 是世界观拼写，不必生造“秘法术”，统一译为“魔法”。
- `Book I` 建议译为“卷一”，不要译成“第一本书”。

## 四、开始翻译

1. 将 `eschalonbook_text.csv` 拖入 AINiee。
2. 选择英语 → 简体中文。
3. 输出保存为：

   `D:\StaticHanHua\Projects\EschalonBook\eschalonbook_text_translated.csv`

4. 必须保持 3048 条逻辑记录、3048 个物理行，并与原文逐行对应。

## 五、翻译后校验

翻译完成后运行：

```powershell
C:\Users\zfyu2\AppData\Local\Programs\Python\Python312\python.exe `
  D:\StaticHanHua\.agents\skills\game-translate\scripts\validate_translation.py `
  D:\StaticHanHua\Projects\EschalonBook\eschalonbook_text.csv `
  D:\StaticHanHua\Projects\EschalonBook\eschalonbook_text_translated.csv `
  --fix --fix-newlines --retranslate-out need_retranslate.csv
```

退出码：

- `0`：格式校验通过，可以进入回填测试。
- `1`：查看 `need_retranslate.csv`，修复或重翻后再次校验。
- `2`：行数错位，必须先恢复 3048 对 3048。

## 六、人工抽查重点

- 搜索 `*`、`&`、`#`、`^`、`$`：确认符号数量与原文一致。
- 搜索 `[END]`、`[BACK]`、`[LOCKED]`、`[EXIT]`：必须保持英文机器标记。
- 搜索 `[Attack]`、`[Quest Complete]`：这些不应残留英文。
- 搜索 `<cough>`：应成为 `<咳嗽>` 等中文动作描述。
- 搜索真实换行：CSV 每条记录不得跨物理行；应使用字面 `\n`。
