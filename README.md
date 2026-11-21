# Tyranor Next · MAGES.

[Tyranor Next](https://github.com/Weiss-UltimateSavior/Tyranor-Next) 的 **MAGES. 引擎外置宿主**：独立的 Android APK，由 Tyranor Next 通过 Intent 启动，运行 MAGES.（前 5pb.）的视觉小说。

引擎是开源项目 [CommitteeOfZero/impacto](https://github.com/CommitteeOfZero/impacto)（MAGES. 引擎的重新实现，ISC 许可）。构建输入 = 固定的上游提交 + 本仓库的补丁系列（[`engine/impacto/patches/`](engine/impacto/patches/README.md)）。**impacto 是项目名，不是引擎名。**

| | |
| --- | --- |
| 下载 | [`Tyranor-Next-MAGES.apk`](../../releases/latest/download/Tyranor-Next-MAGES.apk)（固定地址，Tyranor Next 直接用它）；历史版本见 [Releases](../../releases)（标签 `impacto-host-<版本>`） |
| 系统要求 | arm64-v8a，Android 11 及以上 |
| 引擎来源 | 上游固定提交 + 补丁系列，见 [`source-lock.json`](engine/impacto/source-lock.json) |
| 变更记录 | [`CHANGELOG.md`](CHANGELOG.md) |

## 仓库规则

- **上游代码只能以补丁形式修改**：本仓库不包含、也不直接改上游源码；兼容性改动只存在于补丁系列，由补丁分支导出，不手改。
- **补丁要能跟随上游**：优先新增文件，对上游文件只做最小挂接，改通用行为必须向后兼容；定期同步上游，冲突在补丁分支上解决。
- 宿主自己的代码（`engine/impacto/host-apk/`、`tools/impacto/`、文档）可以直接修改。
- 给 PC 版补的界面还原原版（布局、美术与交互取自原版数据），不自行设计。

完整规范见 [`AGENTS.md`](AGENTS.md)。

## 使用

1. 在 Tyranor Next 的引擎页点 MAGES. 跳转下载，或直接下载上面的 APK 安装。
2. 在 Tyranor Next 里添加游戏目录并扫描，点 MAGES. 游戏启动。宿主**没有桌面图标**；首次启动按提示开启「所有文件访问」。

每个游戏有独立的数据根（存档、`userconfig.toml`），在宿主的私有目录里；游戏文件不会被复制或修改。

## 支持的游戏

可启动的 profile 及其目录识别规则见 [`engine/impacto/profiles.json`](engine/impacto/profiles.json)。

| profile | 游戏 | 状态 |
| --- | --- | --- |
| `mo6tw-pc`、`mo6tw-pc-zhs`、`mo6tw-pc-zht` | Windows／Steam 版 Memories Off 6 T-Wave（日／简／繁） | 能进游戏、对话、存读档（真机与模拟器）；选项、百科、返回标题确认框没有界面 |
| `sg-pc` | Steam 版 STEINS;GATE（实验性，宿主 0.3.0 起） | 原版英文与汉化数据都能玩：MuMu 上从序章玩到第 10 章（第 6–8 章结尾的手机分歧走通；第 10 章的分歧与真结局还在验证）；标题、系统菜单、存读档、CONFIG、HELP、TIPS、消息框、手机（邮件、电话、通讯录、附件、左上角的小手机）按原版还原；Bink 1 视频能播，Bink 2 视频（世界线变动的辉光管动画、标题、时间跳跃背景）需要先用 `tools/impacto/sghd/convert_bink2.py` 转换，否则跳过；附加内容（CLEAR LIST／CG／SOUND／MOVIE）未做（详见 [`docs/steins-gate-steam-sghd.md`](docs/steins-gate-steam-sghd.md)） |
| `chlcc`、`cclcc`、`cclcc-switch`、`mo6tw`、`darling`、`dash`、`rne` | 上游 impacto 自带 | 未在本宿主上逐一验证 |

## 与 Tyranor Next 的约定

两边各持一份，改动必须同步：

| 项 | 值 |
| --- | --- |
| 包名 / Action | `com.tyranor.next.impacto` / `com.tyranor.next.impacto.action.RUN` |
| Extras | `com.tyranor.next.impacto.extra.` + `GAME_DIR`、`PROFILE`、`GAME_KEY`、`TITLE`、`SETTINGS`（扁平 JSON，见下） |
| profile | `engine/impacto/profiles.json` 的 `profiles[].id`（宿主只接受这些，`ImpactoRequest.PROFILES` 必须与之相同） |
| 识别规则 | 宿主 0.4.0 起把 `engine/impacto/profiles.json` 打包为 APK 资产 `tyn/profiles.json`，Tyranor Next 从已安装的宿主读取：`detect` 按精确大小写识别 profile；`unsupportedLayouts` 是「像 MAGES. 但没有 profile」的布局（不区分大小写），作为「暂不支持」的游戏列出并用 `tryProfile` 尝试运行。条目是相对游戏目录的路径，最多一层子目录 |
| `GAME_KEY` | `SHA-256(profile + NUL + 游戏目录)` 前 12 字节的小写十六进制；宿主重算，不符即拒绝。校验向量：`/storage/emulated/0/Games/mo6tw` + `mo6tw` → `853382f8b09761cd5c6e475c` |
| 版本 | Tyranor Next 要求宿主 `versionCode` ≥ 3；`mo6tw-pc*` 需要 ≥ 4，`sg-pc` 需要 ≥ 5（手机与视频需要 ≥ 7）；期望的 `versionCode` 不得高于最新发布 |

入口 Activity 对外导出，所有字段按不可信输入校验（profile 白名单、目录须是共享存储下的规范化路径且不在其他应用的 `Android/data`、`Android/obb` 里、`GAME_KEY` 重算），见 [`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)。

### 用户设置（`SETTINGS`）

宿主在引擎启动前把这些值合并进该游戏的 `userconfig.toml`：只改下表的键，其余内容与注释保留；无法安全逐行编辑或会产生重复键时先备份为 `userconfig.toml.bak` 再写干净的文件；游戏运行时不改。未知字段与类型不对的字段忽略。

| 字段（JSON） | 类型 | `userconfig.toml` 键 |
| --- | --- | --- |
| `swapConfirmCancel` | bool | `[CommonSettings]` `SwapConfirmCancelButtons` |
| `vsync` | bool | `[GameSettings.<profile>]` `UseVSync` |
| `videoPlayback` | bool | `[AdvancedSettings]` `VideoPlayer`（`FFmpeg` / `None`） |
| `subtitles` | `all`/`translation`/`karaoke` | `[EnhancementsSettings]` `SubtitleConfig` |
| `closeBacklogAtEnd` | bool | `[EnhancementsSettings]` `CloseBacklogWhenReachedEnd` |
| `delusionMouse` | bool | `[EnhancementsSettings.CHLCC]` / `.CCLCC` `DelusionMousePatch`（只对 `chlcc`、`cclcc`） |
| `logLevel` | `off`/`fatal`/`error`/`warning`/`info`/`debug`/`trace` | `[CommonSettings]` `LogLvl` |
| `touchControls` | bool | 宿主自用：是否显示屏幕按键，缺省显示 |

## 屏幕按键与虚拟鼠标

impacto 的触摸手势很少，纯触屏够不到强制快进、快速存档、方向键、F 键等。宿主在游戏画面上叠了一层小的半透明按键面板（宿主自己的 Java，不改引擎，所有 profile 通用）：可拖动、会淡出的悬浮球；按键直接显示键位名（`Enter`、`Bksp`、`E`、`Q`、`F8`……）并分页提供方向键、F1–F12、字母数字与修饰键、鼠标；虚拟鼠标（点＝左键，长按＝右键）。透明度、大小、展开方向等在面板的「设置」里调整。

## 构建与发布

- **本地构建**：见 [`engine/impacto/host-apk/README.md`](engine/impacto/host-apk/README.md)。上游库只能在 Linux／WSL 上构建，宿主 APK 可在 Windows 上打包；迭代补丁用 `tools/impacto/dev-build.sh`（产物不得发布）。
- **发布**：手动运行 [`impacto-host-release`](.github/workflows/impacto-host-release.yml)（需要签名相关 secrets），**始终用同一把密钥签名**；同名标签存在时拒绝覆盖，升级须提高 `versionCode`／`versionName`。
- **完整性**：每个补丁的 SHA-256 记录在 `source-lock.json`，构建与 Gradle 都校验检出恰好等于「固定提交 + 补丁系列」。
- **同步上游**：流程见补丁目录的 [README](engine/impacto/patches/README.md#同步上游升级固定提交)。

## 许可

自有代码 [GPL-2.0](LICENSE)；APK 内的上游 impacto（ISC）、静态链接的 FFmpeg 与 libmspack（LGPL）等见 [`NOTICE.md`](NOTICE.md)，每个发布附带许可证文本包。
