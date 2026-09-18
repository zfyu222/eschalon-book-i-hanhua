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
| 翻译 | AiNiee / DeepSeek | - |
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

## 2026-07-26 弹窗文本回填补充

- 诊断确认露营说明、水井确认等文本已经存在于统一 CSV，并非提取或翻译遗漏。
- 此类界面使用独立的逐词排版器 `sub_4C4982`（VA `0x4C4982`），与消息日志的 `sub_4BDEB8` 不同。
- `display_hook_launcher.py` 已在 `sub_4C4982` 入口替换完整正文参数，再由游戏原生逻辑处理 `^`、`&` 样式标记和中文换行。
- 该 Hook 是同类弹窗的通用入口，不需要为每个场景收集或添加运行时碎片。

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
- 百度网盘：`/Hanhua/EschalonBook/Eschalon Book I_子非鱼汉化1.0.zip`

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
- 百度网盘：`/Hanhua/EschalonBook/Eschalon Book I_子非鱼汉化1.1.zip`

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
- 百度网盘：`/Hanhua/EschalonBook/Eschalon Book I_子非鱼汉化1.2.zip`

## 2026-09-19 发布启动根因修复

- 开发脚本实际从完整的 `Eschalon_CN/` 副本启动，该目录同时包含 `gfx.pak`、`data/config/music/sound` 和 `steam_appid.txt`。
- v1.1/v1.2 为绕开误判的目录权限问题，只把游戏 EXE 复制到 `%LOCALAPPDATA%`；这先后触发 Steam 应用身份错误和 `gfx.pak missing`。
- 最终确认真正差异是 `steam_appid.txt`，而不是 Program Files 本身：在原 Steam 游戏目录写入 App ID `25600` 后，可以直接挂起启动原 EXE，Frida 注入、字体加载和显示 Hook 全部成功。
- 新启动器不再默认复制游戏 EXE，而是确保游戏根目录存在 `steam_appid.txt`，始终从包含完整资源的原目录启动。
- 冻结版实测：进程路径保持为 Steam 原目录，窗口进入 `Launch Menu`，未出现 Steam Error 或 `gfx.pak missing`；临时运行目录未被使用。
