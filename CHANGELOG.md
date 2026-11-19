# Changelog

## Unreleased

- 改进（补丁 0022，仅 TYN）：`sg-pc`（STEINS;GATE Steam）的系统菜单、存档与读档画面、系统消息框，并打开存档。S;G 的脚本用的协议与 memo06 PC 已经在用的类一致，所以不写 S;G 专用的 C++：系统菜单用 `SystemMenuType.MO6TW`（`SW_SYSMENUALPHA`／`SW_SYSMENUCNO` 就是 S;G 脚本用的 2143／3338，十二个入口是脚本 `JumpTable` 的顺序，精灵量自 `DATA01.DDS`），存档用 `SaveDataType.MO6TWPC`，存读档画面用 `SaveMenuType.MO6TWPC`（`SAVEMENU`／`LOADMENU`／`QLOADMENU`），确认框用 `SysMesBoxType.MO6TW`（`SYSMESSWINDOW`／`GSYSMES` 是全透明的 128x128，盒子用 `DATA01` 里一块暗色区域拼）；`charset.lua` 补了引擎自己排版文字（格号、日期）需要的 ASCII→字形表。两处向后兼容的通用扩展：MO6TW 系统菜单认 `MenuEntriesHighlightedSprites`（每个入口各有聚焦精灵，hover 区域覆盖两张），MO6TWPC 存档菜单认可选的 `SaveBackgroundSprite`／`LoadBackgroundSprite`／`QuickLoadBackgroundSprite`；memo06 PC 的 profile 不设这些字段，行为不变。MuMu 上：菜单键打开十二个图标的系统菜单，聚焦的一行显示名称，BACK LOG／CLOSE MENU 可用；SAVE 存一格后显示缩略图、游玩时间、日期；LOAD 选格后弹出确认框，确认后回到存档的那一句。未做：从存档画面按返回退出（脚本在轮询 `00:53`，引擎里是 `ClickOnJump` 桩）、QUICK LOAD／TIPS／CONFIG 等界面、手机、格子高亮与 PREV／NEXT 的美术（图集里没有）。
- 改进（补丁 0021，仅 TYN）：`sg-pc`（STEINS;GATE Steam）的日志、字体和换行。日志：S;G 的脚本经 `MesRev`（`Unk0110` 模式 0..5）和系统循环里对 `PADcustom[12]` 的 `KeyOnJump` 轮询打开日志；`InstMesRev` 的显示／隐藏原来只对 MO6TW／MO6TWPC 调用，现在 SGHD 也调用，`UpdatePADInput` 对 SGHD 的向下轻扫／滚轮另外抬起 `PADcustom[12]`（引擎本来只合成 F2 键，S;G 不读它），profile 用量过的 `BACKLOG.DDS`（面板与标题、滚动条轨道与滑块、语音图标）。字体：profile 沿用了 CC 的字宽表，圆形拉丁字母（`o`、`O`、`?`）被裁掉右边；改用 `tools/impacto/sghd/gen_widths.py` 从字体图集生成的字宽（`font-widths.lua`，id 1..226 按墨迹右边缘加 3，空格 16，其余 48，em 宽 48）。换行：两份拉丁字母和数字在 `charset.lua` 里标成 `Alphabet`，单词不再从中间断开。MuMu 上序章前半的对话字形、间距与换行正确，向下轻扫打开日志（章节标题、人名、台词、语音图标、滚动条）；人名在对话框右下是脚本的固定位置模式，不是排版错误（此前的说明有误，已在文档里更正）。
- 新增（宿主，所有 profile）：屏幕按键与虚拟鼠标。纯触屏设备原来够不到强制快进、快速存档、系统菜单、方向键与 F 键（这些只有键盘／手柄入口；触摸手势只有点击、两指轻点／捏合、上下滑、左右滑和长按，不好记也容易误触）。`TouchControls`（宿主自己的 Java，不改引擎、不动补丁系列）在游戏画面上放一个可拖动、会淡出的小悬浮球，点开是一条按键条，**按键直接显示键位名**（Enter、Space、Bksp、Del、E、Q、Ins、1、F8、Esc、Ctrl……），下面一行小字写引擎默认键位里的功能；分页：常用、方向（↑↓←→、WASD、Home/End/PgUp/PgDn、Tab）、F1–F12、A–Z、0–9 加 Shift/Ctrl/Alt、鼠标（左右键、滚轮）。可以横向或竖向展开；设置里可调透明度、大小、展开方向、键位提示、空闲淡出、自动收起、重置位置。另有一个很小的虚拟鼠标箭头：拖动移动（引擎看到的是真鼠标，悬停高亮和点击都有效），点它是左键，长按是右键。按键与鼠标都经 `SDLActivity.onNativeKeyDown/Up`、`onNativeMouse` 送入 SDL，所以自带键位表的 profile 也能用。`SETTINGS` 增加宿主专用字段 `touchControls`（`false` 则整个关闭）。MuMu（`mo6tw-pc-zhs`、`sg-pc`）上验证了悬浮球、横竖展开、各页、自动／日志／菜单／返回／F8 快速存档／按住 Q 强制快进、滚轮下开日志、虚拟鼠标拖动／悬停／点击／长按右键、透明度与大小滑块；没有真机验证。
- 修复（宿主测试）：`ImpactoRequestTest.profileListMatchesTheAppCatalog` 还断言 10 个 profile，加了 `sg-pc` 之后该是 11 个。
- 修复（补丁 0015，仅 TYN）：PC 版 Memories Off 6 的日志（Backlog）原来打不开：向下轻扫会跑完 PC 脚本的日志流程（`MesRev` 的 DispInit 再每帧 Main，`SW_SYSSUBMENUNO` 为 1），但什么都不画，脚本在看不见的画面后面等退出标志。两个原因：`InstMesRev` 只对 `InstructionSet::MO6TW`（PS3）调用 `BacklogMenuPtr->Show()`／`Hide()`，PC 的指令集是另一个值；`profiles/mo6tw-pc/hud/backlogmenu.lua` 沿用了 PS3 的 `DrawType` `ExtrasScenes`，而 PC 脚本把日志当系统菜单的子菜单，开着时画的是 `SystemMenu` 层。修复后在 MuMu（`mo6tw-pc-zhs`）上向下轻扫打开 BACKLOG 画面（日期标题、人名、已读台词），两指轻点关闭后继续下一句。条目间距、滚动条与高亮条仍是 PS3 配置放大 1.5 倍的近似值。
- 实验（补丁 0017–0020）：Steam 版 STEINS;GATE（`sg-pc`）。它与 Chaos;Child（PC）是同一代引擎，所以新增 `InstructionSet::SGHD`（CC 表加几处覆盖：`00:4C`、`10:1B`、`10:3F`、`10:37`、`10:38`）和一个 profile，标题菜单复用 CC 的标题菜单类并按 `TITLE_CHIP` 图集重新量坐标。把参考反汇编器的指令长度和引擎实际执行逐条比对（启动到序章约 23 万条指令）没有其他操作数不一致。MuMu 上实测：Logo、标题、主菜单、START、序章背景与对话文字。没有存档（`LoadSystemData` 对 SGHD 报告 OK）；HUD 精灵、系统菜单、日志、TIPS、名牌位置仍是占位；语音／BGM／序章之后没有验证。宿主白名单与 `profiles.json` 增加 `sg-pc`；主应用的目录检测还没有。
- 修复（补丁 0018，可向上游提交）：DDS 加载器把解析状态放在文件级全局变量里，多个加载线程同时解码时互相覆盖，squish 写越界、进程 SIGSEGV（Android 上 S;G 的 DXT5 系统图集会触发）；改为 `thread_local`。
- 修复（补丁 0016，仅 TYN）：PC 版日志画面的语音图标、滚动条滑块和滚动条轨道改用在 `backlog.png` 上量出来的坐标（PC 图集不是 PS3 图集的 1.5 倍：原来的坐标画出黑条、不在图集上的滑块，轨道还指到 2048 宽图集的 x=2250）。语音条目前现在有喇叭图标，右侧有带圆珠滑块的轨道；条目间距与高亮条仍是近似值。
- 修复（补丁 0014，仅 TYN）：PC 版 Memories Off 6 的「Option」（系统菜单与标题菜单都有）原来点了没有任何可见效果，脚本还会在看不见的选项画面后面一直等 `SF_SUBMENUEXIT`，要按返回才能出来。原因是 PC 脚本通过 CC 风格的子菜单变量（`SW_SYSSUBMENUNO` 为 5、`SW_SYSSUBMENUALPHA` 0→256）打开它，从不碰 PS3 版选项菜单依赖的 `SW_OPTIONALPHA`。现在 `InstructionSet::MO6TWPC` 下子菜单渐入完成就立即给出退出标志，脚本照常渐出并回到系统菜单。PS3 布局与 PC 图集对不上，所以没有把它显示出来；PC 专用的选项画面仍是缺口。
- 文档：新增 `docs/steins-gate-steam-sghd.md`（Steam 版 STEINS;GATE 与 `sg-pc` 的现状、与 Chaos;Child 的关系、怎样发现不同的操作码、已知缺口）以及读 MPK v2 的小工具 `tools/impacto/sghd/mpk_tool.py`。
- 构建：固定的上游 impacto 提交从 `ba0b6e0`（PR #580）升到 `31bbd61`（PR #582，只改 `src/games/cclcc/mapsystem.cpp`，与补丁系列无交集）。补丁分支直接变基，13 个补丁逐字节不变（`source-lock.json` 里的补丁 SHA-256 一个都没变，只改了 `impacto.revision`）；`verify-upstream.py --series-only` / `--patched`、`test-patch-series.py`、`test-profiles.py` 通过，dev 构建通过，MuMu（Android 15，x86_64 + arm64 转译）上 `mo6tw-pc-zhs` 能进标题、New Game、第一段对话与选项。这是补丁系列「只加文件、少改上游文件」策略的一次实际演练。
- 文档：主 Tyranor Next 应用识别 PC 版目录布局（`game.exe` + `data/*.cpk`；[Tyranor-Next#192](https://github.com/Weiss-UltimateSavior/Tyranor-Next/pull/192)，随该 PR 合入并发布的主应用版本生效），添加游戏目录并扫描后按应用界面语言选 `mo6tw-pc-zhs`、`mo6tw-pc` 或 `mo6tw-pc-zht`，只对这三个 profile 要求宿主 0.2.0 及以上。README 里「主应用尚不识别 PC 版目录布局」的说明相应改写；0.2.0 条目里的同一句话是该版本发布时的状态，保持原样。无代码改动。

## 0.2.0（versionCode 4）

- 来源策略从「只用未改动的上游」改为「固定上游提交 + 本仓库经审计的补丁系列」：补丁放在 `engine/impacto/patches/`（`NNNN-*.patch` + `series`），
  SHA-256 记录在 `source-lock.json` 的 `patches`；检出必须恰好等于「固定提交 + 系列」，构建、Gradle 与两个工作流都会校验。
- 补丁系列的内容：通用引擎修复（`SetStringIp` 的缓冲检查、MSB／脚本字符串缓冲的判别、无表的指令组容错、口型表越界检查）、存档文件任务的串行化（同一时刻只运行一个，后到的排队，写入前在主线程拍快照）、两个新的 profile 开关
  （`Game.VoiceTableLittleEndian`、`Dialogue.NameInsideNametag`）、**MO6TWPC 指令集**（Windows／Steam 版 Memories Off 6 T-Wave 的脚本指令）、
  PC 版 SystemMes 布局与标题模式编号，以及 **`mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht` 三个 profile**（日文、简体、繁体；PC 版同时带三套 `mesNN.cpk`，语言由使用者选）与它们在 `gamedefinitions.lua` 里的注册。
- 宿主接受新 profile `mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht`；`engine/impacto/profiles.json` 以机器可读形式列出全部可启动 profile（来源、名称、语言、检测文件提示），
  `ImpactoRequestTest` 校验 `ImpactoRequest.PROFILES` 与它一致，`tools/impacto/test-profiles.py` 校验 PC 变体的 `Dir` 与目录名。
- 工具（`tools/impacto/`）：
  - `apply-patches.py`（只接受干净的固定提交或已恰好应用的检出，失败即停）、`verify-upstream.py --patched`（检出必须恰好等于固定提交 + 系列）、
    `verify-upstream.py --series-only`（只核对锁里的系列本身，发布工作流用它）；
  - `export-patches.py`：从上游检出的补丁分支稳定导出（diff 与 Git 配置选项全部固定），先在临时目录生成并校验（重放得到的树必须等于分支树、结果过 `load_series`），
    再原子替换，先写新文件、最后才删多余的旧补丁；`impacto_common.py` 放共享的加载与报告代码；
  - `dev-build.sh`：WSL 增量构建，产物 `dev-candidate`，不得发布，Gradle 需 `-PimpactoDevCandidate=true` 才接受，版本名带 `-dev`，且与发布签名密钥互斥；
    构建锁记录 `pid + 进程启动时间`，持有者已退出（或 pid 被别的进程复用）时自动清掉陈旧的锁；CMake 配置与锁解析与发布配方共用 `build-tools.sh` 里的同一份实现；
  - `mo6tw-pc/`：生成 `profiles/mo6tw-pc` 数据的脚本（HUD 坐标按 1.5 倍缩放、由字体图集量字宽等），只含代码，读使用者自己的游戏文件，见其 README。
- `.gitattributes` 对 `engine/impacto/patches/**` 关闭换行转换，补丁字节永不被规范化。
- 已知近似与缺口：标题、存档、选项、附加内容等非对话菜单的坐标由 PS3 配置按 1.5 倍缩放得到，只是近似（文件带 `TODO(tyn)` 头）；`mo6tw-pc` 的存档系统是 TYN 自己的格式（不读 Steam 版存档）；
  附加内容菜单用占位图集；主 Tyranor Next 应用尚不识别 PC 版目录布局（`game.exe` + `data/*.cpk`），目前只能由外部 Intent 指定 profile。
- 存档代码独立审查发现的问题已修复：存档菜单翻页不再在按钮回调里释放正在处理点击的控件组；存档文件任务串行化（后到的排队，写入前在主线程拍快照，工作线程不再读写活的存档状态）；
  快速存档的持久化在有任务运行时排队而不是被丢弃；系统数据先整段解析校验、通过后才应用；Load 模式点空槽不再把确认键交给脚本；存档路径按 UTF-8 构造（Windows 下用宽字符 API 写入）；
  删除已无使用者的 `SaveData.AllowMissingImplementation`。真机（荣耀 PPG-AN00，Android 17，`mo6tw-pc-zhs`）复测：约 34 次 PREV/NEXT 连点无崩溃；存档→强制停止→重启→读档回到同一幕同一句；
  快速存档连点后 `SYSTEM.DAT` 的 CRC 与结构完好、无残留临时文件，且槽位数与内存一致。**未验证**：Windows 构建与非 ASCII 路径、损坏系统数据的行为只做了代码审查、其他游戏没有设备回归。
- NOTICE：APK 含经修改的 ISC 上游源码，修改即补丁系列；发布的许可证文本包同时附带补丁系列；补丁系列自身的许可证待仓库所有者确定（NOTICE 里有占位说明）。
- 发行版与宿主 APK 改用新名字「Tyranor Next MAGES」：发布标题为「Tyranor Next MAGES <版本>」，发布资产改为 `Tyranor-Next-MAGES.apk`、`Tyranor-Next-MAGES.sha256`、`Tyranor-Next-MAGES.candidate.json`、`Tyranor-Next-MAGES.licenses.tar.xz`（资产名不能含空格，用连字符），宿主应用名由「MAGES.（impacto）」改为「Tyranor Next MAGES」。标签仍是 `impacto-host-<版本>`，包名与 Intent 协议不变。
- 0.2.0 另附一份与 `Tyranor-Next-MAGES.apk` 逐字节相同的 `impacto-host.apk`，只为让写死旧资产名的旧版 Tyranor Next 继续能从 `releases/latest/download/impacto-host.apk` 下载。**这份兼容副本只在 0.2.0 里有，之后的版本不再附带**：旧版 Tyranor Next 的旧链接会从下一个发布起失效，Tyranor Next 的下载链接需要改为 `Tyranor-Next-MAGES.apk`。0.1.2 及更早的发布仍带 `impacto-host.*` 资产，不会被改动。

## 0.1.2（versionCode 3）

- 支持接收 Tyranor Next 的引擎设置（0.1.2）。
- 宿主 0.1.2（versionCode 3）：新增 `SETTINGS` extra，Tyranor Next 的 MAGES. 引擎设置经它合并进该游戏的 `userconfig.toml`（`ImpactoSettings` 严格解析、`ImpactoUserConfig` 按行合并，只改受管键；字幕轨写成引擎的标志格式 `"Karaoke|Translation"`，不认识的文件布局先备份再重建，原子替换，游戏进程在跑时不改文件）。

## 0.1.1 及更早

- 本仓库由 Tyranor Next 的 MAGES. 引擎（impacto 项目）集成拆出，作为宿主 APK 的长期维护与下载位置。
- 引擎名统一为 MAGES.；impacto 是项目名。宿主应用名改为「MAGES.（impacto）」，发布标题与说明同步（0.1.1）。
- 宿主 APK 没有桌面入口：只有一个供 Tyranor Next 调用的导出 Activity，不带 `MAIN`/`LAUNCHER`。
- 上游库用 NDK `27.3.13750724` 构建（`source-lock.json`），打包时显式 `llvm-strip` 并核对 GNU build-id，避免 APK 膨胀到 400 MB 以上。
- 发布工作流产出固定名称的资产（`impacto-host.apk`、`impacto-host.sha256`、`impacto-host.candidate.json`、`impacto-host.licenses.tar.xz`），并标为最新正式版，Tyranor Next 直接下载 `releases/latest/download/impacto-host.apk`。
