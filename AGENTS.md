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
- **改动通用行为时必须向后兼容**：新加的 profile 字段设为可选，默认值保持上游原行为；按指令集或 profile 条件分支，不改其他游戏的行为。已适配的游戏不一定还有数据可以重跑，回归靠下一节「不依赖游戏数据的回归」。
- 不做与兼容性无关的重构、格式化、重命名或依赖升级；构建脚本与依赖版本不放进补丁。
- **一个提交 = 一个补丁 = 一类改动**，标题 `tyn: <ASCII 描述>`（成为补丁文件名）。通用修复（可向上游提 PR）与仅 TYN 的内容（profile 数据、`gamedefinitions.lua` 注册）分开提交，并在提交正文写明「可向上游提交」或「仅 TYN」。补丁按依赖排序：通用修复与开关 → 指令集 → profile 数据与注册。
- 提交正文写清楚改了什么、为什么、数据或行为的来源，以及在哪台设备上验证了什么。
- 上游已有的通用问题优先向上游提 PR；上游吸收后，在下次同步时删掉对应补丁。

## 同步上游

定期把补丁系列跟到上游最新提交，流程见 [`engine/impacto/patches/README.md`](engine/impacto/patches/README.md#同步上游升级固定提交)，要点：

1. 在补丁分支上 `git rebase --onto <新提交> <旧 revision> tyn`，解决冲突；上游已吸收的补丁直接丢掉。
2. 改 `source-lock.json` 的 `impacto.revision`（导出前改），核对其他固定项（`libatrac9`、`imgui`、`magic_enum`、vcpkg、NDK）是否需要随之更新。
3. 重新导出补丁系列，跑「提交前自检」与 `verify-upstream.py --series-only`、`test-profiles.py`，再构建。
4. 有游戏数据的 profile 在设备上回归（进标题、进游戏、存读档）；没有数据的靠 profile 快照与「不依赖游戏数据的回归」的规则。编译通过不等于兼容。
5. 同步单独成一个提交，说明新的上游提交、丢弃或改写了哪些补丁。

不要为了省事改动上游代码来「适配」补丁；冲突一律在补丁分支上解决。

## 不依赖游戏数据的回归

已经适配完成的游戏，本地不一定还留着数据，不能指望每次改动都把它们重新玩一遍。改动通用代码时这样保证不影响它们：

- **profile 快照**：`tools/impacto/profile-snapshots/<id>.txt` 记录每个 profile 按引擎的方式加载后（`gamedefinitions.lua`、`game.lua` 及其 include，用检出里引擎自带的 minilua 执行）各顶层配置段的哈希。`test-profiles.py --source <补丁后检出>`（CI 也跑）逐个比对，改到共享的 `profiles/common/*.lua`、别的游戏 include 的布局等都会报出来。`python -I tools/impacto/profile-snapshot.py --source <检出> --diff-against <改动前的检出>` 列出具体变了哪几行；确属有意的改动用 `--update` 更新快照，和补丁一起提交，并在提交正文说明。新增 profile 同样要 `--update` 生成快照。
- **识别规则**：`test-profiles.py` 检查任意两个不同游戏的 `detect` 不会同时命中同一个目录（主应用会把这种目录当作有歧义、两个都不识别）；新游戏的目录与已有规则重合时，给已有规则加可选的 `noneOf`。
- **C++ 行为快照覆盖不到，只能靠结构保证**：通用代码里的新行为一律挂在新的 profile 字段（默认值等于原行为）或新的指令集判断后面，已有 profile 不填这些字段，快照自然不变。做不到这一点的改动（必须改变所有游戏的通用逻辑），提交正文写明影响到哪些 profile、为什么不会改变它们的表现，能在设备上验证的仍要验证。

## 兼容性工作的原则

- **界面与行为还原原版，不自行设计。** 为 PC 版游戏补界面时，布局、美术、文字、动画和交互都取自原版数据（原版程序的绘制与输入代码、点击区表、图集、脚本）；在 profile 或补丁里写明数据来源（例如原版函数地址）。原版做不到或在本平台没有意义的部分（例如窗口模式），照原版显示固定状态并在文档里说明，不要另起炉灶。临时估计的实现必须在文档里标明，并在原版实现完成后替换、删除。
- 只把真实设备或模拟器上的运行结果当作兼容性证据；在 PR、CHANGELOG 与文档里写明设备、系统版本、数据版本（原版／汉化）和没有验证的部分。模拟器（MuMu 等）要注明「不是真机」。
- 不提交游戏数据、存档、截图以外的游戏资源或任何密钥。

## 调试模式：适配时的必备工具

适配或排查问题时先打开调试模式（补丁 0053，所有 profile 通用，详见 [`docs/debug-mode.md`](docs/debug-mode.md)），不要靠手动一句句点或反复从头读档：

- **打开**：启动请求的 `SETTINGS` 里带 `"debugMode": true`（写入 `[CommonSettings] DebugMode = true`）。用 `adb shell am start ... --es ...SETTINGS` 传多个字段时，整个 JSON 要在设备端再加一层单引号，否则设备上的 shell 会把 `{a,b}` 当成花括号展开拆掉。
- **打开菜单**：触屏三指同时按下（模拟器上用多点触摸注入，例如 `app_process` 调 `InputManager.injectInputEvent` 发三个手指的 `ACTION_POINTER_DOWN`）；键盘 Alt+D、手柄 RB+Y。菜单的「适配工具」页可切换中文／English。
- **快速推进**：速度 x8–x64 加「强制快进」，从新游戏几十秒就能跑到第一个分支或问题点；选项与需要操作的画面会停下。到达后关掉强制快进、调回 x1 再观察。
- **逆转**：每句自动快照，「退 1 句／退 10 句」或点列表任意一句回去；回到选项那一句可以重选分支。只保留最近 300 句（可调到 5000），跑远了就回不去，需要反复试的地方先「保存当前状态」。
- **随意切换进度**：保存的状态跨启动保留（存档目录 `debug-states.bin`），重新安装开发版后在标题就能直接读取；配合「Debug Editer」改标志／变量。
- **直接跳转**：任意剧本的任意标签、任意线程（默认主线程），或重开当前剧本；「跳过当前视频」与「解锁 CG、音乐、TIPS」。
- 左上角状态行显示速度、剧本名和对白行号（检查点编号），截图时一并记录，便于在报告里定位。
- 注意：状态里的「行号」是剧本检查点编号，不是反汇编行号；快照不含音效和正在播的语音；引擎改动了 `Sc3VmThread` 的大小后旧的 `debug-states.bin` 会被忽略。调试模式下得到的结论，提交前仍要在关闭调试模式的正常流程里确认一次。

## 与 Tyranor Next 的契约：`profiles.json`

`engine/impacto/profiles.json` 同时是宿主的 profile 白名单和主应用的游戏识别规则：宿主把它原样打包为 APK 资产 `tyn/profiles.json`（`stageImpactoAssets`；发布工作流核对资产与仓库文件逐字节相同），Tyranor Next 扫描时从已安装的宿主读取。规则改错会让用户的游戏认不出或认错，所以：

- **新增 profile 时同时写 `detect`**：`allOf` 是游戏目录里必须存在的条目，按引擎实际打开的路径写，**精确大小写**，相对游戏目录、最多一层子目录、不含 `.`／`..`／空段；语言变体用 `variantOf` 归组，各自的文本档写在 `textArchive`（同样必须存在）。`ImpactoRequest.PROFILES` 要同步。
- **`unsupportedLayouts`** 列「像 MAGES. 但没有 profile 全部命中」的布局（不区分大小写），主应用把这样的目录列为「暂不支持」并用 `tryProfile` 尝试运行；`tryProfile` 必须是现有 profile，选同一代引擎、同一档案格式里最接近的。每条至少两个档案（`script.cpk`、`system.mpk` 这类单个档名其他用 CRI 档案的游戏也有），第二层条目必须是文件。
- **只做向后兼容的改动**：已发布的主应用会读这份文件。不改既有字段的含义与类型，只加可选字段；主应用遇到任何不合格式的内容会整份放弃、退回它的内置目录表。
- 改动后跑 `python -I tools/impacto/test-profiles.py`（检查格式、`tryProfile`、路径规则）；主应用仓库的 `tools/impacto/check-game-catalog.py --host-profiles` 用它核对主应用内置目录表里的 Windows／Steam 版条目。
- 主应用不需要为宿主新增的 profile 发版即可识别，但主应用内置的目录表（宿主没有这份资产时使用）只在主应用仓库里更新。

## 仓库导航

- `engine/impacto/source-lock.json`：上游固定提交与补丁系列完整性记录。
- `engine/impacto/patches/`：补丁系列与维护流程。
- `engine/impacto/host-apk/`：宿主 APK（Java 入口、设置合并、屏幕按键）；`host-build/`：构建配置。
- `engine/impacto/profiles.json`：可启动 profile 清单与识别规则（打包为宿主资产 `tyn/profiles.json`），见上节。
- `tools/impacto/`：构建、补丁导出／应用、校验与测试脚本；`docs/`：专题文档（如 `steins-gate-steam-sghd.md`、`steins-gate-0-steam.md`）。
- 已适配：`sg-pc`（Steam 版 STEINS;GATE）、`sg0-pc`（Steam 版 STEINS;GATE 0，宿主 0.4.4 起）。这两个游戏的数据以后不一定还在，改动它们共用的 SGHD 代码时按「不依赖游戏数据的回归」检查。
- `tools/impacto/sg0/`：S;G0 的原版界面模块（手机、系统菜单、存档、CONFIG、BACKLOG、TIPS、EXTRA）用 Ghidra 反编译后机械翻译成 C++ 的脚本与修正表。原版模块很大、手写移植容易出错时可以照这个做法；生成文件不手改，修正记在 `phone_fixes.py`。

## 检查与提交

- 改补丁后：导出 → `python tools/impacto/test-patch-series.py`、`verify-upstream.py --series-only`、`test-profiles.py`（需要补丁后检出，含 profile 快照比对），以及 `tools/impacto/` 下与改动相关的 `test-*.py`；CI 工作流 `impacto-host-tools.yml` 跑同一组检查。
- 改宿主 Java 或打包内容后：Gradle 构建，并在设备上验证。
- 改 `profiles.json` 后：`test-profiles.py`，并用主应用在设备上扫描一次确认识别结果。
- 文件 UTF-8 无 BOM、LF 换行（`.gitattributes`；补丁目录关闭换行转换）。
- 提交类型前缀小写英文（`feat:`、`fix:`、`docs:`、`build:` 等），一个提交一类改动。功能变化同步更新 CHANGELOG、相关 `docs/` 和 `profiles.json`；README 只写用户需要的入口、约定与当前支持情况，验证过程与细节写进 CHANGELOG 或 `docs/`，不堆在 README 里。
- 不要擅自推送、开 PR 或发布；发布只走 `impacto-host-release` 工作流，始终用同一把签名密钥。
