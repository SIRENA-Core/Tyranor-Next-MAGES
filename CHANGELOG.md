# Changelog

## Unreleased

- 本仓库由 Tyranor Next 的 Impacto 集成拆出，作为宿主 APK 的长期维护与下载位置。
- 宿主 APK 没有桌面入口：只有一个供 Tyranor Next 调用的导出 Activity，不带 `MAIN`/`LAUNCHER`。
- 上游库用 NDK `27.3.13750724` 构建（`source-lock.json`），打包时显式 `llvm-strip` 并核对 GNU build-id，避免 APK 膨胀到 400 MB 以上。
- 发布工作流产出：签名 APK、SHA-256、`candidate.json`、许可证文本包。
