# Tyranor-Next-Impacto

[Tyranor Next](https://github.com/Weiss-UltimateSavior/Tyranor-Next) 的 **MAGES. 引擎**外置宿主 APK。MAGES.（前 5pb.）的视觉小说引擎，
**impacto** 是重新实现它的开源项目（本仓库名里的 Impacto 指这个项目，不是引擎名）：把上游
[CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto)（固定提交见 [`source-lock.json`](engine/impacto/source-lock.json)）
加上本仓库经审计的补丁系列（[`engine/impacto/patches/`](engine/impacto/patches/README.md)）打成独立 APK，由 Tyranor Next 通过 Intent 启动。
本仓库负责它的构建、发布与维护。

## 使用

1. 在 Tyranor Next 的引擎页点 Impacto 即可跳转下载；也可以直接下载最新版：[`impacto-host.apk`](../../releases/latest/download/impacto-host.apk)，然后安装。
2. 在 Tyranor Next 里点 MAGES. 游戏即可启动。宿主**没有桌面图标**，首次启动时按提示开启「所有文件访问」。

要求：arm64-v8a，Android 11 及以上。

**状态：** 在一台真机（荣耀 PPG-AN00，Android 17）上，Windows／Steam 版 Memories Off 6 T-Wave 用 `mo6tw-pc-zhs` 能进到标题画面，选「New Game」进入第一段对话，
背景、名牌、简体中文文字和语音播放都正常。除此之外都没有验证：其他 profile 与游戏、繁体／日文变体、非对话菜单（坐标为近似）、存读档（`mo6tw-pc` 还没有存档系统）、
附加内容菜单（占位图集）、输入与性能；Tyranor Next 主应用也还不识别 PC 版目录布局，目前只能由外部 Intent 指定 profile。
全部可启动 profile 的机器可读清单见 [`engine/impacto/profiles.json`](engine/impacto/profiles.json)。

## 与 Tyranor Next 的约定

两边各写一份，改动必须同步：

| 项 | 值 |
| --- | --- |
| 包名 / Action | `com.tyranor.next.impacto` / `com.tyranor.next.impacto.action.RUN` |
| Extras | `com.tyranor.next.impacto.extra.` + `GAME_DIR`、`PROFILE`、`GAME_KEY`、`TITLE` |
| profile | `chlcc`、`cclcc`、`cclcc-switch`、`mo6tw`、`mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht`、`darling`、`dash`、`rne`（`mo6tw-pc*` 为 Windows／Steam 版 Memories Off 6 T-Wave，依次为日文、简体、繁体，profile 定义由补丁系列提供；清单见 `engine/impacto/profiles.json`） |
| `GAME_KEY` | `SHA-256(profile + NUL + 游戏目录)` 前 12 字节的小写十六进制；宿主会重算，不符即拒绝 |
| 下载地址 | `releases/latest/download/impacto-host.apk`（资产名固定，版本在标签 `impacto-host-<versionName>` 与 APK 内）；Tyranor Next 期望的 `versionCode` 不得高于最新发布 |

校验向量：目录 `/storage/emulated/0/Games/mo6tw` + profile `mo6tw` → `853382f8b09761cd5c6e475c`。

## 构建与发布

- 本地构建见 [`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)；上游库只能在 Linux/WSL 上构建（`tools/impacto/`）。
  日常迭代引擎补丁用 `tools/impacto/dev-build.sh`（增量构建，产物标为 `dev-candidate`，Gradle 需显式 `-PimpactoDevCandidate=true`，版本带 `-dev`，**不得发布**）。
- 发布：手动运行 [`impacto-host-release`](.github/workflows/impacto-host-release.yml)，需要 secrets
  `ANDROID_KEYSTORE_BASE64`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、`ANDROID_KEY_PASSWORD`。
  **必须始终用同一把密钥签名**，否则已安装的旧版无法更新；已存在同名标签时拒绝覆盖，升级须提高 `versionCode`/`versionName`，发布后自动成为最新版。
- **固定上游 + 审计补丁系列**：构建输入是 `source-lock.json` 固定的上游提交，加上 [`engine/impacto/patches/`](engine/impacto/patches/README.md)
  里按序应用的补丁；每个补丁的 SHA-256 记录在 `source-lock.json`，构建与 Gradle 都会校验检出恰好等于「固定提交 + 系列」，多一个字节都拒绝。
  补丁只放 TYN 兼容性所需的最小改动，不碰 SDL3 的 Java 层与 JNI 命名空间。
- **同步上游**：把补丁分支变基到新的上游提交，改 `source-lock.json` 的 `impacto.revision`，再用 `tools/impacto/export-patches.py` 重新导出系列
  （流程见补丁目录的 README）；上游已吸收的补丁直接丢掉。

## 许可

自有代码 [GPL-2.0](LICENSE)；APK 内的上游 impacto（ISC）、静态链接的 FFmpeg 与 libmspack（LGPL）等见 [`NOTICE.md`](NOTICE.md)，
每个发布附带许可证文本包。
