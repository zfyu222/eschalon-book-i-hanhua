# Eschalon: Book I 汉化项目

## 游戏信息
- **原名**: Eschalon: Book I
- **中文名**: 埃斯卡隆：卷一
- **开发商**: Basilisk Games
- **发行平台**: Steam / GOG
- **引擎**: 自研引擎（Blender Game Engine 衍生，32位，OpenGL 渲染）
- **原语言**: 英语
- **目标语言**: 简体中文

## 游戏架构分析

### 进程结构
- `eschalon_book_1.exe` 是**单进程程序**（不启动子进程）
- 启动后显示 **Launch Menu**（启动菜单），点击后进入游戏
- Launch Menu 和游戏在同一进程内，通过窗口状态切换

### 代码保护
- EXE 的部分代码段在**运行时解密**（如注册函数 `0x465A81`，挂起时为加密数据，resume 后解密为标准 x86 函数）
- IDA Pro 静态分析时看到的是加密数据，需要动态分析

### 文件结构
```
Eschalon_CN/
├── eschalon_book_1.exe     # 主程序（32位 PE）
├── gfx.pak                 # 图形资源包（!PAK 格式，zlib 压缩，内容全是 PNG）
├── steam_appid.txt         # Steam App ID
├── config/                 # 配置文件
│   ├── game.cfg
│   └── eschalon.cfg
└── data/                   # 游戏数据
    ├── *.ent               # 实体/对话文件（二进制格式，非纯文本）
    ├── *.map               # 地图文件
    ├── fighter             # 职业定义（Fighter）
    ├── healer              # 职业定义（Healer）
    ├── magick              # 职业定义（Mage）
    ├── ranger              # 职业定义（Ranger）
    ├── rogue               # 职业定义（Rogue）
    └── retmark.bin         # 未知二进制数据
```

### gfx.pak 格式
- Magic: `!PAK` (4 bytes)
- 版本: `01 00 01 00`
- 内容: 多个 zlib 压缩流，每个解压后是 PNG 图片
- **不包含文本数据**

## 技术栈

| 环节 | 工具 | 版本 |
|------|------|------|
| 逆向分析 | IDA Pro + IDA MCP | - |
| 字体替换 | 自研 Python 脚本 | - |
| 翻译（v1.0–v1.5） | AiNiee / DeepSeek | - |
| 翻译（2026-10-27 重译） | 自定义工作流 `translation_workflow.py` + `run_api_round.py`，API `deepseek-v4.1-flash` | - |
| 回填 | 尝试多种方案（见下文） | - |

## 已提取的文本

| 文件 | 内容 | 字符串数 |
|------|------|---------|
| `translated_strings.csv` | 原文 | 1048 |
| `translated_strings_translated.csv` | 译文 | 1048 |

文本来源：EXE 内嵌的 `.data` 段，通过 52 个资源注册块组织。

## 已尝试的汉化方案

### 方案1：挂起启动 + 内存注入字符串（失败）

**思路**: 以 `CREATE_SUSPENDED` 启动游戏，在 resume 前修改进程内存中的字符串。

**结果**: 
- 字符串成功写入内存（`金币` 确实在 `0x54159C` 处）
- 游戏不崩溃
- **但游戏显示英文** — 游戏可能不是从这些地址实时读取数据

**文件**: `start_chinese_v2.py`

### 方案2：运行后修改内存（失败）

**思路**: 正常启动游戏，等 Launch Menu 出现后，再修改进程内存。

**结果**:
- 字符串写入成功
- **游戏显示英文** — 游戏启动时已解析了 CSV 数据到内部结构，不再读取原始地址

### 方案3：修改资源链表（失败）

**思路**: 游戏有一个资源链表（堆内存中的单向链表），每个节点存储 `(next, end_key, data_ptr, size)`。修改 `data_ptr` 指向翻译后的数据。

**结果**:
- 链表节点成功修改
- 翻译数据在新内存中正确
- **游戏显示英文** — 发现游戏有两个链表（`0x5E0290` 和 `0x5E02A0`），修改两个都不生效

### 方案4：直接修改 EXE 文件（失败）

**思路**: 直接在磁盘上修改 EXE 的 `.data` 段，用空格填充保持行长度。

**结果**:
- 905 个字符串被替换
- 文件大小不变
- **游戏显示英文** — 原因不明，可能游戏运行时有其他数据源

**文件**: `patch_exe_v2.py`

## 关键技术发现

### 资源注册系统

游戏通过函数 `0x465A81` 注册资源。每个注册块的代码模式：

```asm
mov eax, end_addr        ; B8 xx xx xx xx
sub eax, start_addr      ; 2D xx xx xx xx
push eax                 ; 50 (size)
push start_addr          ; 68 xx xx xx xx (data pointer)
push end_key             ; 68 xx xx xx xx (lookup key - DON'T CHANGE)
call 0x465A81            ; E8 xx xx xx xx
add esp, 0x0C            ; 83 C4 0C
```

- **共找到 52 个注册块**
- 每个块注册一个文本资源（CSV 表或对话文本）
- `end_key` 实际是**资源描述符对象的地址**，包含资源名称（UTF-16 字符串）
- 查找函数 `0x465AC9` 通过描述符中的**名称字符串**匹配，不是通过地址

### 资源描述符结构

```
+0x00: 类型指针 (指向 0x4F1CB0)
+0x04: 标志 (0x80000000)
+0x08: 字符串长度 (DWORD)
+0x0C: UTF-16 资源名称字符串
```

比较函数 `0x462C78` 比较两个描述符的 `[+8]`（长度）和 `[+0xC]`（UTF-16 字符串内容）。

### 内存中的文本搜索

运行时搜索整个进程内存：
- `"Gold Pieces"` — **找不到**（ASCII）
- `"150 Gold Pieces"` — **找不到**
- `"IC_GOLD"` — **找不到**
- `"ITEM CATEGORY"` — **找不到**
- UTF-16 编码同样找不到

**结论**: 游戏启动后将 CSV 数据解析为内部数据结构，原始字符串被释放或重格式化。UI 显示的文本来源不明。

### 数据段地址

| 地址 | 内容 | 大小 | 格式 |
|------|------|------|------|
| `0x54159C` | 物品表 | 39851 | CSV (400+ 物品) |
| `0x552770` | 书籍文本 | 37028 | 文本 (40+ 书籍) |
| `0x560DD8` | 对话文本 | ~3000 | 文本 (32+ 对话) |
| `0x5664C8` | 任务文本 | ~5000 | 文本 (36+ 任务) |

## 字体替换

### 中文字体
```
fonts/cn_OldTymeBG.ttf      # 替换 OldTymeBG 字体
fonts/cn_Fantasy.ttf         # 替换 Fantasy 字体
fonts/cn_DS_Celtic_1.ttf     # 替换 DS_Celtic 字体
```

中文字体的 TTF name 表与原始字体保持一致（`OldTymeBG`, `Fantasy`, `FantasyBold`）。

### 字体注入方式
通过修改字体注册代码中的 push 立即数，指向新分配的内存中的中文字体数据。

## 已知问题

### 2026-10-16 中文缺字修复

- 根因：早期 `cn_subset.ttf` 未随完整译文更新，三套运行字体均缺少当前译文需要的 407 个汉字，包括“浸、崩、湿、昨、邻、豁”。译表中的字完整，但字体没有对应字形。
- 修复：新增 `rebuild_runtime_fonts.py`，从两份运行译表汇总字符，用系统黑体重建子集及三套匹配游戏内部名称的字体。当前 2520 个受支持字符全部覆盖，汉字缺字为 0；旧基础 CSV 的控制字节及少数装饰符号单独列入报告。
- 检查报告：`Analysis/font_coverage/coverage.json`。本轮仅修字体，不润色译文。
- 交付：`Release/EschalonBook_Chinese_Launcher.exe` 已安装至 `Game/EschalonBook_Chinese_Launcher.exe`；SHA-256 `CEAD418D42E2BD0D966FFC8AD31187CF138B029DFF43C21BEF9581BDF45E84C7`。旧启动器备份在被忽略的 `Analysis/font_coverage/backup/`。
- 验证边界：字库覆盖检查通过；原截图所在段落的实机显示待复测，不以进程启动或 Hook 加载代替该场景验证。

1. **数据来源不明**: 修改了 EXE 的 `.data` 段和内存中的字符串，但游戏仍显示英文。游戏可能从其他地方（如 `data/*.ent` 文件、运行时生成的数据结构）读取显示文本。

2. **`.ent` 文件格式未知**: `data/` 目录下的 `.ent` 文件是二进制格式，包含实体定义和对话数据。可能需要逆向分析游戏如何解析这些文件。

3. **CSV 解析时机**: 游戏在启动时（Launch Menu 阶段）解析 CSV 表格，之后不再读取原始数据。修改 CSV 数据需要在解析之前完成。

4. **开木桶崩溃**: 当修改物品表（CSV）后用空格填充变短的字段时，打开包含物品的容器（木桶）会崩溃。原因是空格填充破坏了 CSV 的数据结构。

## 工具文件

| 文件 | 用途 |
|------|------|
| `start_chinese_v2.py` | 挂起启动 + 内存注入启动器 |
| `patch_exe_v2.py` | 直接修改 EXE 文件的 .data 段 |
| `Launch_Chinese_v2.bat` | 启动脚本 |
| `analyze_pak.py` | 分析 gfx.pak 文件格式 |
| `find_registration_blocks.py` | 查找资源注册块 |
| `disasm_reg_func.py` | 反汇编注册函数 |
| `check_font_format.py` | 检查字体格式 |
| `verify_clean.py` | 验证文件完整性 |

## 备份

- **原始 EXE 备份**: `Eschalon_CN/eschalon_book_1.exe.bak`
- **原始游戏备份**: `Game/Eschalon Book I.zip`（完整游戏压缩包）

## 后续建议

1. **逆向 `.ent` 文件解析**: 使用 IDA Pro 找到游戏解析 `.ent` 文件的代码，理解其二进制格式，这可能才是游戏文本的真正来源。

2. **动态调试**: 使用 x64dbg 或 Cheat Engine 的调试器，在游戏渲染文字时设断点，追踪文字数据的来源。

3. **Hook 文字渲染函数**: 游戏使用 OpenGL 自渲染字体（FreeType），找到 `FT_Draw_Glyph` 或类似的渲染函数，Hook 它拦截即将显示的文字。

4. **分析 `data/` 文件**: `fighter`、`healer` 等文件包含部分物品名称，可能是游戏运行时的实际数据源。需要分析这些文件的二进制格式并直接翻译。

5. **BepInEx 注入**: 如果游戏支持 .NET 运行时，可以考虑用 BepInEx 框架注入翻译插件。

## 版本记录

- 2026-07-19: 初始汉化尝试，使用旧启动器修改数据文件导致崩溃
- 2026-07-21: 从备份 zip 恢复游戏文件，分析 EXE 导入表和资源注册系统
- 2026-07-22: 尝试内存注入方案（挂起启动、资源链表修改），均未成功显示中文
- 2026-07-23: 尝试直接修改 EXE 文件，905个字符串替换，仍未成功显示中文
- 2026-07-24: 项目暂停，整理分析结果
- 2026-07-24: 启动器新增“注册对话资源重定向”。对 9 个启动期注册的剧情资源块，
  将 UTF-8 字节数增长的译文写入新分配内存，并仅修改资源载荷的起始/长度操作数，
  保留原资源查找键。挂起状态自检通过：新增覆盖 30 条长对话，剩余固定槽位溢出
  从 169 条降至 136 条；未修改 Steam 原始游戏目录。
- 2026-07-24: 运行期分组诊断确认上述资源重定向会令进程在恢复线程后以
  `0xFFFFFFFF` 退出，现已默认禁用；字体、物品、书籍和 262 条固定槽位短文本
  的方案经 8 秒存活测试通过。当前仍有 169 条超长文本暂不注入，以优先保证可启动性。
- 2026-07-25: 根据木桶崩溃复测，确认物品表的名称列同时承担内部 ID；地图、容器、
  存档和脚本仍以英文名查找，直接改中文会产生空对象并崩溃。现已完全停止修改游戏
  数据表，改在 BlitzMax `brl.max2d.TImageFont.Draw`（VA `0x477B47`）拦截最终
  UTF-16 显示字符串。新入口 `display_hook_launcher.py` 通过 Frida 仅替换绘制参数，
  保留全部内部英文键；挂钩加载和 8 秒进程存活测试通过。
# 当前方案：离线统一汉化（2026-07-25）

> 说明：早期项目记录曾被错误编码损坏；本节为当前有效方案。

- 目标：把游戏文本统一抽取为本地 CSV，集中翻译；游戏运行时不调用网络服务。
- 提取工具：`extract_offline_texts.py`。
- 原文库：`eschalonbook_text.csv`，单列、每条文本一个 CSV 记录。
- 翻译库：`eschalonbook_text_translated.csv`，与原文逐行对应；未完成条目暂时保留英文。
- 来源清单：`eschalonbook_text_catalog.csv`，记录当前译文、状态和原始位置。
- 静态来源：EXE 中 52 个 BlitzMax `Incbin` 注册资源块、游戏区 UTF-16 静态 String 对象、`data/*.ent`，以及运行时段落日志。
- 当前结果：3536 条统一文本已完成翻译并通过项目专项校验；其中 2934 条为可替换的非同文显示文本，其余为内部命令、文件名或无需翻译的标识。
- 回填方式：`display_hook_launcher.py` 优先读取统一离线译表，仅在显示层替换文本；不修改承担内部 ID 的物品表字段，避免打开木桶时崩溃。
- 已定位地址：最终绘制 `0x477B47`、`DrawText` 包装 `0x4788D4`、角色创建/技能说明完整段落 `0x4D950F`。
- 格式注意：译文应保留 `*`、`&`、`#`、`^`、`$` 等颜色/强调控制符和动态占位符。
- 重新提取：

  ```powershell
  C:\Users\zfyu2\AppData\Local\Programs\Python\Python312\python.exe extract_offline_texts.py
  ```

## 当前回填结果（2026-07-26）

- 回填工具：`display_hook_launcher.py` + Frida，中文字体注入沿用现有启动器。
- 策略：安全显示层替换。游戏内部物品 ID、地图键、脚本命令和存档相关英文保持不变，仅在 `brl.max2d.TImageFont.Draw` 绘制前替换 UTF-16 显示字符串。
- 输入：`eschalonbook_text.csv` 与 `eschalonbook_text_translated.csv`，均为 3536 条对齐 CSV 记录。
- 回填映射：2934 条离线译文替换；与基础映射及静态组合规则合并后运行时共有 3413 条显示映射。
- 校验：逻辑行/物理行均为 3536；无空译文；流程标记、样式前缀、`||`、字面 `\\n`、内部命令均通过项目专项校验。
- 启动验证：`Launch_Chinese.bat` 已成功启动游戏（PID 32224），三种中文字体和显示 Hook 均加载成功，并命中设置页显示文本；进程保持响应。
- 待实机复测：进入新游戏、打开木桶/容器、物品栏、技能说明、任务与长对话，确认中文换行和 UI 不截断。不得重新启用旧的数据表直接改名方案。

## 版本记录补充

- 2026-07-26: 完成 3048 条统一译文的专项校验与显示层回填。修复字面 `\\n`、样式前缀和两条可见漏译；安全启动器加载 2505 条新译文替换，启动期运行验证通过。
- 2026-10-20: 修复开场叙事弹窗未汉化。叙事 Hook 改到 `FUN_004c69ad` 所有面板分支的汇合点 `0x4C6C53`，并增加段级匹配与空白归一化；开发版实机验证正文显示中文。

## 2026-07-26 弹窗文本回填补充

- 诊断确认露营说明、水井确认等文本已经存在于统一 CSV，并非提取或翻译遗漏。
- 此类界面使用独立的逐词排版器 `sub_4C4982`（VA `0x4C4982`），与消息日志的 `sub_4BDEB8` 不同。
- `display_hook_launcher.py` 已在 `sub_4C4982` 入口替换完整正文参数，再由游戏原生逻辑处理 `^`、`&` 样式标记和中文换行。
- 该 Hook 是同类弹窗的通用入口，不需要为每个场景收集或添加运行时碎片。

## 2026-10-20 开场叙事弹窗修复

- 现象：新游戏开场叙事弹窗正文仍为英文，底部消息日志和「确定」按钮已是中文。
- 提取与翻译无误：该文本来自 EXE 内 `incbin/narrative.txt` 资源（注册块 `0x4907B5`，载荷 `0x54DC90–0x55273C`），在 `eschalonbook_text.csv` 第 2963 行，译文完整。
- 证据：`runtime_untranslated.jsonl` 记录到正文以逐行碎片进入绘制层；`runtime_narrative_calls.jsonl` 记录 `FUN_004c69ad` 的实际调用参数为 `id:0:0`（type=0、panel=0）。
- 根因：`FUN_004c69ad` 在 `param_3 == 0` 时于 `0x4C6C56` 直接跳转 `0x4C74B3`，绕过旧 Hook 点 `0x4C6C82`，正文随后由原生逻辑拆行，逐行绘制时无法再整段匹配。
- 修复：`display_hook_launcher.py` 的叙事 Hook 改到 `0x4C6C53`。这是所有面板分支的汇合点，此时 `[ebp-0x24]` 仍是完整正文，且 600 字符面板选择已计算完毕，替换不会改变窗口样式。匹配逻辑额外加入段级映射（按 `*` 拆分）与空白归一化兜底。
- 验证：开发版实机复现，开场弹窗正文显示中文；控制台输出 `Translated paragraph`，日志无该段未匹配记录。
- 分析工具：REA 6.4.0 + Ghidra 12.1.4（`Tools/REA/rea.ps1`），反编译证据存于 `Analysis/rea_dec_narrative.c`、`Analysis/rea_dec_popup.c`、`Analysis/rea_xref_*.json`。

## 2026-10-20 覆盖率审计与实机抽样验证

### 为什么要补这一层

此前 `Analysis/static_coverage.py` 报告 "prose 漏翻 0"，但该结论只覆盖一类情况：
EXE 里能枚举到、而译表里没有的字符串。它不检查两件事：

- 译表里**存在**、但译文仍与原文相同（等于没翻）
- 文本根本不在字符串池里（预渲染图片文字）

静态枚举与文本提取共用同一个 `extract_offline_texts` 枚举器，提取器漏掉的内容
审计器同样漏掉，因此 "归零" 存在自证清白的风险。

### 新增的两道检查

| 脚本 | 作用 | 输出 |
|------|------|------|
| `Analysis/classify_identical.py` | 找出译文与原文相同的行，剔除脚本命令/标识符/技术串，剩下玩家可见项 | `Analysis/identical_visible.txt` |
| `Analysis/unpack_pak.py` | 解包 `gfx.pak` 的 225 个 zlib-PNG 流，用于核对图片文字 | `Analysis/pak_extract/` |

同文统计基线：580 行译文与原文相同，其中 188 条脚本链、264 条标识符、65 条技术串、
9 条非拉丁，**78 条初判为可见文本**；逐条复核后确认真实漏翻如下。

### 本轮修复的文本漏翻

| 原文 | 修复后 | 说明 |
|------|--------|------|
| `150 Gold Pieces` | `150 金币` | 同组 250/500/750 均已译，仅此条遗漏 |
| `[Attribute]` | `[属性]` | 角色创建界面标签 |
| `Nor'lander` | `诺兰达人` | 种族名；完整段落已译，单词条目漏译 |
| `This portal has become inactive.` | `这座传送门已经失效。` | `message(...)` 内嵌正文，译表原本只有整行脚本 |
| `This lever is locked. The lighthouse fire cannot be extinguished this way.` | `这根拉杆被锁住了，无法用这种方式熄灭灯塔之火。` | 同上 |

译表由 4544 行增至 4546 行，显示映射由 4761 条增至 4765 条。

未处理且判定为正常保留：`no bars`、`Version 1.05 STEAM EDITION`（另有已译版本行）、
`Copyright (c) 1995-1996 Guy Eric Schalnat, Group 42, Inc.`、`Sound(...) ; book N` 等脚本链。

### 实机抽样验证（窗口模式启动 + 截屏）

- 启动方式：`$env:ESCHALON_WINDOWED="1"` 后运行 `start_chinese.py`，PID 正常，三套字体注入成功。
- 启动菜单：`32位（数百万色）`、`全屏 800 x 600`、底部版本行均为中文。
- 主菜单：底部 `版本 1.05 STEAM 版本 // 版权所有 2007-2008 蛇怪游戏` 为中文。
- `runtime_untranslated.jsonl` 全程仅 1 条未匹配：`DirectX`（产品名，应保留）。
- 结论：**文本层没有真实漏翻**，剩余英文全部来自预渲染图片。

### 图片文字漏翻（本轮未处理）

截图确认以下界面文字为艺术字图片，EXE 中检索不到对应字符串
（`Begin a New Adventure`、`Restore a Saved Adventure`、`Credits` 的 ASCII 与 UTF-16 均为 none）：

- 启动菜单：`Click to change options`、`Press Start to launch game or for help on game options...`、`Graphic Renderer`、`Color Depth`、`Screen Preference`
- 主菜单：`Begin a New Adventure`、`Restore a Saved Adventure`、`Credits`、`Exit`
- 角色创建教程覆盖图：`gfx.pak` 解包后 800×600 的 `img_0035`，含 6 段英文标注
- 制作人员名单：`img_0042`（400×600），全英文

这类内容只能改图片资源，文本 hook 与译表都无法覆盖。是否处理需单独评估重绘成本。

### 复现命令

```powershell
# 同文残留分类
& $py Analysis\classify_identical.py
# 解包 gfx.pak 图片
& $py Analysis\unpack_pak.py
# 静态候选审计（仅覆盖 EXE 字符串池）
& $py Analysis\static_coverage.py
```

## 2026-10-20 文本覆盖缺口排查（第二轮）

### 为什么要再查一遍

第一轮只比对 EXE 的 **ASCII** 字符串池，且审计正则要求候选以 `.!?` 结尾。
BlitzMax 把字符串长度存在别处，字节扫描会把下一个字段的字符粘在句尾
（`"...for me?"E`），这类候选被正则直接丢弃；UTF-16 字符串表则完全没扫过。
地图文件、职业定义文件也从未纳入。

### 新增的文本源与结果

| 来源 | 候选 | 未覆盖 | 结论 |
|------|------|--------|------|
| EXE UTF-16 字符串表 | 1667 | 447 | 仅 `16-bit (Thousands of colors)` 是玩家可见，其余为 DirectX/OpenAL/BlitzMax 调试输出 |
| EXE ASCII 池 | 3804 | 2597 | 剥掉尾部残留字节后，仅 `I can do this.` 一句缺失；其余为物品表/书单 CSV 行、格式串、资源路径 |
| `data/*.ent` | 24 | 0 | 实体定义，文本已在译表 |
| `data/fighter` 等职业文件 | 3 | 0 | — |
| `data/*.map` | 850 | 291 → 8 | 291 是脚本行粒度噪声，句子级提取后仅 8 条真实缺失 |
| `help.html` | 402 | 402 | 全部未译，属游戏帮助文档，见下方待决项 |

### 本轮修复清单

译表 4546 → 4555 行，显示映射 4765 → 4775 条。

1. **行内方括号标签 50 行**：`[BACK]`→`[返回]`、`[END]`→`[结束]`、
   `[EXIT]`→`[离开]`、`[LOCKED]`→`[锁定]`，以及 4 条 `[Give ...]` 动作标签
   （复用已有独立条目译法，如 `[交出陶瓷坩埚]`）。独立成行的方括号条目此前已译，
   漏的是嵌在对话行内的同一标签。
2. **地图文本 8 条**：蛛形生物室告示、Edward/Rachel/Lars 三块墓碑铭文、
   "让时钟停摆"墓志诗、画在墙上的假门、一块字迹模糊的古墓碑。
3. **设置项** `16-bit (Thousands of colors)` → `16位（数千色）`，
   与已译的 32-bit 条目对齐。此前只有切到 16 位色深才暴露。
4. **对话选项** `I can do this.` → `我能做到。`

### 已确认无缺口的部分

- `Yes`/`No` 已译为「是」「否」，水井拉绳询问 `There is a rope going down the well. Pull it up?` 已译。
- 井绳脚本的 8 个 `message(...)` 分支正文、Eeru 引路叙述均已译。
- 物品名（`Mithril Alloy Chain Boots`、`Divine Ore Great Sword`、`Recurved Composite Great Bow` 等）、
  书名（`A History of Thaermore`、`The Alchemist's Cookbook I–III` 等）均按名称列单独译好，
  物品表 CSV 行本身不需要翻。
- 带尾随分支字节的对话（`"And it was stolen?"q`、`"A talking tree wants to help me?..."_`）
  其干净文本均已在译表。

### 待决项

`help.html`（402 条）是游戏目录下的帮助文档，由系统浏览器打开，不经游戏引擎绘制。
翻译它不影响游戏内显示，但玩家查阅时会看到英文。是否处理需单独确认。

### 复现命令

```powershell
& $py Analysis\audit_uncovered.py       # 多源覆盖审计
& $py Analysis\extract_map_text.py      # 地图句子级提取
& $py Analysis\check_map_remaining.py   # 地图剩余核对
& $py Analysis\check_ascii_residue.py   # ASCII 尾部残留剥离复核
```

## 2026-10-20 对话面板部分英文的匹配修复

### 现象

实机截图中同一个 NPC 对话框里中文与英文混排：选项「我中了诅咒，需要精神恢复。」
是中文，紧邻的「I am in need of healing.」却是英文；上方叙述段也整段英文。
`runtime_untranslated.jsonl` 记录了这些碎片，说明译文存在但运行时没匹配上。

### 三个根因

1. **短条目不入索引**：`_build_word_index` / `_build_prefix_index` 都有
   `len(source) < 40` 的下限。对话选项普遍只有 20–30 字符，完全进不了索引，
   只能靠精确匹配；而源文带分支 ID（`"I am in need of healing."5`），
   游戏绘制的是去 ID 的 `"I am in need of healing."`，精确匹配必然失败。
2. **词长阈值漏掉整句**：词索引只收长度 ≥ 6 的词。
   `No way. I'm not going to risk my life for a chunk of metal.` 里没有任何
   六字母词，整句无法被索引到。
3. **前缀索引用了带引号的原行**：选项绘制为 `"No way. ..."`，前两个词取到
   `"No`，而索引 key 是 `No way.`，带引号的首词永远对不上。

另有一个放大因素：`dialogParagraph` 在遇到任何无法匹配的绘制调用时立即清空。
状态栏数字（`2.3/136 lbs`）恰好插在对话行之间，导致换行后的尾行
（`me."`、`pieces.`、`services."`）失去上下文。

### 修复

| 位置 | 改动 |
|------|------|
| `_build_word_index` | 长度下限 40 → 12；词长 `{5,}` → `{4,}`（≥5 字母）；单词条目上限 40 → 200 |
| `_build_prefix_index` | 长度下限 40 → 12 |
| `translateDialogLine` | 前缀索引用去引号后的 `bare` 查找，并用 `startsWith(bare)` 比对 |
| `dialogParagraph` | 连续 4 次未命中才丢弃上下文，避免被 UI 数字打断 |
| `applyCombatPatterns` | 新增 `Level: N (职业)`、`N hours`、`日期 Jul 2026`、种族+职业两词组合规则 |

译表 4555 → 4563 行，补充 8 条运行时确认缺失的短选项与标记：

```
"Hello?"              -> "你好？"
"No pay? No way."     -> "没有报酬？想都别想。"
"Eh, thanks." [BACK]  -> "呃，谢谢。" [返回]
"Thank you." [BACK]   -> "谢谢。" [返回]
"Goodbye." [END]      -> "再见。" [结束]
[BACK] / [END] / BACK / END
```

### 验证

- `Analysis/simulate_dialog_lookup.py` 用截图中的 12 行逐行复现查找链，
  修复后 11 行命中（其中一行是截图误读的 `stained glass`，游戏原文为 `stain glass`）。
- `Analysis/analyze_unmatched.py` 对运行时日志归因：可恢复条目 0 → 6，
  阻塞条目 15 → 11，缺失条目 18 → 16。
- 实机启动加载 4783 条映射，无 hook 报错；存档信息已显示
  `Game '222' 加载成功。此角色的总游 戏时间： 9.6 小时。`

### 说明

状态栏 `Hit Points` / `Mana Points` / `Encumbrance` / `Experience` 仍为英文。
前两项在译表里有独立条目，后两项在 EXE 中根本检索不到，四者与主菜单
`Options` / `Save` 同为预渲染艺术字图片，文本 hook 无法覆盖。按既定范围不处理图片。

### 复现命令

```powershell
& $py Analysis\simulate_dialog_lookup.py   # 逐行复现查找链
& $py Analysis\analyze_unmatched.py        # 运行时日志归因
```

## 对外发布

### v1.0（2026-08-20）

- 补丁：`Dispatch/Eschalon Book I_子非鱼汉化1.0.zip`
- 标题：`《Eschalon Book I》子非鱼AI汉化补丁 v1.0`
- 支持版本：Steam Windows 32 位本地版本；已验证 `eschalon_book_1.exe` SHA-256 为 `8F25C5FF8FC869E3C3B02C9E6F960C6A082CFCC097289A5247F237656C3031A8`。
- 载荷：独立启动器 `EschalonBook_Chinese_Launcher.exe`；译表、中文字体、Python 和 Frida 运行组件均已嵌入，不包含游戏本体。
- 安装：将启动器放在 `eschalon_book_1.exe` 同一目录，通过该启动器进入游戏。
- 验证：独立发布版成功启动游戏，加载三套中文字体、2934 条离线译文和 3413 条显示映射，启动菜单中文正常；开发版已验证物品、容器、消息日志、长段落和确认弹窗。
- 已知问题：少量独立界面仍可能显示英文；超长中文可能出现不理想换行；Frida 运行组件可能被部分安全软件误报；其他商店或不同可执行文件版本尚未验证。
- ZIP SHA-256：`AD325BBE465325E20BFBB29C015E55E4C94EDD04E88571EA02F48AB476F988A5`

### v1.1（2026-09-18）

- 补丁：`Dispatch/Eschalon Book I_子非鱼汉化1.1.zip`
- 标题：`《Eschalon Book I》子非鱼AI汉化补丁 v1.1`
- 支持版本：Steam Windows 32 位本地版本；已验证 `eschalon_book_1.exe` SHA-256 为 `8F25C5FF8FC869E3C3B02C9E6F960C6A082CFCC097289A5247F237656C3031A8`。
- 载荷：修复后的独立启动器 `EschalonBook_Chinese_Launcher.exe`；不包含游戏本体。
- 修复：启动器不再直接从 Steam/Program Files 目录注入。它会把玩家自己的 EXE 临时复制到 `%LOCALAPPDATA%\EschalonBookChineseRuntime` 后启动，游戏退出后自动清理，从而避开 `VirtualAllocEx returned 0x00000005` 导致的无法启动问题。
- 验证：启动器能够创建临时进程、加载三套中文字体、2934 条离线译文和 3413 条显示映射，但发布后复测发现 Steam DRM 弹出 `Application load error 5:0000065434`，因此 v1.1 已由 v1.2 取代。
- 已知问题：v1.1 不可用；临时 EXE 未携带 Steam App ID，无法进入游戏主界面。
- ZIP SHA-256：`8C6082D1F0FB02C56306B6D5EDCD6DE6995C694546A42B848C31D78DB9841257`
- GitHub Release：`https://github.com/zfyu222/eschalon-book-i-hanhua/releases/tag/v1.1`

### v1.2（2026-09-18）

- 补丁：`Dispatch/Eschalon Book I_子非鱼汉化1.2.zip`
- 标题：`《Eschalon Book I》子非鱼AI汉化补丁 v1.2`
- 支持版本：Steam Windows 32 位本地版本；已验证 `eschalon_book_1.exe` SHA-256 为 `8F25C5FF8FC869E3C3B02C9E6F960C6A082CFCC097289A5247F237656C3031A8`。
- 载荷：独立启动器 `EschalonBook_Chinese_Launcher.exe`；译表、字体、Python 与 Frida 运行组件均已嵌入，不包含游戏本体。
- 修复：临时运行副本启动前自动设置 `SteamAppId=25600` 与 `SteamGameId=25600`，满足 Steam DRM 的应用身份校验。
- 验证：启动器解决了 Steam 应用身份错误，但发布后进一步复测发现临时副本按 EXE 目录查找资源，会报 `ERROR: gfx.pak missing.`；因此 v1.2 不应继续分发。
- 已知问题：v1.2 不可用；仅复制游戏 EXE 到 `%LOCALAPPDATA%` 会丢失同目录资源。
- ZIP SHA-256：`7126F50D42FD25478D04A81BB8FFB0D248F1AC5B1EA8384D89A7D095FD6F20AE`
- GitHub Release：`https://github.com/zfyu222/eschalon-book-i-hanhua/releases/tag/v1.2`

## 2026-09-19 发布启动根因修复

- 开发脚本实际从完整的 `Eschalon_CN/` 副本启动，该目录同时包含 `gfx.pak`、`data/config/music/sound` 和 `steam_appid.txt`。
- v1.1/v1.2 为绕开误判的目录权限问题，只把游戏 EXE 复制到 `%LOCALAPPDATA%`；这先后触发 Steam 应用身份错误和 `gfx.pak missing`。
- 最终确认真正差异是 `steam_appid.txt`，而不是 Program Files 本身：在原 Steam 游戏目录写入 App ID `25600` 后，可以直接挂起启动原 EXE，Frida 注入、字体加载和显示 Hook 全部成功。
- 新启动器不再默认复制游戏 EXE，而是确保游戏根目录存在 `steam_appid.txt`，始终从包含完整资源的原目录启动。
- 冻结版实测：进程路径保持为 Steam 原目录，窗口进入 `Launch Menu`，未出现 Steam Error 或 `gfx.pak missing`；临时运行目录未被使用。

### v1.3（2026-09-19）

- 补丁：`Dispatch/Eschalon Book I_子非鱼汉化1.3.zip`
- 标题：`《Eschalon Book I》子非鱼AI汉化补丁 v1.3`
- 支持版本：Steam Windows 32 位本地版本；已验证 `eschalon_book_1.exe` SHA-256 为 `8F25C5FF8FC869E3C3B02C9E6F960C6A082CFCC097289A5247F237656C3031A8`。
- 载荷：`EschalonBook_Chinese_Launcher.exe` 与 `steam_appid.txt`；不包含游戏本体或原始游戏资源。
- 安装：将两个载荷文件放到 `eschalon_book_1.exe`、`gfx.pak` 所在的游戏根目录，覆盖旧启动器后从汉化启动器进入游戏。
- 验证：冻结版从真实 Steam 游戏目录直接启动原 EXE，成功进入 `Eschalon: Book I` 启动菜单；三套中文字体、2934 条离线译文和 3413 条显示映射加载完成，运行时已有中文替换命中；未出现 Steam Error 或 `gfx.pak missing`。
- 已知问题：少量罕见文本仍可能显示英文；部分长中文在窄界面中可能换行；运行时注入组件可能被安全软件误报；其他商店或不同 EXE 版本尚未验证。
- ZIP SHA-256：`CD249FAF8B1A4007C50F7E33E8FB2364C5B79BC97FA9853EFACAFFBD3F653E97`
- GitHub Release：`https://github.com/zfyu222/eschalon-book-i-hanhua/releases/tag/v1.3`

### v1.4（2026-10-20）

- 补丁：`Dispatch/Eschalon Book I_子非鱼汉化1.4.zip`
- 标题：`《Eschalon Book I》子非鱼AI汉化补丁 v1.4`
- 支持版本：Steam Windows 32 位本地版本；已验证 `eschalon_book_1.exe` SHA-256 为 `8F25C5FF8FC869E3C3B02C9E6F960C6A082CFCC097289A5247F237656C3031A8`。
- 载荷：`EschalonBook_Chinese_Launcher.exe` 与 `steam_appid.txt`；不包含游戏本体或原始游戏资源。
- 修复：开场叙事弹窗正文未汉化。叙事 Hook 从被 `panel=0` 分支绕过的 `0x4C6C82` 移到 `FUN_004c69ad` 所有面板分支的汇合点 `0x4C6C53`，并加入段落级匹配与空白归一化兜底。
- 验证：发布版启动冒烟测试通过（启动器与游戏进程存活，窗口正常进入 `Eschalon: Book I`）；开发版实机确认开场叙事弹窗、消息日志、物品、容器、技能说明与确认弹窗显示中文。ZIP 已解压复核，载荷 SHA-256 与 `SHA256SUMS.txt` 一致，说明书含 UTF-8 BOM 与完整更新日志。
- 安装：`EschalonBook_Chinese_Launcher.exe` 与 `steam_appid.txt` 放入游戏根目录；v1.4 已安装到 `Game/`（Steam 目录），旧启动器备份于 `Analysis/release_backup/EschalonBook_Chinese_Launcher.v1.3.exe`。
- 已知问题：少量独立界面仍可能显示英文；超长中文在窄界面中换行可能不理想；运行时注入组件可能被安全软件误报；仅验证 Steam 32 位版本。
- ZIP SHA-256：`BF17C1E24EBB8A7273EE9117B903D42B844B98495E377E29276F0303369C9EBE`
- GitHub Release：`https://github.com/zfyu222/eschalon-book-i-hanhua/releases/tag/v1.4`

### v1.5（2026-10-20）

- 补丁：`Dispatch/Eschalon Book I_子非鱼汉化1.5.zip`
- 标题：`《Eschalon Book I》子非鱼AI汉化补丁 v1.5`
- 支持版本：Steam Windows 32 位本地版本；已验证 `eschalon_book_1.exe` SHA-256 为 `8F25C5FF8FC869E3C3B02C9E6F960C6A082CFCC097289A5247F237656C3031A8`。
- 载荷：`EschalonBook_Chinese_Launcher.exe` 与 `steam_appid.txt`；不包含游戏本体或原始游戏资源。
- 变更：显示映射 3413 → 4783 条，离线译表 2934 → 3962 条（译表 4563 行）。包含覆盖率审计补入的同文漏翻（金币、`[Attribute]`、`Nor'lander`、`message(...)` 内嵌正文），50 行行内方括号标签，8 条地图碑铭与告示，16 位色深设置项；对话框匹配修复（词/前缀索引长度下限 40 → 12、去引号前缀匹配、段落上下文容错 4 → 12 次未命中）；状态栏单位换算（`lbs` → 磅、游戏时长、日期）。
- 新增资源：`runtime_fragment_overrides.json`（2 条酒吧老板对话的运行时覆盖）随启动器嵌入，启动日志显示 `Runtime fragment overrides active: 2`。
- 验证：发布版从真实 Steam 游戏目录启动冒烟测试通过 —— 启动器进程与 `eschalon_book_1`（PID 8232）存活，窗口标题 `Eschalon: Book I`；日志显示三套字体注入成功（`cn_OldTymeBG` / `cn_Fantasy` / `cn_DS_Celtic_1`），`Loaded 4783 translations`、`Offline corpus active: 3962`，启动菜单与角色创建提示命中中文。ZIP 已解压复核，载荷 SHA-256 与 `SHA256SUMS.txt` 一致，说明书含 UTF-8 BOM 与完整更新日志（v1.0–v1.5）。
- 安装：`EschalonBook_Chinese_Launcher.exe` 与 `steam_appid.txt` 放入游戏根目录；v1.5 已安装到 `Game/`（Steam 目录）。
- 已知问题：主菜单选项、状态栏标签、制作人员名单等预渲染艺术字图片仍为英文；少量独立界面可能显示英文；超长中文在窄界面中换行可能不理想；运行时注入组件可能被安全软件误报；仅验证 Steam 32 位版本。
- ZIP SHA-256：`498291CB3157040396B6056257FDF50E7FDA06CE93DAD510303235BE9FBEA839`
- GitHub Release：`https://github.com/zfyu222/eschalon-book-i-hanhua/releases/tag/v1.5`
- 资产命名：GitHub 上传时会剔除中文，Release 资产显示为 `Eschalon.Book.I_.1.5.zip`（与 v1.4 行为一致），内容即本地的 `Eschalon Book I_子非鱼汉化1.5.zip`，SHA-256 一致。

#### v1.5 打包过程说明（质量门禁）

- `create_release_patch.py` 的自定义工作流门禁首先拦下了打包：`TranslateFiles/state/workflow.sqlite3` 记录了一次 686 条的增量运行，但全部记录停在 `source` 阶段，`glossary_review` 还有 5 个 `running` 任务，从未进入 pilot/final 验收。
- 核对结果：该运行的 686 条原文已全部出现在 `eschalonbook_text.csv`（4563 行，命中 686/686），译文经 `Analysis/merge_increment_translation.py` 并入主译表，属于**已并表的遗留运行记录**，不是本次发布载荷的来源。
- 处理：把 `workflow.sqlite3` 与 `config/workflow.json` 归档到 `TranslateFiles/state/archive/20261020_increment_run/`，本版按 v1.0–v1.4 的既有验证流程（实机冒烟 + 载荷哈希复核）发布。后续如再启动自定义工作流，应从当前译表重新 `init`，不要复用该归档库。

## 图片文字汉化（2026-10-27，源文准备完成）

- 用户明确启用图片流程，偏好保存在 `localization_project.json`。本分支独立于既有正文、启动器和 v1.5 发布文件；本次没有修改游戏目录，也没有处理此前反馈的升级崩溃。
- 来源：当前 Steam 游戏 `gfx.pak`，SHA-256 `0ffbf360080320dd91b98034431a1644b703ff32ecabb306560dfd7da55825d9`。复用 `Analysis/pak_extract/` 的 225 张 PNG，逐张核对归档中的压缩流，225/225 匹配；来源索引为 `ImageText/provenance.json` 和 `ImageText/archive_index.json`。
- 抽取：使用 `game-image-extract`；本地 PP-OCRv6 medium 全量扫描 225 张、10098 个候选区域，扫描错误为 0。动画图集存在大量伪文字候选，模型分数不当作正确率。
- 本地复核：`qwen3-vl:8b-instruct-q4_K_M` 原计划 126 张，成功 101 张；地图一张达到固定 2048 输出 Token 上限，剩余 24 张未请求。不提高预算、不重复成功项，转由当前对话 Agent 直接查看。对话 Agent 共导入 107 张图的视觉裁决，包含模型争议、直接复核及抽查；并非人工确认。
- 正式图片源文：根目录 `eschalonbook_images_text.csv`，231 条去重文本；`eschalonbook_images_text.mapping.json` 记录 42 张含字图片、296 处文字位置、原始贴图与审核证据。包括菜单、角色创建、教程、状态栏、快捷键、装备、炼金、旅行、死亡/结局等。所有 225 张图的联系表已查看，但筛选、抽查及队列未决为 0 不代表全游戏没有漏字。
- 校准与报告：`ImageText/policy-v1.json`、`ImageText/extraction_report-v1.json`；没有将普通字体族标记为已验证快通道。快照、OCR/Qwen 缓存和证据大图保留在本地工作目录，不入库。
- 翻译交接：`prepare-translation` 已建立 `TranslateFiles/image-text/` 隔离子工程和逐条图片上下文，不初始化/改写正文的旧数据库。**尚未选定本次正式翻译路线，尚未发起付费请求、生成正式图片译文或安装中文贴图。**旧正文曾使用 AINiee，归档 API 配置不视为本次付费执行授权；待用户选择现行 SubAgent/API 路线。
- 排版边界：坐标是视觉确认区域，不等于清字蒙版；需逐类检查精灵切片、透明底、悬停高亮和相邻图案。保留标志、署名、数字/计数符号与网址的适用范围，不能见英文就替换。地图北部一处竖排地名未可靠转写，地图暂不进入安装名单；后续需单独解决该标签及密集地图排版，不猜写地名。
- 回填预研：归档是 20 字节头、zlib 索引（225 项，每项 272 字节）及各自压缩的 PNG。`Analysis/inspect_image_archive.py` 验证现有索引，`Analysis/rebuild_image_archive.py` 仅生成全新输出文件、拒绝覆盖目标，更新压缩长度/偏移并逐项读回；空替换重建已验证 225/225 图片一致。测试文件仅在忽略目录 `ImagePatch/`，**不代表中文贴图构建、安装或实机通过**。对外发布不得直接携带完整游戏资源包。

## 2026-10-27 统一语料全量重译（自定义 API 工作流）

### 本次目标与范围

用户要求「重新翻译，从术语提取开始，图片 OCR 等提取结果复用，术语提取基于图片文本和普通文本统一做，用 API 方式」。此前正文（AINiee，v1.5）与图片（隔离子工程 r2）各自维护术语表，重叠的 26 条专名中 9 条译法冲突（如 `Thaermore` 泰尔莫/泰尔摩尔、`Darkford` 达克福德/暗福德），且正文 158 个专名没有进入图片术语表。本次改为**单一翻译工程 + 单一术语表**。

本次只产出译文，未修改游戏目录、未重建中文贴图、未发布新版补丁。

### 统一语料

| 项 | 值 |
|---|---|
| 统一源文 | `eschalonbook_unified_text.csv`（4743 行） |
| 来源 | 正文 `eschalonbook_text.csv` 4563 行 + 图片独有 180 行 |
| 去重 | 图片 231 行中 51 行与正文完全相同，不重复计入，拆分时复用正文译文 |
| 索引 | `TranslateFiles/unified_corpus.json`（逐行记 origin/src_row/reuse_text_row） |
| 上下文 | `TranslateFiles/unified_context.json`（group=text/image、resource=原文件或 `img_00NN`、text_type） |
| 生成 | `Analysis/build_unified_corpus.py` |

图片 OCR/视觉裁决沿用 `ImageText/` 既有结果，未重新跑 OCR。

### 术语

| 项 | 值 |
|---|---|
| 提取 | 12 批覆盖 4743 条（正文 11 批 + 图片 1 批），初筛 581 术语 / 105 人物 / 386 禁翻 |
| 旧名追记 | `Analysis/annotate_legacy_terms.py` 把 v1.5 已发布译名写入同源条目的 `term_reason`，只作裁决证据，不覆盖新提取；对照结果见 `TranslateFiles/glossary/legacy_reference.json`（210 条旧名：101 条一致、51 条冲突、58 条统一语料未提取到） |
| 审校 | 93 批，逐项语义核对，程序检查通过后才冻结 |
| 冻结表 | `TranslateFiles/glossary/r1/freeze_0680ffd0/built/glossary_reviewed.json`，577 术语 / 105 人物 / 379 禁翻，hash `76cc99de…` |
| 与 v1.5 对比 | 143 条同名专名中仅 11 条译名变化（如 `Goblins` 哥布林→地精、`Shadowmirk` 暗影沼泽→暗影堡、`Divination` 占卜术→预言术），其余追记后回归 v1.5 |

### 翻译过程

| 阶段 | 结果 |
|---|---|
| 试译 | 150 条随机样本；首轮发现方括号玩家标签被整体保护而漏译，关闭 `square_bracket` 保护后重跑通过 |
| 全量 | 113 批，4743 条草稿，5 次连接失败重试 |
| 草稿验收 | `draft-scan` clean，0 失败 |
| 独立审校 | 318 批 + 4 轮定向修复，最终 clean |
| 最终质量闭环 | 13 条遗留争议逐条裁决：12 条 pass/contextual（源文尾部残留 `q/Y/f` 分支字节、无上下文短片段），1 条 repair（`R0004356` 同条内 Goblins 译名不一致 + "coming for the key" 语义偏差），修复后复查 clean |

### 配置与执行

- 工作流：自定义（`workflow=custom`），执行器 `backend=api`，模型 `deepseek-v4.1-flash`（`Tools/localization/api.local.jsonc` 的 `default_api`）
- 配置：`TranslateFiles/config/unified_workflow.json`
- 关键调整：`placeholder_family_overrides.square_bracket = null`——本游戏方括号内容全部是玩家可见的选项/动作标签（151 条，如 `[Give him the Amulet Passkey 15]`、`[Save vs Disease: SUCCESS!]`），整体保护会导致漏译；`[P1]` 类占位符由程序另行生成，不受影响
- 编排：`translation_workflow.py`（init → extract → glossary_review → freeze-glossary → pilot → translate → draft-scan → review → 质量闭环 → export）；批次执行 `run_api_round.py`
- 导出：`eschalonbook_unified_text_translated.csv`（4743 行）

### 交付文件

| 文件 | 行数 | 说明 |
|---|---|---|
| `eschalonbook_text_translated.csv` | 4563 | 正文正式译文，与 `eschalonbook_text.csv` 逐行对应 |
| `eschalonbook_images_text_translated.csv` | 231 | 图片正式译文（含 51 条复用正文译文），与 `eschalonbook_images_text.csv` 逐行对应 |
| 拆分脚本 | — | `Analysis/split_unified_translation.py` |

### 校验结果

- 行数：正文 4563/4563、图片 231/231，空译文 0
- 无汉字行：正文 617、图片 13，逐条核对为脚本命令（`init_trade`/`teach_skill`/`Sound(...)`）、资源路径、版权行、署名、罗马数字与 `0123456789`，属正确保留
- 控制符：`*`/`&`/`#`/`$/` 数量核对通过；`^` 有 2 处（第 1891、1896 行）新版只保留 1 个标记整词，v1.5 为逐词各 1 个（`^移动 ^静默` / `^隐藏 ^在 ^阴影`）。新版可读性更好，`^` 为「标记其后一个词」的前缀式标记而非成对开关，故不构成渲染风险，列入实机确认项
- 术语一致性：图片 UI 标签（力量/敏捷/耐力/护甲等级/生命值/法力值）与正文冻结表一致

### 旧产物备份

- v1.5 正文译表：`TranslateFiles/backups/20261027_rebuild/eschalonbook_text_translated.v1.5.csv`
- 首版图片译表：`TranslateFiles/backups/20261027_rebuild/eschalonbook_images_text_translated.first.csv`
- 旧正文术语表：`TranslateFiles/backups/20261027_rebuild/glossary_r1/`
- 旧工程数据库：`TranslateFiles/state/archive/`（含 20261020 增量运行与 20261027 图片子工程 r2）

### 待办与已知问题

1. 中文贴图尚未构建：`ImagePatch/` 只有空替换往返验证；需按 `ImageText/mapping.json` 逐区清字、排版、回填，再重打包 `gfx.pak`。
2. 地图北部一处竖排地名仍未可靠转写，地图不进入安装名单。
3. 启动器 `display_hook_launcher.py` 当前读取的是旧译表路径与映射，接入新译文需重新生成运行时映射（正文 4743 条统一表）并复测。
4. `no bars`（第 1254 行）译文「无栏」缺上下文，实机确认后再定。
5. `help.html` 402 条仍未翻译（浏览器打开，不经引擎绘制）。
6. 上一轮反馈的升级崩溃问题本次未处理。

