# STEINS;GATE 0（Steam 版）适配记录（`sg0-pc`，进行中）

`sg0-pc` 是 Steam 版 STEINS;GATE 0 的 profile。它和 Steam 版 STEINS;GATE（`sg-pc`，见 [`steins-gate-steam-sghd.md`](steins-gate-steam-sghd.md)）是同一代引擎，大部分适配直接沿用前作。**目前还在适配中**：能从标题开始新游戏，一直玩到第 1 章之后的 β 世界线前几章；手机（RINE）、存读档、设置、回想等画面还没做。启动器里是隐藏的。

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
| 指令集 `InstructionSet::SG0` | 指令表 0xdcc198（系统）、0xdcbfb0（图形）、0xdcc320（用户 1） | 以 S;G 的 SGHD 表为基础；`00:53`–`00:59`（条件调用／跳转、鼠标和键盘跳转）按原版实现；`10:37`、`10:38`（RINE／手机组）只读掉操作数 |
| 标题画面 | 0x45c1b0 及其调用的例程（主菜单 0x45bf90、CONTINUE 0x45ac90、EXTRA 0x45ba80／0x45b470、装饰 0x45b030、Logo 0x45be40、按下开始 0x45cbe0、输入 0x45c2f0） | "0" Logo 动画（`TITLE_LOGO1..3`，60 帧）、文字 Logo、装饰线和小方块、主菜单从右滑入并被两图之间的背景条遮住、子菜单先出指针再"擦开"；没有存档标志 860 时 EXTRA 不显示，下面的条目上移 |
| 对话框 | 0x45fca9 | `MESWIN` (0, 882) 1920×324，画在 (0, 756)，遮罩 (0, 1212) |
| 名字与名牌 | 0x45fd4b／0x45fda9、`_SYSTEM` 的文字模式 0 | 名字在对话框底部正中（以 `NamePos.x + MaxNameWidth / 2` 为中心），两侧是 `MESWIN` 的两笔橙色刷痕，随名字宽度展开 |
| 视频帧计数 | — | SG0 的剧本靠轮询 `SW_MOVIEFRAME`／`SW_MOVIETOTALFRAME` 等视频结束（如 `_STARTUP_WIN` 标签 47、`MACROSYS2` 标签 310），Bink 2 播放时设置这两个值 |

## 与原版不同、估计或没做的部分

- 短的 EXTRA 列表（标志 860 之前）在原版里两个点击区都登记在 y 519（0x45bcad、0x45bd7d），鼠标点不到 CLEAR LIST；这里用 CLEAR LIST 实际画出的位置 471。
- 标题模式 3 里按键说明例程（0x456940 类型 6）画的旋转装饰件没有移植。
- 标题和菜单的系统音效（`sysse` 挂载点）还没找到来源，`sg-pc` 同样没有。
- 手机／RINE、存读档、CONFIG、BACKLOG、TIPS、EXTRA 各画面：profile 里暂时沿用 `sg-pc` 的布局，只是为了让 HUD 能加载，没有检查过，不能当作已适配。
- 标题子菜单在触屏上用返回键或双指轻点关不掉（`sg-pc` 同样，原来就有的问题）。
- 标题"按下开始"在模式 1 之前（剧本最多等 420 帧）不接受点击，和 `sg-pc` 一样要等提示稳定后再点。

## 验证

MuMu 模拟器（Android 15 x86_64，**不是真机**），Steam 原版数据加中文脚本，用调试模式（x64、强制快进、保存的状态）：

- 启动 Logo、intro 视频完整播放，标题、按下开始、菜单、NEW GAME（触摸）。
- 序章到 `SG0_B01_12` 连续推进：对话框、名字和名牌、立绘、背景、全屏 NVL 文字、世界线变动视频 `IMV001` 和章节标题视频 `TIT_B02`。
- 真机没有测试。
