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
  除此之外都没有验证：其他 profile 与游戏、繁体／日文变体、非对话菜单（坐标为近似）、附加内容菜单（占位图集）、输入与性能。
  存档代码审查发现的问题已修复，并在同一台真机上复测了翻页连点、强制停止后读回、快速存档连点；Windows 构建与非 ASCII 路径、其他游戏的回归没有验证。Tyranor Next 主应用也还不识别 PC 版目录布局（`game.exe` + `data/*.cpk`），目前只能由外部 Intent 指定 profile。
- 全部可启动 profile 的机器可读清单见 [`engine/impacto/profiles.json`](engine/impacto/profiles.json)。
- 宿主 0.1.2 起支持接收 Tyranor Next 传来的引擎设置（见下文 `SETTINGS`）。

## 与 Tyranor Next 的约定

两边各写一份，改动必须同步：

| 项 | 值 |
| --- | --- |
| 包名 / Action | `com.tyranor.next.impacto` / `com.tyranor.next.impacto.action.RUN` |
| Extras | `com.tyranor.next.impacto.extra.` + `GAME_DIR`、`PROFILE`、`GAME_KEY`、`TITLE`、`SETTINGS`（0.1.2 起，扁平 JSON，见下） |
| profile | `chlcc`、`cclcc`、`cclcc-switch`、`mo6tw`、`mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht`、`darling`、`dash`、`rne`（`mo6tw-pc*` 为 Windows／Steam 版 Memories Off 6 T-Wave，依次为日文、简体、繁体，profile 定义由补丁系列提供；清单见 `engine/impacto/profiles.json`） |
| `GAME_KEY` | `SHA-256(profile + NUL + 游戏目录)` 前 12 字节的小写十六进制；宿主会重算，不符即拒绝 |
| 下载地址 | `releases/latest/download/Tyranor-Next-MAGES.apk`（资产名固定，版本在标签与 APK 内）；Tyranor Next 期望的 `versionCode` 不得高于最新发布 |
| 最低版本 | Tyranor Next 要求宿主 `versionCode` ≥ 3（0.1.2）；`mo6tw-pc*` 三个 profile 需要 `versionCode` ≥ 4（0.2.0），更早的宿主会拒绝这些 profile |

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

写入方式：

- 只改上表的键，文件里其它内容与注释原样保留；文件替换用原子重命名。
- 遇到无法逐行安全编辑的布局（带引号的表头或键、点号键、多行字符串或数组、单独的 `\r` 换行等），或合并后会出现重复的表或键，先备份为 `userconfig.toml.bak` 再写一份干净的文件——引擎读 TOML 出错会直接无法启动。
- 游戏进程已在运行时不改文件（引擎自己在改写它）。

不提供的上游选项：分辨率与显示模式（Android 上固定全屏）、渲染器与音频后端（Android 构建只有 OpenGL 与 OpenAL）、补丁档案（补丁目录在宿主私有目录里，用户无法放入文件）、日志文件路径与频道。

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
