# STEINS;GATE 0（Steam 版）适配记录（`sg0-pc`，已适配）

`sg0-pc` 是 Steam 版 STEINS;GATE 0 的 profile。它和 Steam 版 STEINS;GATE（`sg-pc`，见 [`steins-gate-steam-sghd.md`](steins-gate-steam-sghd.md)）是同一代引擎，大部分适配直接沿用前作。宿主 0.4.4 起**已适配**：标题、剧情（序章、β 世界线，B 线快进到结局）；手机和 RINE、右键系统菜单、存读档、CONFIG、BACKLOG、TIPS、系统消息框、EXTRA（CLEAR LIST、CG／SOUND／MOVIE 鉴赏）都已按原版移植。主应用从宿主 versionCode 11（0.4.4）起识别它。

## 游戏目录

```
Game.exe
USRDIR/script.mpk  system.mpk  bg.mpk  chara.mpk  bgm.mpk  se.mpk  voice.mpk  mask.mpk  manual.mpk  mpk_bg.lst
USRDIR/movie/1920x1080/*.bk2
```

识别规则（`engine/impacto/profiles.json`）：`Game.exe`、`USRDIR/script.mpk`、`USRDIR/system.mpk`、`USRDIR/mpk_bg.lst`。前作 `sg-pc` 的规则同样能命中这个目录，所以 `sg-pc` 加了可选字段 `noneOf: ["USRDIR/mpk_bg.lst"]`（有这个文件就不是前作）。不认识 `noneOf` 的主应用会把 SG0 目录当作两个 profile 同时命中、不识别；主应用支持 `noneOf` 后才能正确识别 SG0。`test-profiles.py` 会检查任意两个不同游戏的规则不会同时命中同一个目录。

视频是 Bink 2，由内置的 libbink2 直接播放，不需要转换。

## 已移植（数据取自原版 Game.exe）

| 部分 | 来源 | 说明 |
| --- | --- | --- |
| 指令集 `InstructionSet::SG0` | 指令表 0xdcc198（系统）、0xdcbfb0（图形）、0xdcc320（用户 1） | 以 S;G 的 SGHD 表为基础；`00:53`–`00:59`（条件调用／跳转、鼠标和键盘跳转）按原版实现；`10:37`（手机／RINE）见下文；`10:38` 只读掉操作数 |
| 标题画面 | 0x45c1b0 及其调用的例程（主菜单 0x45bf90、CONTINUE 0x45ac90、EXTRA 0x45ba80／0x45b470、装饰 0x45b030、Logo 0x45be40、按下开始 0x45cbe0、输入 0x45c2f0） | "0" Logo 动画（`TITLE_LOGO1..3`，60 帧）、文字 Logo、装饰线和小方块、主菜单从右滑入并被两图之间的背景条遮住、子菜单先出指针再"擦开"；没有存档标志 860 时 EXTRA 不显示，下面的条目上移 |
| 对话框 | 0x45fca9 | `MESWIN` (0, 882) 1920×324，画在 (0, 756)，遮罩 (0, 1212) |
| 名字与名牌 | 0x45fd4b／0x45fda9、`_SYSTEM` 的文字模式 0 | 名字在对话框底部正中（以 `NamePos.x + MaxNameWidth / 2` 为中心），两侧是 `MESWIN` 的两笔橙色刷痕，随名字宽度展开 |
| 视频帧计数 | — | SG0 的剧本靠轮询 `SW_MOVIEFRAME`／`SW_MOVIETOTALFRAME` 等视频结束（如 `_STARTUP_WIN` 标签 47、`MACROSYS2` 标签 310），Bink 2 播放时设置这两个值 |

## 与原版不同、估计或没做的部分

- 短的 EXTRA 列表（标志 860 之前）在原版里两个点击区都登记在 y 519（0x45bcad、0x45bd7d），鼠标点不到 CLEAR LIST；这里用 CLEAR LIST 实际画出的位置 471。
- 标题模式 3 里按键说明例程（0x456940 类型 6）画的旋转装饰件没有移植。
- 标题和菜单的系统音效（`sysse` 挂载点）还没找到来源，`sg-pc` 同样没有。
- SOUND 鉴赏的曲目在引擎 BGM 通道上只播一遍，循环和“下一首”由鉴赏自己的逻辑处理（原版音频线程按循环点计数，这里没有移植）。
- MOVIE 鉴赏在触屏上第一次点击只选中条目，再点一次才播放。
- TIPS 画面的键盘 Enter／Esc 不起作用（触屏正常）。
- 标题子菜单在触屏上用返回键或双指轻点关不掉（`sg-pc` 同样，原来就有的问题）。
- 标题"按下开始"在模式 1 之前（剧本最多等 420 帧）不接受点击，和 `sg-pc` 一样要等提示稳定后再点。

## 验证

MuMu 模拟器（Android 15 x86_64，**不是真机**），Steam 原版数据加中文脚本，用调试模式（x64、强制快进、保存的状态）：

- 启动 Logo、intro 视频完整播放，标题、按下开始、菜单、NEW GAME（触摸）。
- 序章到 `SG0_B01_12` 连续推进：对话框、名字和名牌、立绘、背景、全屏 NVL 文字、世界线变动视频 `IMV001` 和章节标题视频 `TIT_B02`。
- 真机没有测试。

## 手机和 RINE

原版手机模块（Game.exe 0x46b600..0x478000，90 多个函数）不是逐个手写的，而是用 Ghidra 反编译后由 [`tools/impacto/sg0/translate_phone.py`](../tools/impacto/sg0/README.md) 机械翻译成 C++（引擎里的 `src/games/sg0/phonecode.cpp`，生成文件）。原版全局变量保留原地址，放在模拟内存里；它调用的引擎函数（绘图、文字排版、点击区域、旗标、输入）在 `phoneshim.cpp` 里实现；RINE 对话读取器直接读剧本字节，在 `phonerine.cpp` 里手写移植。

- 打开：消息窗左上角的手机按钮（点击或鼠标中键），对应原版的 PADcustom[22]。原版只在文字等待玩家时才允许打开（旗标 1611，由 MesMain 置位），这里也一样。
- 操作：点击等于鼠标左键，双指点击等于右键（返回／关闭），滚轮或拖动滚动聊天记录。
- RINE 回复：在 RINE 里点左右箭头切换候选句，点其他地方发送；之后每点一下显示下一条消息。
- 手机状态（0x3ee0 字节）跟着调试快照和正式存档保存（存档文件版本 3 的额外数据）。
- 已在 MuMu 模拟器上验证（不是真机）：主屏、RINE、设定、壁纸、剧情中的 Amadeus 画面，序章真由理的 RINE 从回复到对话结束、关闭手机后剧情继续。Amadeus 来电（CONNECT）在剧情里接通，手机里显示红莉栖。

## 系统画面

右键系统菜单、SAVE／LOAD、CONFIG、BACKLOG、TIPS、系统消息框和 EXTRA 各画面与手机一样，从 Ghidra 反编译机械翻译（`EXTRA_FUNCS` 列出入口），引擎侧的入口和桥接在 `sysmenu.cpp`、`savemenu.cpp`、`config.cpp`、`tips.cpp`：

| 指令 | 原版 | 说明 |
| --- | --- | --- |
| `00:44` | 0x482760 | 系统菜单（画面缩进显示器、12 个按钮） |
| `10:23` | 0x485f10 | SAVE／LOAD／QUICK LOAD，存档头取自引擎存档系统 |
| `10:13` | 0x4858c0 | CONFIG，设置在打开时从引擎读入、每帧写回 |
| `10:33` | 0x486540 | TIPS（`01:0E` 另存原版文字模式表给排版用） |
| `00:43` | 0x4824d0 | 系统消息框（确认框） |
| `10:21` | 0x485b80 | CLEAR LIST |
| `10:1F`／`10:1D`／`10:20` | 0x485b00／0x485aa0／0x485b40 | CG／SOUND／MOVIE 鉴赏；SOUND 通过原版 BGM 通道请求（0x2ed16e0）桥接到引擎 BGM 通道，MOVIE 画引擎的视频播放器 |

CG、BGM、TIPS 的解锁状态直接读写引擎 MO6TWPC 存档系统里的数据（`EvBytes`／`BgmBytes`／`TipsBits`），不另存一份。`sg0-pc` 打开了 `SaveData.WriteSystemDataOnBackground`：应用切到后台时写一次系统数据，被系统杀掉也不会丢。
