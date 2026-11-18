# Steins;Gate（Steam／PC 版）与 impacto 的差距分析

状态：**分析，不是支持。** 宿主目前**不能**运行这个游戏，也没有对应的 profile。本文记录 2026-11 对一份真实游戏目录的调查结果，
说明为什么它不是「再加一个 profile」就能解决的，以及如果要做，应该怎么分步走。结论都来自对游戏文件的实际解析，没有靠猜；
没有验证的地方会写明。

## 这个游戏是什么

- Steam 上的 *STEINS;GATE*（MAGES.，2016，Steam AppID 412830），不是 2009 年的原版 PC 版，也不是 PS3 版。
  目录布局：根目录 `Game.exe`、`Launcher.exe`、`steam_api.dll` 等，数据在 `USRDIR/*.mpk`（`bg`、`bgm`、`chara`、`mask`、`script`、`se`、`system`、`voice`、`shader`、`mgsshader`、`manual`）和 `USRDIR/movie/`。
- 与已支持的 `mo6tw-pc*` 完全不同：后者是 CRI `.cpk` 加 `data/` 目录，前者是 MAGES. 自己的 **MPK v2** 档案。
  impacto 的 `MpkArchive` 已经能读 v2（头 `MPK\0`，版本 2.0，目录从 `0x40` 起每项 `0x100` 字节，压缩类型 0／1），所以**档案层不是问题**。

## 档案与素材

| 档案 | 内容（抽样） | 备注 |
| --- | --- | --- |
| `script.mpk`（190 个文件） | `_STARTUP_WIN.SCX`（档案内编号 2，起始脚本）、`_SYSTEM`、`_TIPS`、`_ATCH`、`_MAIL`、`MACROSYS`、`MACROSYS2`、`SGxx_yy.SCX` | SC3 格式（魔数 `SC3\0`，`[4]` 字符串表偏移，`[8]` 返回表偏移，标号表从 `+12` 起） |
| `bg.mpk`（507） | `BG01A.PNG` 等，1920x1080 PNG | |
| `chara.mpk`（330） | `CRS_ALA.png` + `CRS_ALA_.lay` | 立绘 PNG 加 `.lay` |
| `system.mpk`（32） | `DATA01.DDS`、`FONT.PNG`、`TITLE_CHIP.DDS`…… | **扩展名是 `.DDS`，但 `DATA01.DDS` 实际是 3072x1788 的 PNG**；`DATA03.DDS`、`GSYSMES.DDS` 等才是真 DDS（A8R8G8B8）。图集里没有任何精灵坐标信息 |
| `voice.mpk`（14512） / `bgm.mpk` / `se.mpk` | `.OGG` | impacto 已能播 |
| `movie/` | `.bk2`（Bink 2） | FFmpeg 不解 Bink 2，视频要关（`videoPlayback=false`） |
| `shader.mpk`、`mgsshader.mpk` | `.cg` 着色器 | 原版用，impacto 不用 |

设计分辨率是 1920x1080（背景、图集都是 PS3 版 1280x720 的 1.5 倍）。

## 为什么不是「加个 profile」：指令集不同

impacto 的指令集表（`src/vm/opcodetables_*.h`）覆盖 CHLCC、CC、MO6TW、MO7、MO8、CHN、RNE、Dash、Darling、LCCSwitch、SGPS3 以及我们加的 MO6TWPC。
这个游戏用的是另一代：CoZ 的 [sc3ntist](https://github.com/CommitteeOfZero/sc3ntist) 里的 `SGHDDisassembler`（SGHD = Steins;Gate HD）。它和 Steins;Gate 0（PC）同一代，
[compendium](https://github.com/CommitteeOfZero/compendium) 的 `scripting/` 描述的就是这一代的脚本引擎。

用 sc3ntist 的 `SCXParser`（独立命令行，g++ 可编，不需要 Qt）反汇编了全部 190 个脚本：

- 一共 **252 404 条指令，151 种指令名**；sc3ntist 自己的解码器对 284 处标「未识别」（集中在 `MACROSYS`／`MACROSYS2`）。
- 三个指令组：`00`（系统）、`01`（图形）、`10`（用户），与 impacto 一样；但组内的操作码含义**全部不同**。例如 `01:00 CreateSurface`、`01:02 LoadTexture`、`01:0C GroupLoadDialogue`、`01:0D GroupDisplayDialogue`、
  `10:01 LoadBackground`、`10:05 LoadCharacter`、`10:37 Group1037`（一个带十几个子类型的特效组）。
- 对话不是 `Mes*` 指令，而是 `ShowCurrentDialogueBox` → `ClearDialogueBox` → `LoadVoicedDialogue(audioId, animationId, characterId, line)` → `DisplayDialogue`（每句 5 条指令），
  文字带 `[name]…[line]…[%p]` 标记，字符集是 SGHD 自己的（`SGHDCharset`）。
- 出现频率最高的指令：`DisplayDialogue`／`ShowCurrentDialogueBox`／`ClearDialogueBox`／`Checkpoint00`（各约 3.07 万）、`CallFar`（2.19 万）、`LoadDialogue`（1.6 万）、`LoadVoicedDialogue`（1.4 万）、`ResetFlag`（1.06 万）、`LoadCharacter`（5563）、`LoadBackground`（2137）。

impacto 里最接近的 `SGPS3` 表是 PS3 版的方言，且 765 项里 602 项是 `InstDummy`（上游自己也没做完，`sgps3` profile 还是照着 CHLCC 抄的占位，没注册进 `gamedefinitions.lua`）。

## 为什么更难：原生一侧是写死的

脚本只是状态机：`GlobalVars[n]` 在引擎里就是 `ScrWork[n]`，`FlagRef(n)` 是标志；图形由 Game.exe 读这些变量来画。
- 贴图通过 `LoadTexture(surfaceId, archiveId, fileId)` 绑到**表面编号**，之后 UI 怎么用哪个表面、哪块区域，全写在 Game.exe 里；数据里没有精灵表。
- 标题、系统菜单、存档、日志、TIPS、手机界面、各种提示框的布局与逻辑都是原生实现，需要自己从图集量坐标、从脚本推行为。
- 脚本里大量 `GlobalVars[4400..4402]` 之类的变量就是在驱动渐变、位置、遮罩；没有变量名表，要靠读 `MACROSYS` 推断。
- 内嵌 `.sdb`、`BGMASK00..29`、`WAVTABLE.DAT`（口型）等格式在 Game.exe 里出现，impacto 没有对应实现。

## 建议的分步路线（没有做）

1. **只让虚拟机跑起来**：新增 `InstructionSet::SGHD` 与表 `opcodetables_sghd.h`（只加新文件，对上游文件只改 `vm.h`／`vm.cpp`／`CMakeLists.txt` 各一处），
   操作数形状直接照 sc3ntist 的解码器（它已验证过 190 个脚本），先把每条指令按形状正确跳过并记日志，保证 `_STARTUP_WIN` → 标题循环不跑偏。
2. **能看到内容**：`LoadBackground`、`LoadCharacter`、对话五件套、`PlayBgm`／`PlaySoundEffect`／`PlayVoice`，用最朴素的对话框和固定位置先出画面和声音。
3. **标题与系统菜单**：按图集量坐标。
4. 之后才是存档、日志、TIPS、手机、特效组 `Group1037`。

补丁系列的原则不变：新增文件为主，对上游已有文件只做小而集中的改动，这样上游升级时基本不冲突。

## 复现这份分析的工具链

不含任何游戏内容，只有读你自己文件的脚本：

- `tools/impacto/sghd/mpk_tool.py`：列出／解出 MPK v2 档案里的文件。
- `sc3ntist` 的 `src/SCXParser.cpp` 加 `src/parser/*.cpp`，`g++ -std=c++17` 直接编；它从标准输入读「脚本目录」和「游戏名（`SGHD`）」，在每个 `.SCX` 旁写 `.txt`。目录路径里不能有空格。
- 简体中文汉化补丁过的 `script.mpk` 会让 sc3ntist 抛 `End of expression expected`（汉化补丁改过脚本），日文／英文原版 `script_bak.mpk` 可以完整反汇编。

## 没有验证的

- 没有在设备上跑过任何 SGHD 相关代码；以上全是静态分析。
- 没有查过 Game.exe 里的原生实现细节，也没有运行 Windows 版做对照。
- 工作量只是估计：第 1、2 步是以天计的，第 3 步以后是以周计的。
