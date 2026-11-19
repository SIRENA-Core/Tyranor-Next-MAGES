# Steins;Gate（Steam／PC 版）：`sg-pc` profile 与 SGHD 指令集

状态：**实验性，能进剧情，不能完整游玩。** 在 MuMu 模拟器（Android 15）上、用原版英文数据实测到：厂商 Logo → 标题画面（Press Enter）→ 主菜单 →
START → 序章（秋叶原车站，背景里的行人在动）→ 对话文字逐句显示。**没有验证**：真机、语音、BGM、音效、立绘（序章之后的内容）、日文版和汉化版数据。
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

另外几处要识别 S;G：`SelInit` 的存档点 id、`NameID` 的名牌标号、`MSinit` 清零大小、CC 标题菜单状态机的「按任意键」检测、三处背景滤色读取。

## 已知的缺口

- **没有存档系统**：`SaveDataType.None`。启动脚本把 `Save(4)`（读系统数据）的失败当致命错误，所以现在 `LoadSystemData` 对 SGHD 报告 OK（当作全新安装）。存档、读档、快速存档、已读标记都没有。
- 所有界面的**精灵坐标**：标题已经按 `TITLE_CHIP.DDS` 量过（背景 1920x1080 在 (0,0)；主菜单项成对放在 x=1922／2123；子菜单项 249x37 在 x=1957／2245；橙色指针；「Press Enter」）。
  菜单项在屏幕上的位置是我估的，没有 Windows 版的原图对照。对话框用了 `DATA01` 里量出的 ADV 框。存档图标、读盘中、日期、系统消息框、选项、日志、TIPS、系统菜单、名牌、等待图标目前都指向透明块（占位）。
- 对话里人名的位置不对（序章的 `???` 出现在右下）。
- 视频是 Bink 2，FFmpeg 不解；脚本里的片头／过场会在日志里报 `Failed to open movie`，目前不阻塞。
- `ClickOnJump`（Logo 期间点击跳过）是桩。
- 简体中文汉化过的 `script.mpk` 让 sc3ntist 抛 `End of expression expected`（汉化补丁改过脚本），没有在引擎里测过。

## 接入（Tyranor Next）

宿主已接受 profile `sg-pc`（`ImpactoRequest.PROFILES`、`engine/impacto/profiles.json`）。游戏目录是含 `Game.exe` 的那一层（宿主在 `gamedata/sg-pc` 建符号链接，档案按 `USRDIR/*.mpk` 找）。
主应用的目录检测（`Game.exe` 加 `USRDIR/script.mpk`、`USRDIR/system.mpk`）在另一个仓库，还没有做。

## 复现工具

- `tools/impacto/sghd/mpk_tool.py`：列出／解出 MPK v2 里的文件（读你自己的游戏文件，不含游戏内容）。
- 参考反汇编器：sc3ntist（`src/SCXParser.cpp` 加 `src/parser/*.cpp`，`g++ -std=c++17`）。它没有许可证文件，所以这里**不复制它的代码或表**，操作数形状是对着数据自己核对的。
