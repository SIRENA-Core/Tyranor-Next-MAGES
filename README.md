# Tyranor Next · MAGES.

[Tyranor Next](https://github.com/Weiss-UltimateSavior/Tyranor-Next) 的 **MAGES. 引擎外置宿主**：一个独立的 Android APK，由 Tyranor Next 通过 Intent 启动，负责运行 MAGES.（前 5pb.）的视觉小说。

引擎本体是开源项目 [CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto)（MAGES. 引擎的重新实现，ISC 许可）。构建输入是固定的上游提交加上本仓库经审计的补丁系列（[`engine/impacto/patches/`](engine/impacto/patches/README.md)）。
**impacto 是项目名，不是引擎名**；包名、类名、发布资产里的 `impacto` 指的都是这个项目。本仓库负责它的构建、发布与长期维护。

| | |
| --- | --- |
| 最新版本 | 见 [Releases](../../releases/latest)（标签 `impacto-host-<版本>`） |
| 下载 | [`Tyranor-Next-MAGES.apk`](../../releases/latest/download/Tyranor-Next-MAGES.apk)（固定地址，Tyranor Next 直接用它；0.1.2 及更早的发布资产名为 `impacto-host.apk`；0.2.0 另附一份同内容的 `impacto-host.apk` 兼容旧版 Tyranor Next，之后的版本不再附带） |
| 系统要求 | arm64-v8a，Android 11 及以上 |
| 引擎来源 | 上游固定提交 + 补丁系列，见 [`source-lock.json`](engine/impacto/source-lock.json) |

## 使用

1. 在 Tyranor Next 的引擎页点 MAGES. 跳转下载，或直接下载上面的 APK 并安装。
2. 在 Tyranor Next 里点 MAGES. 游戏即可启动。宿主**没有桌面图标**；首次启动时按提示开启「所有文件访问」，用于按路径读取游戏目录。

每个游戏有独立的数据根（存档、`userconfig.toml`），位于宿主的内部私有目录；游戏文件本身不会被复制或修改。

## 当前状态

- 引擎库已在真机（Android 17）上加载并进入上游启动流程。
- Windows／Steam 版《秋之回忆6 T-Wave》（`mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht`，由补丁系列提供）：在一台真机（荣耀 PPG-AN00，Android 17）上，
  `mo6tw-pc-zhs` 能进到标题画面，选「New Game」进入第一段对话，背景、名牌、简体中文文字和语音播放都正常，存档→强制停止→重启→读档能回到同一句。
  在 MuMu 模拟器（Android 15，x86_64 加 arm64 转译，**不是真机**）上，`mo6tw-pc`（日文）、`mo6tw-pc-zhs`、`mo6tw-pc-zht` 三个变体都能进标题、New Game 并显示第一段对话，选项分支、两指轻点打开系统菜单、向下轻扫打开日志（两指轻点关闭）、存档菜单存一格再重启后从 Continue → Load 读出（缩略图、游玩时长、时间都在）也都正常；系统菜单的「オプション」在 PC 版目前没有可用的界面（选项画面的 PS3 布局与 PC 图集对不上），点了会直接回到系统菜单，「エンサイクロペディア」（TIPS）同样没有界面，点了没有可见反应、按返回才退出；「タイトルに戻る」的确认对话框也不显示（脚本在等一个看不见的确认），同样要按返回。除此之外都没有验证：非对话菜单（坐标为近似）、附加内容菜单（占位图集）、输入与性能（真机）。
  存档代码审查发现的问题已修复，并在同一台真机上复测了翻页连点、强制停止后读回、快速存档连点；Windows 构建与非 ASCII 路径、其他游戏的回归没有验证。Tyranor Next 主应用识别 PC 版目录布局（根目录 `game.exe` + `data/` 里的 `script.cpk`、`mes00.cpk`；见 [Tyranor-Next#192](https://github.com/Weiss-UltimateSavior/Tyranor-Next/pull/192)，随该 PR 合入并发布的主应用版本生效）：添加游戏目录并扫描后按应用界面语言选 `mo6tw-pc-zhs`、`mo6tw-pc` 或 `mo6tw-pc-zht`，只对这三个 profile 要求宿主 0.2.0 及以上。更早的主应用版本不识别，只能由外部 Intent 指定 profile。主应用一侧在真机上只验证了识别、变体选择与版本提示，「主应用启动宿主进入游戏」这一整段还没有验证。
- **实验性：Windows／Steam 版 STEINS;GATE（`sg-pc`，补丁系列提供）**：在 MuMu 模拟器（Android 15，**不是真机**）上、用原版英文数据能走到标题、主菜单、START，读过序章前半（秋叶原、7F、天台、讲座会场的背景，真由理与红莉栖的立绘和 CG；对话字形与间距正确、按词换行；向下轻扫打开日志，有章节标题、台词、语音图标和滚动条）。它与 Chaos;Child（PC）是同一代引擎（新的 `InstructionSet::SGHD` 从 CC 表复制再覆盖几个操作码）。**没有**存档（当作全新安装）、没有系统菜单／存档／TIPS／选项／手机的真实界面（电话与邮件触发点走不通），语音、BGM、序章之后的内容没有验证；主应用还不识别这个游戏的目录。细节见 [`docs/steins-gate-steam-sghd.md`](docs/steins-gate-steam-sghd.md)。
- 全部可启动 profile 的机器可读清单见 [`engine/impacto/profiles.json`](engine/impacto/profiles.json)。
- 宿主 0.1.2 起支持接收 Tyranor Next 传来的引擎设置（见下文 `SETTINGS`）。

## 与 Tyranor Next 的约定

两边各写一份，改动必须同步：

| 项 | 值 |
| --- | --- |
| 包名 / Action | `com.tyranor.next.impacto` / `com.tyranor.next.impacto.action.RUN` |
| Extras | `com.tyranor.next.impacto.extra.` + `GAME_DIR`、`PROFILE`、`GAME_KEY`、`TITLE`、`SETTINGS`（0.1.2 起，扁平 JSON，见下） |
| profile | `chlcc`、`cclcc`、`cclcc-switch`、`mo6tw`、`mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht`、`sg-pc`、`darling`、`dash`、`rne`（`sg-pc` 为 Steam 版 STEINS;GATE，实验性，需要之后的宿主版本；`mo6tw-pc*` 为 Windows／Steam 版 Memories Off 6 T-Wave，依次为日文、简体、繁体，profile 定义由补丁系列提供；清单见 `engine/impacto/profiles.json`） |
| `GAME_KEY` | `SHA-256(profile + NUL + 游戏目录)` 前 12 字节的小写十六进制；宿主会重算，不符即拒绝 |
| 下载地址 | `releases/latest/download/Tyranor-Next-MAGES.apk`（资产名固定，版本在标签与 APK 内）；Tyranor Next 期望的 `versionCode` 不得高于最新发布 |
| 最低版本 | Tyranor Next 要求宿主 `versionCode` ≥ 3（0.1.2）；`mo6tw-pc*` 三个 profile 需要 `versionCode` ≥ 4（0.2.0），更早的宿主会拒绝这些 profile；Tyranor Next 只对这三个 profile 按 ≥ 4 提示更新宿主，其余 profile 仍只要求 ≥ 3 |

校验向量：目录 `/storage/emulated/0/Games/mo6tw` + profile `mo6tw` → `853382f8b09761cd5c6e475c`。

入口 Activity 对外导出，所有字段按不可信输入校验：profile 走白名单；目录必须是共享存储下的规范化路径，且不得位于其他应用的 `Android/data`、`Android/obb`；`GAME_KEY` 由宿主重算。细节见 [`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)。

## 用户设置（`SETTINGS`）

Tyranor Next 在每次启动请求里带上该游戏的生效设置，宿主在引擎启动前把它们合并进该游戏的 `userconfig.toml`。请求不可信：只接受已知字段的正确类型，其余忽略；字段缺失或非法时不改对应键。

| 字段（JSON） | 类型 | `userconfig.toml` 键 |
| --- | --- | --- |
| `swapConfirmCancel` | bool | `[CommonSettings]` `SwapConfirmCancelButtons` |
| `vsync` | bool | `[GameSettings.<profile>]` `UseVSync` |
| `videoPlayback` | bool | `[AdvancedSettings]` `VideoPlayer`（`FFmpeg` / `None`） |
| `subtitles` | `all`/`translation`/`karaoke` | `[EnhancementsSettings]` `SubtitleConfig`（写成引擎的标志格式 `"Karaoke\|Translation"` / `"Translation"` / `"Karaoke"`；没有“全部关闭”，引擎读不回空的标志集） |
| `closeBacklogAtEnd` | bool | `[EnhancementsSettings]` `CloseBacklogWhenReachedEnd` |
| `delusionMouse` | bool | `[EnhancementsSettings.CHLCC]` / `.CCLCC` `DelusionMousePatch`（只对 `chlcc`、`cclcc`） |
| `logLevel` | `off`/`fatal`/`error`/`warning`/`info`/`debug`/`trace` | `[CommonSettings]` `LogLvl` |
| `touchControls` | bool | 不是引擎选项，只由宿主使用：是否显示屏幕按键（见下节），缺省为显示 |

写入方式：

- 只改上表的键，文件里其它内容与注释原样保留；文件替换用原子重命名。
- 遇到无法逐行安全编辑的布局（带引号的表头或键、点号键、多行字符串或数组、单独的 `\r` 换行等），或合并后会出现重复的表或键，先备份为 `userconfig.toml.bak` 再写一份干净的文件——引擎读 TOML 出错会直接无法启动。
- 游戏进程已在运行时不改文件（引擎自己在改写它）。

不提供的上游选项：分辨率与显示模式（Android 上固定全屏）、渲染器与音频后端（Android 构建只有 OpenGL 与 OpenAL）、补丁档案（补丁目录在宿主私有目录里，用户无法放入文件）、日志文件路径与频道。

## 屏幕按键与虚拟鼠标

impacto 对触摸只做了几个手势：点击（确定）、两指轻点或捏合（返回／右键）、下滑（日志）、上滑（隐藏界面）、右滑／左滑（快进／全部快进）、原地按住约 0.3 秒（自动播放）。
强制快进、快速存档、系统菜单（只能靠两指轻点间接打开）、方向键、F 键等没有触摸入口，手势本身也不好记、容易误触；纯触屏的手机因此用不了大部分功能。所以宿主在游戏画面上叠了一层**很小的半透明按键面板**（宿主自己的 Java，不改引擎、不依赖补丁系列，所有 profile 通用）：

- **悬浮球**：点一下展开／收起，可以拖动，位置跨游戏保存；空闲几秒后淡出，展开后几秒不操作自动收起（可关）。
- **按键直接显示键位名**，下面一行小字写它在引擎默认键位里的功能（可关）：`Enter`/`Space`（确定）、`Bksp`（返回）、`Del`（自动）、`E`（快进）、`Q`（强制快进，按住）、`Ins`（回想）、`1`（菜单）、`F8`（快速存档）、`Esc`、`Ctrl`（按住）。
  分页（点第一个按钮切换）：常用、方向（↑↓←→、WASD、Home/End/PgUp/PgDn、Tab）、F1–F12、A–Z、0–9 加 Shift/Ctrl/Alt（按住）、鼠标（左键、右键、滚轮上下）。按下的是真实键盘事件（`SDLActivity.onNativeKeyDown/Up`，Android 键码对应 SDL 的扫描码），所以自带键位表的 profile（cclcc、chlcc、mo6tw）也能用，只是小字提示按引擎默认键位写。
- **展开方向**可选横向（在悬浮球旁边）或竖向（在悬浮球上方／下方，内容多时滚动），向有空间的一侧展开。
- **设置**（面板里的「设置」）：透明度、大小、展开方向、键位提示、空闲淡出、自动收起、虚拟鼠标开关、重置位置。设置按设备保存，不分游戏。
- **虚拟鼠标**：一个很小的箭头，拖动它移动（引擎看到的是普通鼠标：悬停高亮、点击都有效），点它是左键，长按是右键（等同两指轻点，在 memo06 里打开系统菜单）。鼠标页的按钮也作用在它的位置。
- 请求里带 `"touchControls": false` 可以整体关闭（例如主应用检测到手柄或键盘时）。

在 MuMu（Android 15）上用 `mo6tw-pc-zhs` 和 `sg-pc` 验证过：悬浮球、横向与竖向展开、各页键位、自动（台词自己往下走）、日志、菜单（系统菜单）、返回（关闭日志）、F8（出现 Quick Saved）、按住 Q（越过对话停在选项）、滚轮下（打开日志）、虚拟鼠标的拖动、悬停高亮与点击、长按右键、透明度与大小滑块。`E`（快进）只切换引擎的快进状态，引擎默认只快进已读文本，所以新开的游戏里按了没有可见变化，这和键盘一致。没有在真机上验证，也没有测过实体键盘或手柄同时存在的情况。

## 构建与发布

- **本地构建**：见 [`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)。上游库只能在 Linux／WSL 上构建（`tools/impacto/`），宿主 APK 可在 Windows 上打包。
  日常迭代引擎补丁用 `tools/impacto/dev-build.sh`（增量构建，产物标为 `dev-candidate`，Gradle 需显式 `-PimpactoDevCandidate=true`，版本带 `-dev`，**不得发布**）。
- **发布**：手动运行 [`impacto-host-release`](.github/workflows/impacto-host-release.yml)，需要 secrets
  `ANDROID_KEYSTORE_BASE64`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、`ANDROID_KEY_PASSWORD`。
  - **始终用同一把密钥签名**，否则已安装的旧版无法更新。
  - 已存在同名标签时拒绝覆盖；升级须提高 `versionCode`／`versionName`，发布后自动成为最新版。
- **固定上游 + 审计补丁系列**：构建输入是 `source-lock.json` 固定的上游提交，加上 [`engine/impacto/patches/`](engine/impacto/patches/README.md)
  里按序应用的补丁；每个补丁的 SHA-256 记录在 `source-lock.json`，构建与 Gradle 都会校验检出恰好等于「固定提交 + 系列」，多一个字节都拒绝。
  补丁只放 TYN 兼容性所需的最小改动，不碰 SDL3 的 Java 层与 JNI 命名空间。
- **同步上游**：把补丁分支变基到新的上游提交，改 `source-lock.json` 的 `impacto.revision`，再用 `tools/impacto/export-patches.py` 重新导出系列
  （流程见补丁目录的 README）；上游已吸收的补丁直接丢掉。

## 许可

自有代码 [GPL-2.0](LICENSE)；APK 内的上游 impacto（ISC）、静态链接的 FFmpeg 与 libmspack（LGPL）等见 [`NOTICE.md`](NOTICE.md)，每个发布附带许可证文本包。
