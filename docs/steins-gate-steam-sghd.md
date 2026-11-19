# Steins;Gate（Steam／PC 版）：`sg-pc` profile 与 SGHD 指令集

状态：**实验性，能进剧情并读下去、能存档读档，不能完整游玩。** 在 MuMu 模拟器（Android 15）上、用原版英文数据实测到：厂商 Logo → 标题画面（Press Enter）→ 主菜单 →
START → 序章：秋叶原车站、7F、天台、讲座会场的背景，椎名真由理与牧濑红莉栖的立绘和 CG，背景里行人在动；对话逐句显示、字形与间距正确、按词换行；
向下轻扫（或鼠标滚轮向下、屏幕按键的 `Ins`）打开日志（BACKLOG：章节标题、人名、台词、语音图标、滚动条）；菜单键（`1`）打开系统菜单（十二个图标，聚焦的那一行显示名称），
BACK LOG、CLOSE MENU 可用；SAVE 画面存一格后显示缩略图、游玩时间和日期，LOAD 画面选格后弹出确认框，确认后回到存档的那一句。连续点按约 450 次读过序章前半，没有崩溃。
**没有验证**：真机、语音／BGM／音效的实际播放、日文版和汉化版数据、序章之后的内容（电话触发、分支）。
Tyranor Next 主应用目前**不识别**这个游戏的目录（需要主应用一侧加一条检测，见下文「接入」）。

## 这个游戏是什么

- Steam 上的 *STEINS;GATE*（MAGES.，2016，AppID 412830），不是 2009 年的原版 PC 版，也不是 PS3 版。
  目录：根目录 `Game.exe`、`Launcher.exe`、`steam_api.dll`……，数据在 `USRDIR/*.mpk`（`script`、`system`、`bg`、`chara`、`bgm`、`se`、`voice`、`mask`、`shader`、`mgsshader`、`manual`）和 `USRDIR/movie/`（Bink 2 的 `.bk2`）。
- 档案是 MAGES. 的 **MPK v2**，impacto 的 `MpkArchive` 已能读（头 `MPK\0`，版本 2.0，目录从 `0x40` 起每项 `0x100` 字节）。
- 素材：背景 1920x1080 PNG；立绘 PNG 加 `.lay`；`system.mpk` 里原版的图集是 DXT5 的 `.DDS`（汉化过的版本里有的 `.DDS` 其实是 PNG）；语音、BGM、音效是 OGG；字体 `FONT.PNG`／`FONT2.PNG` 是 3072x6000、每格 48 像素的 64x125 网格。

## 结论：它和 Chaos;Child（PC）是同一代引擎

最初我按脚本反汇编里的指令名（CoZ 的 sc3ntist 里 `SGHDDisassembler` 的命名）判断它「与 impacto 的任何指令集都不同」，**这个判断是错的**。把脚本里的 `GlobalVars`
编号和 impacto 的 Chaos;Child 变量表对照后发现：

- 启动脚本用 `GlobalVars[4400/4401/4402]` 做淡入遮罩，正好是 CC 的 `SW_MASK1COLOR/ALPHA/PRI`；`GlobalVars[4363]` 是 CC 的 `SW_MESMODE0`；`3333` 是 `SW_SAVEERRORCODE`；
  系统子菜单变量 `2147/2148/2149` 也与我们已经做过的 MO6TW PC 版一致。
- 按操作数形状逐个比较，约三分之二的操作码和 impacto 的 CC 表一致（对话指令 `Mes`／`MesMain`／`MessWindow` 的类型位都一样）。
- 字体图集和 CC 一样是 3072x6000 的 64 列网格。

所以做法是：新增 `InstructionSet::SGHD`（补丁「add the SGHD instruction set」），`opcodetables_sghd.h` 从 CC 表复制，只覆盖操作数或含义不同的几个操作码；
再用 `sg-pc` profile 把 CC 的标题菜单类等界面类接到 S;G 的图集上。

## 怎么发现哪些操作码不同

用与 impacto 无关的参考解码器（sc3ntist 的 `SCXParser`，独立命令行，g++ 可编，目录路径里不能有空格）把全部 190 个脚本反汇编，并让它打印每条指令的地址和长度；
再在 impacto 里开 `logLevel: trace`，每条执行的指令会打印 `Address / TID / Opcode / ScriptBuffer`。逐线程比较「引擎实际前进的字节数」和「参考解码器给出的指令长度」
（表达式语句 `0xFE` 不打印，算进间隙），任何不一致就是一个操作数形状不同的操作码。从启动一直跑到序章（约 23 万条指令）只剩两个需要处理的：

| 操作码 | S;G | CC | 处理 |
| --- | --- | --- | --- |
| `00:4C` | 类型字节，类型为 0 时一个表达式 | Dummy | 跳过操作数的桩 |
| `10:1B`、`10:3F` | 一个字节 | Dummy（Dummy 不前进，启动脚本在标题前执行 `10:3F`，线程直接挂死） | 跳过一个字节的桩 |
| `10:37` | 手机／邮件组，按类型有不同操作数 | MapSystem | 按类型跳过操作数的桩 |
| `10:38` | 类型字节，类型 0 时带一个标号 | Mtrg | 桩 |
| `10:33` 类型 0 | 两个标号 | 一个标号 | 与 MO8／CHN／MO6TWPC 同样处理 |
| `10:3F` | 一个字节：菜单打开／关闭信号（3/4 存读档、5/6 TIPS、17/18 系统菜单、21/22 选项、23/24 帮助） | 空 | 类型 4 清掉 `SW_SYSSUBMENUALPHA`（补丁 0023） |
| `10:13`、`10:1A` | 同 CC（Option、Help） | 同 | 子菜单淡入后抬起 `SF_SUBMENUEXIT`，因为还没有选项／帮助画面（补丁 0023） |

标题菜单用 CC 的类，但 S;G 标题脚本的编号不同（0 START、10 QUICK LOAD、11 LOAD、20 CLEAR LIST、21 CG LIBRARY、22 SOUND、23 MOVIE、24 TIPS、30 CONFIG、40 HELP），profile 用补丁 0024 的可选字段设置；EXTRA 里 SOUND／MOVIE 两项 CC 的类没有按钮，CLEAR LIST、CG LIBRARY 的画面还没有（只能按返回退出）。

另外几处要识别 S;G：`SelInit` 的存档点 id、`NameID` 的名牌标号、`MSinit` 清零大小、CC 标题菜单状态机的「按任意键」检测、三处背景滤色读取。

## 已知的缺口

- **存档**：用 `SaveDataType.MO6TWPC`（S;G 的脚本用的是 Chaos;Child 风格的存档协议和 CC 的 ScrWork／标志位布局，memo06 PC 的存档实现已经按这套写好；自己的文件格式，不兼容 Steam 的存档）。
  已验证存一格、读一格（缩略图、游玩时间、日期、确认框）；快速读档画面能打开（QLOADMENU，列出快速存档）、按返回能退出，从里面读档没有走完；已读标记走同一套实现，没有单独验证。
  存档画面的格子布局、PREV／NEXT（隐形的点击区）、页码文字是估的：这些图集里没有卡片、高亮和按钮的美术。从系统菜单打开的存档／读档／快速读档画面按返回能退出（补丁 0023：`10:3F` 类型 4 清掉 `SW_SYSSUBMENUALPHA`，见下面的指令表）。
- **系统菜单**：十二个入口里 BACK LOG、CLOSE MENU 可用，SAVE／LOAD／QUICK SAVE／QUICK LOAD 走存档；CONFIG、HELP 没有画面，选中后直接回到菜单（补丁 0023 的兜底，免得卡在看不见的画面后面）；TIPS LIST、FULL SCREEN、RETURN TITLE、EXIT GAME 的界面还没有（TIPS 只能按返回退出；选项图集 `CONFIG.DDS` 是 3072x2048，三页：基本／文字、声音、各角色语音，还没有量）；
  手机（`10:37` 组只是跳过操作数的桩，电话／邮件触发点会走不通）、相册等也没有。面板位置（屏幕左缘）是估的，没有原版画面对照。
- 其余界面的**精灵坐标**：标题已经按 `TITLE_CHIP.DDS` 量过（背景 1920x1080 在 (0,0)；主菜单项成对放在 x=1922／2123；子菜单项 249x37 在 x=1957／2245；橙色指针；「Press Enter」）。
  菜单项在屏幕上的位置是我估的，没有 Windows 版的原图对照。对话框用了 `DATA01` 里量出的 ADV 框；日志用了量出的 `BACKLOG.DDS`（面板与「BACKLOG」标题 x 0..1790，滚动条轨道 x 1790..1823，滑块 (1940,58)，语音图标 (1974,6)；这张图没有高亮条和操作提示，用透明块占位）。存档图标、读盘中、日期、系统消息框、选项、TIPS、系统菜单、等待图标目前都指向透明块（占位）。
- 日志的背景是一整张渐变图，引擎按 CC 的做法让它随滚动平铺，所以滚动时在平铺接缝处会有一道暗度跳变。
- 人名固定在对话框右下（`SetMesModeFormat` 的名字显示模式是「固定位置、居中」，坐标按 1.5 倍放大后落在 (1620,1011)），这是脚本的设计，不是排版错误；没有与原版画面对照。名牌美术没有。
- 视频是 Bink 2，FFmpeg 不解；脚本里的片头／过场会在日志里报 `Failed to open movie`，目前不阻塞。
- `ClickOnJump`（`00:53`；sc3ntist 叫它 `Useless0053`）是桩，S;G 只在 Logo 画面用它（`arg1` 1、`arg2` 80），Logo 也能被同一循环里的 `KeyOnJump` 跳过，所以不影响操作；`sysse`（系统音效）没有挂载，日志里会报找不到音频。
- 简体中文汉化过的 `script.mpk` 让 sc3ntist 抛 `End of expression expected`（汉化补丁改过脚本），没有在引擎里测过。

## 通用化：S;G 复用了哪些类

S;G 的系统菜单、存档画面、系统消息框都没有写 S;G 专用的 C++，只是 profile 指向正确的美术，复用 memo06 PC 已经在用的类：
`SystemMenuType.MO6TW`（跟随 `SW_SYSMENUALPHA`、写 `SW_SYSMENUCNO`，S;G 脚本用的正是 2143／3338）、`SaveMenuType.MO6TWPC` + `SaveDataType.MO6TWPC`、`SysMesBoxType.MO6TW`。
为此补了两处向后兼容的通用扩展：MO6TW 系统菜单现在认 `MenuEntriesHighlightedSprites`（每个入口各有一个聚焦时的精灵，hover 区域覆盖两张）；MO6TWPC 存档菜单认可选的
`SaveBackgroundSprite`／`LoadBackgroundSprite`／`QuickLoadBackgroundSprite`（三个画面各有一张背景）。memo06 PC 的 profile 不设这些字段，行为不变。

## 字体、换行与日志的几个细节

- 引擎的 `font.lua` 一开始沿用了 CC 的字宽表，但它描述的是另一套字体：圆形的拉丁字母（`o`、`O`、`?`）右边被裁掉。S;G 的 `FONT.PNG` 是 3072x6000、64x125 个 48 像素格子；
  拉丁字母有两份（第 0–1 行 id 1..62，和 127 个 id 之后的第 2–3 行 id 128..189，脚本用的是后一份），都是比例字体、左对齐。`tools/impacto/sghd/gen_widths.py`
  读你自己提取的 `FONT.PNG`，按墨迹右边缘加 3 像素给 id 1..226 生成字宽（空格 16，其余 48），写成 `profiles/sg-pc/font-widths.lua`。
- 引擎只在「非字母」处断行；`charset.lua` 里把两份拉丁字母和数字标成 `Alphabet`，否则单词会从中间断开（`asph|alt`）。
- 日志：S;G 的脚本通过 `MesRev`（`Unk0110` 的模式 0..5）和系统循环里对 `PADcustom[12]` 的 `KeyOnJump` 轮询来打开日志，而引擎的向下轻扫只合成 F2 键，
  所以 `UpdatePADInput` 在 SGHD 下对向下轻扫／滚轮另外抬起 `PADcustom[12]`；`InstMesRev` 的显示／隐藏原来只对 MO6TW／MO6TWPC 调用，现在 SGHD 也调用。

## 接入（Tyranor Next）

宿主已接受 profile `sg-pc`（`ImpactoRequest.PROFILES`、`engine/impacto/profiles.json`）。游戏目录是含 `Game.exe` 的那一层（宿主在 `gamedata/sg-pc` 建符号链接，档案按 `USRDIR/*.mpk` 找）。
主应用的目录检测（`Game.exe` 加 `USRDIR/script.mpk`、`USRDIR/system.mpk`）在另一个仓库，还没有做。

## 复现工具

- `tools/impacto/sghd/mpk_tool.py`：列出／解出 MPK v2 里的文件（读你自己的游戏文件，不含游戏内容）。
- `tools/impacto/sghd/gen_widths.py`：从你自己提取的 `FONT.PNG` 生成 `profiles/sg-pc/font-widths.lua`（见上）。
- 参考反汇编器：sc3ntist（`src/SCXParser.cpp` 加 `src/parser/*.cpp`，`g++ -std=c++17`）。它没有许可证文件，所以这里**不复制它的代码或表**，操作数形状是对着数据自己核对的。
