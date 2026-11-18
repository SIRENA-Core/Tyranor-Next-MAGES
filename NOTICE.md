# 第三方组件与许可

宿主 APK 的 `libimpacto.so` 由上游 [CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto) 在固定提交
（见 `engine/impacto/source-lock.json`）**加上本仓库的补丁系列**（`engine/impacto/patches/`）构建，连同 vcpkg 固定提交下的依赖一起静态链接。
APK 因此包含**经过修改的 ISC 许可上游源码**；修改内容恰好就是本仓库 `engine/impacto/patches/` 里列出（并在 `source-lock.json` 中
逐个记录 SHA-256）的补丁，没有其他改动。许可概况：

| 组件 | 许可 | 备注 |
| --- | --- | --- |
| impacto 本体（MAGES. 引擎的开源重新实现） | ISC | 上游 `LICENSE`；本仓库对它的修改（补丁系列）随源码公开，上游版权声明与许可文本原样保留（含在许可证文本包里） |
| FFmpeg（经 vcpkg） | LGPL-2.1 | 上游 Android 构建静态链接 FFmpeg；本构建未启用 GPL/nonfree 选项 |
| libmspack | LGPL-2.1 或更高 | 上游随引擎一并编译 |
| SDL3 | zlib | 构建时 Java 层（`org.libsdl.app`）来自上游检出（补丁系列不涉及它），不复制 |
| 其余 vcpkg 依赖 | 各自许可 | 随发布附带的许可证文本包逐项收录 |
| 本仓库的宿主代码 | GPL-2.0 | 见 `LICENSE` |
| 本仓库的补丁系列（`engine/impacto/patches/`） | **待仓库所有者决定** | 补丁是对 ISC 上游的修改，上游部分的版权声明与 ISC 许可文本原样保留；补丁新增内容以何种许可发布尚未确定，在所有者决定并写入这里之前，不要假定它是 GPL-2.0 或其他许可 |

impacto 自己的第三方清单见上游的 `THIRDPARTY.md`，也收录在许可证文本包里。

## 对应源码

每个发布的 APK 都能从公开的固定来源完整重建，不需要任何本仓库之外的私有材料：

1. 上游源码：`source-lock.json` 中 `impacto`、`libatrac9`、`imgui`、`magic_enum` 的固定提交；
   **对应源码 = `impacto` 固定提交 + 本仓库 `engine/impacto/patches/` 的补丁系列**（按 `series` 顺序，用 `tools/impacto/apply-patches.py` 应用）；
2. 依赖源码：`source-lock.json` 中 `vcpkg` 的固定提交，及其 `arm64-android-impacto` triplet（本仓库 `engine/impacto/triplets/`）；
3. 构建配方与补丁：本仓库的 `tools/impacto/`、`engine/impacto/host-build/` 与 `engine/impacto/patches/`，与发布同一提交（发布说明里写明提交号）；
4. 工具链：`source-lock.json` 中固定的 NDK 与 CMake。

这满足 LGPL 对 FFmpeg 与 libmspack 的要求：任何人可以用同样的配方重建 `libimpacto.so`（含替换其中的 LGPL 组件）并重新打包。
发布对上游 impacto 的修改只有上述补丁系列，它是公开的、可逐个核对哈希的，因此"修改后的对应源码"就是「固定提交 + 补丁系列」，
不需要另外提供其他材料；FFmpeg、libmspack 与其余依赖仍按 vcpkg 固定提交原样构建，没有补丁。

**用自己提供的 FFmpeg 重建（LGPL 重新链接）：** FFmpeg 是静态链接进 `libimpacto.so` 的，所以重新链接就是重建这个库，步骤即上面的配方：
(1) 在 vcpkg 固定提交的检出里把 `ffmpeg` port 换成你自己的源码（或补丁），triplet 保持 `engine/impacto/triplets/arm64-android-impacto.cmake`；
(2) 按 `tools/impacto/build-upstream.sh` 的顺序构建：`apply-patches.py` 得到「固定提交 + 补丁系列」的源码，`impacto_cmake_configure`（`tools/impacto/build-tools.sh`）配置，`cmake --build` 得到新的 `libimpacto.so`
（`engine/impacto/host-build/pin-dependencies.cmake` 会按 `source-lock.json` 校验 libatrac9、imgui、magic_enum 的固定提交；改动固定项就要同步改 `source-lock.json`，这样产出的候选只用于本地）；
(3) 用 `-PimpactoCandidate=<候选目录>` 运行 `engine/impacto/host-apk` 的 Gradle 构建重新打包 APK（用 `dev-build.sh` 产物时再加 `-PimpactoDevCandidate=true`）。

## 许可证文本

每个发布附带 `Tyranor-Next-MAGES.licenses.tar.xz`：上游 Impacto 的 LICENSE 与 THIRDPARTY.md、该次构建里每个 vcpkg 依赖的
`copyright` 文件、本仓库的 LICENSE 与本文件，以及该次构建所用的补丁系列（`patches/`）。
