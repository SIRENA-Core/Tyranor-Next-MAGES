# 第三方组件与许可

宿主 APK 的 `libimpacto.so` 是**未改动**的上游 [CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto) 在固定提交
（见 `engine/impacto/source-lock.json`）上的原样构建，连同 vcpkg 固定提交下的依赖一起静态链接。许可概况：

| 组件 | 许可 | 备注 |
| --- | --- | --- |
| impacto 本体（MAGES. 引擎的开源重新实现） | ISC | 上游 `LICENSE` |
| FFmpeg（经 vcpkg） | LGPL-2.1 | 上游 Android 构建静态链接 FFmpeg；本构建未启用 GPL/nonfree 选项 |
| libmspack | LGPL-2.1 或更高 | 上游随引擎一并编译 |
| SDL3 | zlib | 构建时 Java 层（`org.libsdl.app`）来自上游检出，不复制、不修改 |
| 其余 vcpkg 依赖 | 各自许可 | 随发布附带的许可证文本包逐项收录 |
| 本仓库的宿主代码 | GPL-2.0 | 见 `LICENSE` |

impacto 自己的第三方清单见上游的 `THIRDPARTY.md`，也收录在许可证文本包里。

## 对应源码

每个发布的 APK 都能从公开的固定来源完整重建，不需要任何本仓库之外的私有材料：

1. 上游源码：`source-lock.json` 中 `impacto`、`libatrac9`、`imgui`、`magic_enum` 的固定提交；
2. 依赖源码：`source-lock.json` 中 `vcpkg` 的固定提交，及其 `arm64-android-impacto` triplet（本仓库 `engine/impacto/triplets/`）；
3. 构建配方：本仓库的 `tools/impacto/` 与 `engine/impacto/host-build/`，与发布同一提交（发布说明里写明提交号）；
4. 工具链：`source-lock.json` 中固定的 NDK 与 CMake。

这满足 LGPL 对 FFmpeg 与 libmspack 的要求：任何人可以用同样的配方重建 `libimpacto.so`（含替换其中的 LGPL 组件）并重新打包。
发布不含对上游的任何补丁，所以没有需要另外提供的"修改后源码"。

## 许可证文本

每个发布附带 `impacto-host-<版本>.licenses.tar.xz`：上游 Impacto 的 LICENSE 与 THIRDPARTY.md、该次构建里每个 vcpkg 依赖的
`copyright` 文件、本仓库的 LICENSE 与本文件。
