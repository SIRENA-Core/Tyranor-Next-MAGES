# Changelog

## Unreleased

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

## 0.1.2（versionCode 3）

- 支持接收 Tyranor Next 的引擎设置（0.1.2）。
- 宿主 0.1.2（versionCode 3）：新增 `SETTINGS` extra，Tyranor Next 的 MAGES. 引擎设置经它合并进该游戏的 `userconfig.toml`（`ImpactoSettings` 严格解析、`ImpactoUserConfig` 按行合并，只改受管键；字幕轨写成引擎的标志格式 `"Karaoke|Translation"`，不认识的文件布局先备份再重建，原子替换，游戏进程在跑时不改文件）。

## 0.1.1 及更早

- 本仓库由 Tyranor Next 的 MAGES. 引擎（impacto 项目）集成拆出，作为宿主 APK 的长期维护与下载位置。
- 引擎名统一为 MAGES.；impacto 是项目名。宿主应用名改为「MAGES.（impacto）」，发布标题与说明同步（0.1.1）。
- 宿主 APK 没有桌面入口：只有一个供 Tyranor Next 调用的导出 Activity，不带 `MAIN`/`LAUNCHER`。
- 上游库用 NDK `27.3.13750724` 构建（`source-lock.json`），打包时显式 `llvm-strip` 并核对 GNU build-id，避免 APK 膨胀到 400 MB 以上。
- 发布工作流产出固定名称的资产（`impacto-host.apk`、`impacto-host.sha256`、`impacto-host.candidate.json`、`impacto-host.licenses.tar.xz`），并标为最新正式版，Tyranor Next 直接下载 `releases/latest/download/impacto-host.apk`。
