# MAGES. 引擎宿主 APK（impacto）

承载 MAGES. 引擎的开源重新实现 impacto（项目名，不是引擎名）——[CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto)
的固定提交（见 `../source-lock.json`）**加上本仓库经审计的补丁系列**（`../patches/`，流程见其 README）。
Tyranor Next 通过 Intent 启动本 APK；它没有桌面图标，本仓库负责它的构建、发布与维护。

## 为什么是独立 APK

上游 `android/` 自带 SDL3 的 `org.libsdl.app` Java 层，与主 APK 内置的 SDL2 同名类冲突。独立进程消除不了同一 APK 内的类名冲突，
而改名、生成修改后的副本或替换符号（私有 SDL 命名空间）仍然被禁止：补丁系列不碰 SDL3 的 Java 层与 JNI 命名空间，候选库检查会拒绝私有命名空间。所以它是单独的 APK：包内只有

- 上游 Java 源码（`ImpactoActivity` 与 SDL3 Java 层），构建时直接引用已校验的**补丁后检出**（固定提交 + 系列），不复制；SDL3 Java 层与上游一致；
- 库 `libimpacto.so`（由 `tools/impacto/build-upstream.sh` 从同一个补丁后检出构建的候选库）；
- 同一检出里的 `profiles/`、`resources/`、着色器和 `gamedefinitions.lua`，构建时暂存到 `build/`，不写回源码目录；
- TYN 自有的类：`ImpactoLaunchActivity`、`TyranorImpactoActivity`，以及屏幕按键与虚拟鼠标（`TouchControls`、`TouchKeys`、`TouchPrefs`，见下文）。

## 宿主做了什么

宿主自己只使用上游已公开的钩子（上游代码的改动全部在补丁系列里，宿主不另改）：

| 上游钩子 | 宿主行为 |
| --- | --- |
| `SDLActivity.getArguments()` | 传原版命令行 `-g <profile> -bp <basepaths.lua> -gc <gamedefinitions.lua> -uc <userconfig.toml>` |
| `ImpactoActivity.getChosenDirectory()` | 返回每个游戏独立的数据根 `<内部私有目录>/games/<gameKey>` |
| `ImpactoActivity.chooseDirectory()` / `resetChosenDir()` | 空实现：游戏目录由 Tyranor Next 选择，禁用上游目录选择器 |

原生代码经 JNI 在 Activity 实例上调用后三者，因此重写会被命中。

数据根下由上游自己创建 `gamedata/`、`patches/`、`saves/`；宿主只在 `gamedata/<profile>` 建一个指向游戏目录的符号链接，
上游即按 `RootGamedataDir/<profile>/<档案>` 找到数据，无需复制。存档与 `userconfig.toml` 因此按游戏隔离。
链接位置已存在真实目录或文件时拒绝替换。

屏幕按键：纯触屏设备够不到自动、快进、快速存档、系统菜单等只有键盘／手柄入口的操作，`TouchControls` 在 SDL 的布局上加一个小悬浮球和按键条（见仓库根 README「屏幕按键与虚拟鼠标」）。
它只往 SDL 送真实的键盘与鼠标事件（`SDLActivity.onNativeKeyDown/Up`、`onNativeMouse`），不碰引擎，所有 profile 通用；只有它自己的几个视图接收触摸，其余触摸仍直达游戏。`SETTINGS` 里的 `touchControls: false` 经启动器转给游戏 Activity（只有宿主自己能设这个额外参数，游戏 Activity 不导出）。

启动请求还可带 `SETTINGS`（用户设置 JSON，字段与对应的 `userconfig.toml` 键见仓库根 README）：宿主在建好数据根后、启动引擎前，把它合并进数据根下的 `userconfig.toml`（引擎自己的 `-uc` 路径）；写入失败只记日志，不阻止启动。

入口 Activity 对外导出，所有字段都按不可信输入校验：profile 必须在固定白名单内；目录必须是共享存储（`/storage/`、`/sdcard/`）
下的规范化路径，且不得位于其他应用的 `Android/data`、`Android/obb`；`gameKey` 由宿主按与主 App 相同的方式
（SHA-256 前 12 字节，输入为 `profile NUL 目录`）重新计算，不符即拒绝，因此调用方无法让某个游戏的数据根指向别的目录。
读取 extras 时任何运行时异常都按拒绝处理，不会让承载游戏的进程崩溃。校验通过且已授予「所有文件访问」后才启动不导出的游戏 Activity。
游戏 Activity 运行在独立的 `:game` 进程，并关闭预测性返回（`SDLActivity` 依赖 `onBackPressed()`，targetSdk 36 默认会吞掉它）。

## 构建

需要 Python 3（非 Windows 使用 `python3`）、Android SDK（compileSdk 36）、JDK 17，以及：

1. 已校验的补丁后检出：固定上游提交 + 补丁系列（`tools/impacto/apply-patches.py` 应用，`tools/impacto/verify-upstream.py --patched` 通过；`build-upstream.sh` 会自己做这一步，其 `source/` 目录可直接使用），
2. 候选库 `libimpacto.so`（只能在 Linux 或 WSL 构建，见 `tools/impacto/build-upstream.sh`），以及构建它的 NDK：设置 `ANDROID_NDK_HOME` 或 `-PimpactoNdk=<NDK 目录>`。宿主构建用该 NDK 的 `llvm-strip` 剥离调试符号并核对 build-id；找不到工具时构建失败，不会打进未剥离的库（未剥离约 337 MiB，会使 APK 膨胀到 400 MB 以上）。

```sh
./gradlew -p engine/impacto/host-apk :app:assembleDebug \
  -PimpactoSource=/path/to/patched/impacto \
  -PimpactoCandidate=/path/to/build/candidate
```

### 开发快速路径（不得发布）

迭代引擎补丁时，在 WSL/Linux 上用 `tools/impacto/dev-build.sh`：独立根目录（默认 `~/impacto-dev`），首次从 `IMPACTO_DEV_SEED`（默认 `~/impacto-build/upstream`，只读）复制上游检出、vcpkg、二进制缓存与下载缓存，之后每次把源码重置到固定提交并应用补丁系列（已经恰好是「固定提交 + 系列」时保持原样，ninja 只重编改动的文件），再增量构建并产出 `dev-candidate`。
`IMPACTO_DEV_CONFIGURE_ONLY=1` 只做配置；构建锁（`.build.lock`）记录持有者的 pid 与进程启动时间，持有者已退出时下次运行自动清掉陈旧的锁；默认并行度刻意压低（ninja 最多 4 个任务，vcpkg 2，可用 `IMPACTO_DEV_JOBS`／`VCPKG_MAX_CONCURRENCY` 调整），已有 `build/build.ninja` 时不重复配置（`IMPACTO_DEV_RECONFIGURE=1` 强制）。它不满足发布配方的「新建构建根、不复用 FetchContent/CMake 状态」要求，所以产物标为 `dev-candidate`、`releaseReady:false`，Gradle 只有显式传 `-PimpactoDevCandidate=true` 才接受（版本名带 `-dev`），且与发布签名密钥互斥：

```sh
./gradlew -p engine/impacto/host-apk :app:assembleDebug \
  -PimpactoSource=<DEV>/source -PimpactoCandidate=<DEV>/candidate \
  -PimpactoDevCandidate=true -PimpactoNdk=<NDK>
```

只编译 Java、运行 JVM 单测时不需要候选库，加 `-PimpactoHostOnly=true`（打包时也需要核对候选库，所以不加它就必须给 `-PimpactoCandidate`）：

```sh
./gradlew -p engine/impacto/host-apk :app:testDebugUnitTest -PimpactoSource=/path/to/patched/impacto -PimpactoHostOnly=true
```

构建任务（`preBuild`，覆盖编译、lint、单测）会先运行 `verify-upstream.py --patched`，检出不是「固定提交 + 系列」（含多出任何改动）即失败；打包前还会核对候选库：`candidate.json` 必须来自 `../source-lock.json`，且 `libimpacto.so` 的 SHA-256 与报告一致。

仅验证 Java 层（请求校验、权限流程、数据目录与符号链接）时，可加 `-PimpactoHostOnly=true`：不打包 `libimpacto.so`，
版本名带 `-hostonly`，**该 APK 起不了引擎，不得分发**。

## 限制

- 仅 Android 11（API 30）及以上：需要「所有文件访问」才能经路径读取游戏目录。
- 每个进程只跑一个游戏；游戏 Activity 结束时宿主结束进程，避免 SDL 的进程级状态残留。
- 数据根与存档在宿主的内部私有目录内（`files/games/<gameKey>/`），主 App 无法管理或同步。外部存储（含 `Android/data`）是 FUSE，不允许建符号链接，已在真机上确认，所以数据根必须放在内部存储。
- 只在一台真机（荣耀 PPG-AN00，Android 17）上验证过：Windows／Steam 版 Memories Off 6 T-Wave + `mo6tw-pc-zhs` 到标题画面、New Game、第一段对话（背景、名牌、简体中文文字、语音）；其余 profile、变体、存读档（`mo6tw-pc` 暂无存档系统）、输入与性能均未验证。
