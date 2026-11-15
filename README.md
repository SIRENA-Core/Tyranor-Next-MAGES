# Tyranor-Next-Impacto

[Tyranor Next](https://github.com/Weiss-UltimateSavior/Tyranor-Next) 的 **MAGES. 引擎**外置宿主 APK。MAGES.（前 5pb.）的视觉小说引擎，
**impacto** 是重新实现它的开源项目（本仓库名里的 Impacto 指这个项目，不是引擎名）：把**未改动**的上游
[CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto)（固定提交见 [`source-lock.json`](engine/impacto/source-lock.json)）
打成独立 APK，由 Tyranor Next 通过 Intent 启动。本仓库负责它的构建、发布与维护。

## 使用

1. 在 Tyranor Next 的引擎页点 Impacto 即可跳转下载；也可以直接下载最新版：[`impacto-host.apk`](../../releases/latest/download/impacto-host.apk)，然后安装。
2. 在 Tyranor Next 里点 MAGES. 游戏即可启动。宿主**没有桌面图标**，首次启动时按提示开启「所有文件访问」。

要求：arm64-v8a，Android 11 及以上。

**状态：** 引擎库已在一台真机（Android 17）上加载，进入了上游的 `SDL_main` 和启动流程；但还没有任何游戏能进到画面——Windows／Steam 版数据与上游 PS3 配置不符（没有 `SCRIPT.cls`），没有可用的受支持数据，渲染、声音、输入都未验证。

## 与 Tyranor Next 的约定

两边各写一份，改动必须同步：

| 项 | 值 |
| --- | --- |
| 包名 / Action | `com.tyranor.next.impacto` / `com.tyranor.next.impacto.action.RUN` |
| Extras | `com.tyranor.next.impacto.extra.` + `GAME_DIR`、`PROFILE`、`GAME_KEY`、`TITLE` |
| profile | `chlcc`、`cclcc`、`cclcc-switch`、`mo6tw`、`darling`、`dash`、`rne` |
| `GAME_KEY` | `SHA-256(profile + NUL + 游戏目录)` 前 12 字节的小写十六进制；宿主会重算，不符即拒绝 |
| 下载地址 | `releases/latest/download/impacto-host.apk`（资产名固定，版本在标签 `impacto-host-<versionName>` 与 APK 内）；Tyranor Next 期望的 `versionCode` 不得高于最新发布 |

校验向量：目录 `/storage/emulated/0/Games/mo6tw` + profile `mo6tw` → `853382f8b09761cd5c6e475c`。

## 构建与发布

- 本地构建见 [`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)；上游库只能在 Linux/WSL 上构建（`tools/impacto/`）。
- 发布：手动运行 [`impacto-host-release`](.github/workflows/impacto-host-release.yml)，需要 secrets
  `ANDROID_KEYSTORE_BASE64`、`ANDROID_KEYSTORE_PASSWORD`、`ANDROID_KEY_ALIAS`、`ANDROID_KEY_PASSWORD`。
  **必须始终用同一把密钥签名**，否则已安装的旧版无法更新；已存在同名标签时拒绝覆盖，升级须提高 `versionCode`/`versionName`，发布后自动成为最新版。
- 不修改上游任何源码、资源或 SDL。需要改引擎才能解决的问题，记录证据后停下，不在这里打补丁。

## 许可

自有代码 [GPL-2.0](LICENSE)；APK 内的上游 impacto（ISC）、静态链接的 FFmpeg 与 libmspack（LGPL）等见 [`NOTICE.md`](NOTICE.md)，
每个发布附带许可证文本包。
