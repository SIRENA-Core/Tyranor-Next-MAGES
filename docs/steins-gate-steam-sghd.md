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
| `10:13`、`10:1A` | 同 CC（Option、Help） | 同 | profile 没有选项／帮助画面时，子菜单淡入后抬起 `SF_SUBMENUEXIT`（补丁 0023）；sg-pc 已有原版画面（补丁 0027、0028） |

标题画面是原版的（补丁 0029，`TitleMenuType.SGHD`，布局、动画、输入都取自原版 Game.exe）：菜单在右侧，LOAD／EXTRA 打开子列表，选中的项闪烁 64 帧后才告诉脚本；脚本的编号是 0 START、10 QUICK LOAD、11 LOAD、20 CLEAR LIST、21 CG LIBRARY、22 SOUND、23 MOVIE、24 TIPS、30 CONFIG、40 HELP（EXTRA 在标志 860 设置后有五项，否则只有 CLEAR LIST 和 TIPS）。原版标题上的卫星是 Bink 2 视频，本引擎不能播放。CLEAR LIST、CG LIBRARY 的画面还没有（只能按返回退出）；TIPS 见补丁 0032。

另外几处要识别 S;G：`SelInit` 的存档点 id、`NameID` 的名牌标号、`MSinit` 清零大小、CC 标题菜单状态机的「按任意键」检测、三处背景滤色读取。

## 已知的缺口

- **存档**：用 `SaveDataType.MO6TWPC`（S;G 的脚本用的是 Chaos;Child 风格的存档协议和 CC 的 ScrWork／标志位布局，memo06 PC 的存档实现已经按这套写好；自己的文件格式，不兼容 Steam 的存档）。
  已验证存一格、读一格（缩略图、游玩时间、日期、确认框）；快速读档画面能打开（QLOADMENU，列出快速存档）、按返回能退出，从里面读档没有走完；已读标记走同一套实现，没有单独验证。
  存档画面的格子布局（每页 8 格、卡片、缩略图）已按原版 Game.exe 改（补丁 0025）；格子里的文字位置、锁图标、PREV／NEXT（隐形的点击区，原版是 y 934 的页签）、页码文字仍是估的：这些图集里没有卡片、高亮和按钮的美术。从系统菜单打开的存档／读档／快速读档画面按返回能退出（补丁 0023：`10:3F` 类型 4 清掉 `SW_SYSSUBMENUALPHA`，见下面的指令表）。
- **系统菜单**：十二个入口里 BACK LOG、CLOSE MENU 可用，SAVE／LOAD／QUICK SAVE／QUICK LOAD 走存档；CONFIG 是原版的三页画面（补丁 0027，数据全部取自原版 Game.exe）；HELP 是原版的两页说明画面（补丁 0028，图取 `manual.mpk`，页码、页签、按键提示和动画取自原版 Game.exe）；RETURN TITLE、EXIT GAME 的确认框是原版的（补丁 0030；EXIT GAME 用原版的第二个、全局消息框，屏幕变暗）；TIPS LIST 是原版的画面（补丁 0032，含 TIPS 数据的读取与解锁），FULL SCREEN 在这里没有意义；
  相册等附加内容还没有。系统菜单的面板、图标、文字位置和滑出动画已按原版 Game.exe 改（补丁 0026）；原版对不可用项的暗色图标还没有。
- 其余界面的**精灵坐标**：标题、系统菜单、存档格子、CONFIG、HELP、系统消息框、TIPS 已按原版 Game.exe 的绘制代码做（补丁 0025–0030、0032）。对话框用了 `DATA01` 里量出的 ADV 框；日志用了量出的 `BACKLOG.DDS`（面板与「BACKLOG」标题 x 0..1790，滚动条轨道 x 1790..1823，滑块 (1940,58)，语音图标 (1974,6)；这张图没有高亮条和操作提示，用透明块占位），还没有和原版对照。存档图标、读盘中、日期、等待图标目前都指向透明块（占位）。
- 日志的背景是一整张渐变图，引擎按 CC 的做法让它随滚动平铺，所以滚动时在平铺接缝处会有一道暗度跳变。
- 人名固定在对话框右下（`SetMesModeFormat` 的名字显示模式是「固定位置、居中」，坐标按 1.5 倍放大后落在 (1620,1011)），这是脚本的设计，不是排版错误；没有与原版画面对照。名牌美术没有。
- **手机**（补丁 0033–0037）：按原版 Game.exe 做出来，见下面「手机」一节。
- **视频**：`USRDIR/movie/1920x1080` 里 13 个是 Bink 1（片头、序章、结局、`ar`、`imv005`／`041`／`042`），FFmpeg 能播；另外 24 个是 Bink 2（`IMV*` 的世界线变动辉光管动画、`title`、`timeleapbg` 等），FFmpeg 没有 Bink 2 解码器，引擎会跳过它们（不阻塞脚本）。用 `tools/impacto/sghd/convert_bink2.py` 转换后就能播，见「复现工具」。
- 时间跳跃的日期计数动画（`10:3A`，原版 0x41a140）还没画，只读操作数并按原版的长度结束。
- `ClickOnJump`（`00:53`；sc3ntist 叫它 `Useless0053`）是桩，S;G 只在 Logo 画面用它（`arg1` 1、`arg2` 80），Logo 也能被同一循环里的 `KeyOnJump` 跳过，所以不影响操作；`sysse`（系统音效）没有挂载，日志里会报找不到音频。
- 简体中文汉化（2018 年的汉化补丁：`script.mpk`、`system.mpk`、`bg.mpk`、`manual.mpk`）在 MuMu 上从第 6 章玩到第 10 章：文字、手机邮件、存档确认框都是中文。汉化字体只替换了汉字格子；汉化的 `CLEARLIST`／`CONFIG`／`DATA01`／`MOVMENU` 是同尺寸的 PNG（扩展名仍是 `.DDS`），引擎按内容识别。英文数据存的档能在汉化数据下读。

## 手机

- 逻辑：原版手机主例程 0x453800 与各画面例程；`10:37` 的各类型（邮件状态位的设置与跳转、可通话／可发邮件的联系人、邮件表、模式切换）、`10:38`（附件的文本页）。邮件状态每封 5 位：0 收到、1 已读、2 可回复、3 有附件、4 已回复。
- 剧情分歧靠手机：各章结尾只在几句台词里允许发送准备好的邮件（标志 2602）或给登记的联系人打电话（`10:37` 类型 0x14，标志 2603；打通后标志 2614），错过就进角色结局（第 6 章铃羽、第 7 章菲莉丝、第 8 章琉华）。第 10 章的走向由章节脚本 `MAIN00` 用 `10:37` 类型 2 检查：邮件 334 已读才进牧濑线，邮件 386 已回复才进真结局线。和原版一样，「全部快进」会跳过这些机会。
- 打开：剧情里按手机键（Z、L2，宿主屏幕按键第一页），或点左上角的小手机（原版的鼠标模式，0x434d40；有新邮件时闪烁，0x45a9a0）。点击区来自原版的表 0x52ea58。

## 通用化：S;G 复用了哪些类

S;G 的系统菜单、存档画面复用 memo06 PC 已经在用的类，profile 指向原版的美术和布局：
`SystemMenuType.MO6TW`（跟随 `SW_SYSMENUALPHA`、写 `SW_SYSMENUCNO`，S;G 脚本用的正是 2143／3338）、`SaveMenuType.MO6TWPC` + `SaveDataType.MO6TWPC`。
标题、CONFIG、HELP、系统消息框的行为和 memo06／CC 的类差得多，按原版 Game.exe 写成了新的通用类（`TitleMenuType.SGHD`、`OptionsMenuType.SGHD`、`HelpMenuType.SGHD`、`SysMesBoxType.SGHD`，布局全部在 profile 里）。
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
- `tools/impacto/sghd/convert_bink2.py`（Windows）：`python convert_bink2.py <游戏目录> USRDIR/movie/1920x1080 <输出目录>`。视频用你游戏目录里的 `bink2w32.dll` 解码（先用 `bink2dump/build.bat` 以 Visual Studio Build Tools 编出 32 位的 `bink2dump.exe`），音频由 ffmpeg 直接从 `.bk2` 读（Bink 音频它支持），编码成 H.264／AAC 的 MP4，文件名不变；把输出的文件替换进手机上游戏的 `USRDIR/movie/1920x1080`（先备份原文件）。需要 PATH 里有带 libx264 的 ffmpeg。
- `tools/impacto/sghd/import_steam_save.py`：`python -I import_steam_save.py <SAVEDATA.DAT> <Game.exe> <SYSTEM.DAT> <输出>`，把 Steam 版存档的系统数据并入 `sg-pc` 的 `SYSTEM.DAT`。Steam 存档的布局取自原版 0x45cf90 起：系统块 0x3820 字节（标志 800–1199、3680–3999，ScrWork 1600–2099，CG 标志 1200 位，BGM 100 字节，已读标记 10000 字节，附加数据 0x400），后面是两块各 0x3b97c0 字节的存档格；已读标记按 `Game.exe` 里 0x52c9d8 的「每个脚本的（句数，起始位）」表换算成引擎的（脚本，句）。存档格不转换。
- 参考反汇编器：sc3ntist（`src/SCXParser.cpp` 加 `src/parser/*.cpp`，`g++ -std=c++17`）。它没有许可证文件，所以这里**不复制它的代码或表**，操作数形状是对着数据自己核对的。

## 从原版 Game.exe 取界面数据

界面不自己设计，数值从原版程序里读：Steam 版 `Game.exe` 的代码没有加壳（CoZ 补丁的 `gamedef.json` 特征码能定位原版的原生函数：
绘制精灵 0x432230、绘制矩形 0x42f890、手机文字 0x444f70、点击判定 0x433040、原生指令表等），用 `objdump` 反汇编后逐个还原
绘制调用的参数（图集上的哪一块画到屏幕哪里；原版按 1280x720 计算，乘 1.5 绘制）。点击区域在 `.data` 里是
`{65535, 0, x, y, w, h, 组, id}` 的记录表。已经用这个方法替换的：存档／读档画面（0025）、系统菜单（0026）。
