# Changelog

## Unreleased

- 修复（补丁 0015，仅 TYN）：PC 版 Memories Off 6 的日志（Backlog）原来打不开：向下轻扫会跑完 PC 脚本的日志流程（`MesRev` 的 DispInit 再每帧 Main，`SW_SYSSUBMENUNO` 为 1），但什么都不画，脚本在看不见的画面后面等退出标志。两个原因：`InstMesRev` 只对 `InstructionSet::MO6TW`（PS3）调用 `BacklogMenuPtr->Show()`／`Hide()`，PC 的指令集是另一个值；`profiles/mo6tw-pc/hud/backlogmenu.lua` 沿用了 PS3 的 `DrawType` `ExtrasScenes`，而 PC 脚本把日志当系统菜单的子菜单，开着时画的是 `SystemMenu` 层。修复后在 MuMu（`mo6tw-pc-zhs`）上向下轻扫打开 BACKLOG 画面（日期标题、人名、已读台词），两指轻点关闭后继续下一句。条目间距、滚动条与高亮条仍是 PS3 配置放大 1.5 倍的近似值。
- 修复（补丁 0016，仅 TYN）：PC 版日志画面的语音图标、滚动条滑块和滚动条轨道改用在 `backlog.png` 上量出来的坐标（PC 图集不是 PS3 图集的 1.5 倍：原来的坐标画出黑条、不在图集上的滑块，轨道还指到 2048 宽图集的 x=2250）。语音条目前现在有喇叭图标，右侧有带圆珠滑块的轨道；条目间距与高亮条仍是近似值。
- 修复（补丁 0014，仅 TYN）：PC 版 Memories Off 6 的「Option」（系统菜单与标题菜单都有）原来点了没有任何可见效果，脚本还会在看不见的选项画面后面一直等 `SF_SUBMENUEXIT`，要按返回才能出来。原因是 PC 脚本通过 CC 风格的子菜单变量（`SW_SYSSUBMENUNO` 为 5、`SW_SYSSUBMENUALPHA` 0→256）打开它，从不碰 PS3 版选项菜单依赖的 `SW_OPTIONALPHA`。现在 `InstructionSet::MO6TWPC` 下子菜单渐入完成就立即给出退出标志，脚本照常渐出并回到系统菜单。PS3 布局与 PC 图集对不上，所以没有把它显示出来；PC 专用的选项画面仍是缺口。
- 文档：新增 `docs/steins-gate-steam-sghd.md`，记录 Steins;Gate（Steam 版）与 impacto 的差距（SGHD 指令集、写死在 Game.exe 里的原生 UI、分步路线），以及读 MPK v2 的小工具 `tools/impacto/sghd/mpk_tool.py`。这是分析，不是支持：宿主仍然不能运行该游戏。
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
