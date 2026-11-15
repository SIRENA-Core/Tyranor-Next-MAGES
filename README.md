# Tyranor-Next-Impacto

[Tyranor Next](https://github.com/Weiss-UltimateSavior/Tyranor-Next) 的 **Impacto 外置宿主 APK**：把**未改动**的上游
[CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto)（固定提交见 [`engine/impacto/source-lock.json`](engine/impacto/source-lock.json)）
打成一个独立 APK，由 Tyranor Next 通过 Intent 启动。本仓库负责它的构建、发布与后续维护。

> English: a standalone Android host APK for the **unmodified** upstream Impacto engine, launched by Tyranor Next over an
> Intent. This repository builds, signs and publishes it.

## 下载与使用

- 在 [Releases](../../releases) 下载 `impacto-host-<版本>.apk` 并安装（同一版本附带 `.sha256`、`candidate.json` 与许可证文本包）。
- 该 APK **没有桌面图标**，安装后桌面上看不到它：它只是 Tyranor Next 的一个引擎模块，在 Tyranor Next 里点 Impacto 游戏即由它启动。
- 首次启动游戏时系统会要求为它开启「所有文件访问」（用来按路径读取你在 Tyranor Next 里选的游戏目录）。
- 仅支持 arm64-v8a、Android 11（API 30）及以上。

**当前状态：引擎本体还没有在真机上跑过，也没有用真实游戏数据验证。** 能确认的只有：上游库可以从固定提交编译出来、宿主 Java 层
（请求校验、授权流程、数据根与链接、`:game` 进程）在一台真机上用诊断包验证过。是否能真正玩游戏，要等有受支持的游戏数据后实测。

## 它做了什么（以及没做什么）

不修改上游任何源码、资源、着色器或 profile，不补丁 SDL。只使用上游已公开的钩子，细节见
[`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)。需要引擎改动才能解决的问题，应当停下来记录证据，
而不是在这里加补丁。

## 与 Tyranor Next 的约定

两边各自构建，下面这些值在两边各写一份，改动必须同步：

| 项 | 值 |
| --- | --- |
| 包名 | `com.tyranor.next.impacto` |
| 启动 Action | `com.tyranor.next.impacto.action.RUN` |
| Extras | `com.tyranor.next.impacto.extra.GAME_DIR` / `PROFILE` / `GAME_KEY` / `TITLE` |
| 接受的 profile | `chlcc`、`cclcc`、`cclcc-switch`、`mo6tw`、`darling`、`dash`、`rne` |
| `GAME_KEY` | `SHA-256(profile + NUL + 游戏目录)` 的前 12 字节，十六进制小写；宿主会重新计算，不符即拒绝 |
| 发布标签 | `impacto-host-<versionName>` |
| 期望版本 | Tyranor Next 的 `ImpactoHostContract.VERSION_CODE` / `VERSION_NAME` 必须不高于已发布的宿主版本 |

校验向量（宿主单测与 Tyranor Next 的单测都断言它）：目录 `/storage/emulated/0/Games/mo6tw`、profile `mo6tw`
→ `853382f8b09761cd5c6e475c`。

## 构建与发布

- 本地构建步骤、参数与限制：[`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)。
- 上游库只能在 Linux（或 WSL）上从固定提交构建：`tools/impacto/setup-linux-tools.sh` 安装固定的 NDK 与 CMake，
  `tools/impacto/build-upstream.sh` 编译。工具链固定值在 `source-lock.json`（当前 NDK `27.3.13750724`，上游自己的 CI 也用这个；
  NDK 28 编不过上游的 `fsfolderarchive.h`）。
- 发布由手动触发的 [`impacto-host-release`](.github/workflows/impacto-host-release.yml) 工作流完成，需要仓库 secrets：
  `ANDROID_KEYSTORE_BASE64`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、`ANDROID_KEY_PASSWORD`。
  **宿主必须始终用同一把密钥签名**，否则已安装的旧版无法被更新。已存在同名发布时工作流会拒绝覆盖，升级须提高
  `versionCode` 与 `versionName`。
- 日常检查：[`impacto-host-tools`](.github/workflows/impacto-host-tools.yml)（脚本与依赖固定回归，不下载依赖）。

## 许可

本仓库的 TYN 自有代码按 [GPL-2.0](LICENSE) 发布。APK 内含的上游 Impacto 及其依赖有各自的许可（Impacto 本体为 ISC，
Android 构建静态链接 FFmpeg 与 libmspack，二进制整体按 LGPL 条款处理），见 [`NOTICE.md`](NOTICE.md)；每个发布都附带
对应版本的许可证文本包。
