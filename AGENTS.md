# Repository Guidelines

本文档是 AI Agent（以及人工维护者）在本仓库内工作时必须遵循的规范。动手前先读完，与既有实现保持一致。

本仓库是 Tyranor Next 的 **MAGES. 引擎外置宿主**：构建输入 = 固定的上游 [CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto) 提交 + 本仓库的补丁系列，产物是一个独立的 Android APK。用户入口见 [README.md](README.md)。

## 核心规则：上游代码只能以补丁形式修改

1. **本仓库不包含、也不直接修改上游 impacto 的源码。** 上游只以 `engine/impacto/source-lock.json` 里的 `impacto.revision` 固定提交的形式出现。
2. **所有对引擎的兼容性改动（C++ 源码、`profiles/`、`gamedefinitions.lua`、着色器、资源）都只能存在于 [`engine/impacto/patches/`](engine/impacto/patches/README.md) 的补丁系列里。** 不得把改过的上游文件、上游源码副本或「先改一份再说」的临时文件提交到本仓库其他位置。
3. 补丁在一份上游检出的补丁分支（`tyn`）上以提交维护，用 `tools/impacto/export-patches.py` 导出。**不得手改** `*.patch`、`series` 或 `source-lock.json` 里的补丁哈希；三者不一致时构建与 Gradle 会直接拒绝。
4. 构建、Gradle 与 CI 校验检出必须恰好等于「固定提交 + 补丁系列」，多一个字节都失败；不要绕过、放宽或关闭这些校验。
5. 补丁不得修改 SDL3 的 Java 层（`org.libsdl.app`）与 SDL 的 JNI 命名空间。

宿主自己的代码不受上述限制，可以直接修改：`engine/impacto/host-apk/`（Java、资源、Gradle）、`engine/impacto/host-build/`、`tools/impacto/`、`docs/`、`engine/impacto/profiles.json`、README／CHANGELOG 等。引擎行为需要宿主配合时，先考虑能否只在宿主侧完成。

## 让补丁易于跟随上游

补丁越小、越少碰上游已有文件，同步上游时冲突越少。写补丁时：

- **优先新增文件**（新的界面类、profile、指令集文件放进新文件，如 `src/games/<代号>/`、`src/profile/games/<代号>/`、`profiles/<profile>/`），对上游已有文件只做最小的挂接（枚举值、`switch` 分支、`CMakeLists.txt` 文件列表）。
- **改动通用行为时必须向后兼容**：新加的 profile 字段设为可选，默认值保持上游原行为；按指令集或 profile 条件分支，不改其他游戏的行为。改了通用代码就要回归其他受影响的 profile。
- 不做与兼容性无关的重构、格式化、重命名或依赖升级；构建脚本与依赖版本不放进补丁。
- **一个提交 = 一个补丁 = 一类改动**，标题 `tyn: <ASCII 描述>`（成为补丁文件名）。通用修复（可向上游提 PR）与仅 TYN 的内容（profile 数据、`gamedefinitions.lua` 注册）分开提交，并在提交正文写明「可向上游提交」或「仅 TYN」。补丁按依赖排序：通用修复与开关 → 指令集 → profile 数据与注册。
- 提交正文写清楚改了什么、为什么、数据或行为的来源，以及在哪台设备上验证了什么。
- 上游已有的通用问题优先向上游提 PR；上游吸收后，在下次同步时删掉对应补丁。

## 同步上游

定期把补丁系列跟到上游最新提交，流程见 [`engine/impacto/patches/README.md`](engine/impacto/patches/README.md#同步上游升级固定提交)，要点：

1. 在补丁分支上 `git rebase --onto <新提交> <旧 revision> tyn`，解决冲突；上游已吸收的补丁直接丢掉。
2. 改 `source-lock.json` 的 `impacto.revision`（导出前改），核对其他固定项（`libatrac9`、`imgui`、`magic_enum`、vcpkg、NDK）是否需要随之更新。
3. 重新导出补丁系列，跑「提交前自检」与 `verify-upstream.py --series-only`、`test-profiles.py`，再构建。
4. 在设备上回归（至少每个有补丁内容的 profile 进标题、进游戏、存读档）。编译通过不等于兼容。
5. 同步单独成一个提交，说明新的上游提交、丢弃或改写了哪些补丁。

不要为了省事改动上游代码来「适配」补丁；冲突一律在补丁分支上解决。

## 兼容性工作的原则

- **界面与行为还原原版，不自行设计。** 为 PC 版游戏补界面时，布局、美术、文字、动画和交互都取自原版数据（原版程序的绘制与输入代码、点击区表、图集、脚本）；在 profile 或补丁里写明数据来源（例如原版函数地址）。原版做不到或在本平台没有意义的部分（例如窗口模式），照原版显示固定状态并在文档里说明，不要另起炉灶。临时估计的实现必须在文档里标明，并在原版实现完成后替换、删除。
- 只把真实设备或模拟器上的运行结果当作兼容性证据；在 PR、CHANGELOG 与文档里写明设备、系统版本、数据版本（原版／汉化）和没有验证的部分。模拟器（MuMu 等）要注明「不是真机」。
- 不提交游戏数据、存档、截图以外的游戏资源或任何密钥。

## 仓库导航

- `engine/impacto/source-lock.json`：上游固定提交与补丁系列完整性记录。
- `engine/impacto/patches/`：补丁系列与维护流程。
- `engine/impacto/host-apk/`：宿主 APK（Java 入口、设置合并、屏幕按键）；`host-build/`：构建配置。
- `engine/impacto/profiles.json`：可启动 profile 清单，是与 Tyranor Next 的契约，改动须与主应用同步。
- `tools/impacto/`：构建、补丁导出／应用、校验与测试脚本；`docs/`：专题文档（如 `steins-gate-steam-sghd.md`）。

## 检查与提交

- 改补丁后：导出 → `python tools/impacto/test-patch-series.py`、`verify-upstream.py --series-only`、`test-profiles.py`（需要补丁后检出），以及 `tools/impacto/` 下与改动相关的 `test-*.py`；CI 工作流 `impacto-host-tools.yml` 跑同一组检查。
- 改宿主 Java 后：Gradle 构建，并在设备上验证。
- 文件 UTF-8 无 BOM、LF 换行（`.gitattributes`；补丁目录关闭换行转换）。
- 提交类型前缀小写英文（`feat:`、`fix:`、`docs:`、`build:` 等），一个提交一类改动。功能变化同步更新 README、CHANGELOG、相关 `docs/` 和 `profiles.json`。
- 不要擅自推送、开 PR 或发布；发布只走 `impacto-host-release` 工作流，始终用同一把签名密钥。
